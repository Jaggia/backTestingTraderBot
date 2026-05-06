"""IBKR live streamer — 1-min bars via reqHistoricalData(keepUpToDate=True),
aggregated to 5-min, then calls on_bar_close.

Uses reqHistoricalData with keepUpToDate=True to get a live-updating
BarDataList of 1-min OHLCV bars.  The list auto-populates via the IBKR
socket; we poll it every 5s to detect new/updated entries (avoids the
broken eventkit updateEvent callback on Python 3.10+).

This approach requires no special market data subscription beyond what
IBKR paper accounts already provide for historical data.

Connects to IB Gateway or TWS (paper account on port 4002 / 7497).
Uses the same reconnection policy as DatabentoStreamer: up to 5 attempts
with exponential backoff (5/10/20/40/60 s), and a stale-connection timeout
that triggers a reconnect if no bar arrives within 120 s.

Requires IB Gateway or TWS to be running and the API socket to be enabled.
"""

import logging
import time
from zoneinfo import ZoneInfo

import pandas as pd
from ib_insync import IB, Stock

from src.constants import STREAMER_RETRY_WAITS, STREAMER_STALE_TIMEOUT_S

logger = logging.getLogger(__name__)

_MAX_RETRIES = 5
_RETRY_WAITS = STREAMER_RETRY_WAITS
_DEFAULT_STALE_TIMEOUT = STREAMER_STALE_TIMEOUT_S

_EST = ZoneInfo("America/New_York")

# How often to poll the BarDataList for new bars (seconds)
_POLL_INTERVAL = 5


def _parse_bar_ts(date_str: str) -> pd.Timestamp:
    """Convert an ib_insync bar date string to a tz-aware EST Timestamp.

    ib_insync returns dates as 'YYYYMMDD  HH:MM:SS' for intraday bars.
    Raises ValueError if the date string cannot be parsed.
    """
    ts = pd.Timestamp(date_str)
    if ts.tzinfo is None:
        ts = ts.tz_localize(_EST)
    else:
        ts = ts.tz_convert(_EST)
    return ts


class IBKRStreamer:
    """Stream 1-min bars from IBKR and emit 5-min bars via callback.

    Parameters
    ----------
    on_bar_close : callable(bar: pd.Series)
        Called with a single-row Series (name=timestamp, values=OHLCV)
        each time a complete 5-min bar is assembled.
    symbol : str
        Ticker symbol to stream (default "QQQ").
    host : str
        IB Gateway / TWS hostname (default 127.0.0.1).
    port : int
        Socket port: 4002 = IB Gateway paper, 7497 = TWS paper,
        4001 = IB Gateway live, 7496 = TWS live.
    client_id : int
        Must be unique per connection to IB Gateway (use a different ID
        from IBKRTrader to avoid conflicts).
    stale_timeout : float
        Seconds without receiving a bar before reconnecting. Default 120 s.
    eod_cutoff_time : str
        HH:MM cutoff time for bars (default 15:55).
    """

    def __init__(self, on_bar_close, on_1min_bar=None, symbol: str = "QQQ",
                 host: str = "127.0.0.1", port: int = 4002,
                 client_id: int = 1, stale_timeout: float = _DEFAULT_STALE_TIMEOUT,
                 eod_cutoff_time: str = "15:55",
                 warmup_end_ts: pd.Timestamp | None = None):
        self._on_bar_close = on_bar_close
        self._on_1min_bar_callback = on_1min_bar
        self._symbol = symbol
        self._host = host
        self._port = port
        self._warmup_end_ts = warmup_end_ts
        self._client_id = client_id
        self._stale_timeout = stale_timeout
        self._eod_cutoff_time = eod_cutoff_time
        self._pending: list[dict] = []
        self._last_bar_time: float = time.monotonic()

    def run(self):
        """Block and stream indefinitely. Reconnects with exponential backoff.

        Ctrl+C / KeyboardInterrupt exits cleanly without retrying.
        """
        attempt = 0
        while True:
            try:
                self._run_once()
                # _run_once returned normally (stale timeout) — treat as transient failure
                attempt += 1
            except KeyboardInterrupt:
                logger.info("IBKRStreamer interrupted by user — stopping")
                raise
            except Exception as exc:
                attempt += 1
                logger.warning(
                    "IBKRStreamer connection error (attempt %d/%d): %s",
                    attempt, _MAX_RETRIES, exc,
                )

            if attempt >= _MAX_RETRIES:
                logger.error(
                    "IBKRStreamer exceeded %d reconnection attempts — giving up",
                    _MAX_RETRIES,
                )
                raise RuntimeError(
                    f"IBKRStreamer failed after {_MAX_RETRIES} attempts"
                )

            wait = _RETRY_WAITS[min(attempt - 1, len(_RETRY_WAITS) - 1)]
            logger.warning(
                "IBKRStreamer reconnecting in %ds (attempt %d/%d) …",
                wait, attempt + 1, _MAX_RETRIES,
            )
            time.sleep(wait)

    def _run_once(self):
        """Connect, subscribe to live 1-min bars via keepUpToDate, aggregate
        to 5-min.

        Uses reqHistoricalData with keepUpToDate=True which creates a
        live-updating BarDataList of 1-min OHLCV bars.  We poll this list
        every _POLL_INTERVAL seconds to detect new/updated bars.

        Unlike the old polling approach (re-requesting every 10s with
        keepUpToDate=False), this subscribes once and receives real-time
        bar updates as they complete — no 15-min paper-account delay.

        Returns normally on a stale-connection timeout so run() can reconnect.
        Raises on unexpected connection errors.
        """
        ib = IB()
        ib.connect(self._host, self._port, clientId=self._client_id)
        logger.info(
            "IBKRStreamer connected to IB Gateway at %s:%s (clientId=%s)",
            self._host, self._port, self._client_id,
        )

        contract = Stock(self._symbol, "SMART", "USD")
        ib.qualifyContracts(contract)

        # Seed seen timestamps with bars up to warmup_end_ts so we don't
        # replay bars the engine already saw during warmup.
        seen_ts: set = set()
        seed = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
            keepUpToDate=False,
        )
        for b in seed:
            ts = _parse_bar_ts(b.date)
            if self._warmup_end_ts is None or ts <= self._warmup_end_ts:
                seen_ts.add(str(b.date))
        logger.info(
            "IBKRStreamer: seeded %d historical bars, %d newer bars will stream",
            len(seen_ts), len(seed) - len(seen_ts),
        )

        # Subscribe to live-updating 1-min bars (keepUpToDate=True).
        # The BarDataList auto-populates as new bars complete.
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="60 S",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
            keepUpToDate=True,
        )
        logger.info(
            "IBKRStreamer: subscribed to live 1-min %s bars "
            "(keepUpToDate, polling BarDataList every %ds)",
            self._symbol, _POLL_INTERVAL,
        )

        # Track which bar dates we've already processed.  The last bar in
        # the list is the "in-progress" bar that gets updated in place —
        # we detect when it's replaced by a new bar (new timestamp).
        _last_seen_count = len(bars)
        self._last_bar_time = time.monotonic()

        try:
            while True:
                # Pump the event loop and wait for next poll.
                # Use ib.sleep instead of time.sleep to keep the socket alive and
                # processing incoming messages into the BarDataList.
                ib.sleep(_POLL_INTERVAL)

                current_count = len(bars)
                if current_count > _last_seen_count:
                    # New bar(s) arrived. The last bar in the list (index current_count-1)
                    # is always the "in-progress" bar. We only want to process
                    # bars that have definitely completed.
                    # Newly completed bars are from _last_seen_count-1 up to current_count-2.
                    new_bars = bars[_last_seen_count - 1 : current_count - 1]
                    _last_seen_count = current_count
                    
                    if new_bars:
                        self._last_bar_time = time.monotonic()
                        for bar in new_bars:
                            ts_str = str(bar.date)
                            if ts_str not in seen_ts:
                                seen_ts.add(ts_str)
                                self._on_1min_bar(bar)
                                logger.debug(
                                    "IBKRStreamer: new completed bar %s O=%.2f H=%.2f L=%.2f C=%.2f",
                                    ts_str, bar.open, bar.high, bar.low, bar.close,
                                )

                # Stale-connection check
                if time.monotonic() - self._last_bar_time > self._stale_timeout:
                    logger.warning(
                        "IBKRStreamer: no bar received for %.0fs — "
                        "treating connection as stale, reconnecting",
                        self._stale_timeout,
                    )
                    ib.cancelHistoricalData(bars)
                    ib.disconnect()
                    return  # triggers a reconnect in run()
        except Exception:
            try:
                ib.cancelHistoricalData(bars)
            except Exception:
                pass
            ib.disconnect()
            raise

    def _on_1min_bar(self, bar):
        """Handle a single 1-min bar from ib_insync."""
        ts = _parse_bar_ts(bar.date)
        now_est = pd.Timestamp.now(tz=_EST)
        lag_s = (now_est - ts).total_seconds()
        logger.info(
            "1-min bar: %s O=%.2f H=%.2f L=%.2f C=%.2f lag=%.0fs",
            ts.strftime("%H:%M"), float(bar.open), float(bar.high),
            float(bar.low), float(bar.close), lag_s,
        )

        # Filter to regular market hours (09:30–cutoff, matching aggregate_1m_to_5m)
        if ts.hour < 9 or (ts.hour == 9 and ts.minute < 30):
            return

        from src.backtest.trade_logic import _is_eod
        if _is_eod(ts.hour, ts.minute, self._eod_cutoff_time) and ts.minute != int(self._eod_cutoff_time.split(":")[1]):
            # If it's after the cutoff minute, skip.
            # We want to include the bar AT the cutoff minute.
            # E.g. 15:55 bar is the 15:55:00-15:55:59 window.
            if ts.hour > int(self._eod_cutoff_time.split(":")[0]) or ts.minute > int(self._eod_cutoff_time.split(":")[1]):
                return

        # Prepare 1-min bar Series for callback
        if self._on_1min_bar_callback:
            one_min = pd.Series({
                "open":   float(bar.open),
                "high":   float(bar.high),
                "low":    float(bar.low),
                "close":  float(bar.close),
                "volume": int(bar.volume),
            }, name=ts)
            self._on_1min_bar_callback(one_min)

        # Reset pending at the start of each 5-min window to discard stale bars
        if ts.minute % 5 == 0:
            if self._pending:
                logger.warning(
                    "IBKRStreamer: discarding %d stale bar(s) from incomplete window before %s",
                    len(self._pending), ts.strftime("%H:%M"),
                )
            self._pending = []

        self._pending.append({
            "timestamp": ts,
            "open":   float(bar.open),
            "high":   float(bar.high),
            "low":    float(bar.low),
            "close":  float(bar.close),
            "volume": int(bar.volume),
        })

        # Emit when this is the last 1-min bar of the 5-min window
        if ts.minute % 5 == 4 and self._pending:
            self._emit()

    def _emit(self):
        bars = self._pending
        self._pending = []
        open_ts = bars[0]["timestamp"]

        five_min = pd.Series({
            "open":   bars[0]["open"],
            "high":   max(b["high"]   for b in bars),
            "low":    min(b["low"]    for b in bars),
            "close":  bars[-1]["close"],
            "volume": sum(b["volume"] for b in bars),
        }, name=open_ts)

        logger.info(
            "5-min bar closed: %s O=%.2f H=%.2f L=%.2f C=%.2f",
            open_ts.strftime("%H:%M"),
            five_min["open"], five_min["high"],
            five_min["low"], five_min["close"],
        )

        self._on_bar_close(five_min)
