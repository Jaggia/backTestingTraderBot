"""IBKR paper trading client for options orders.

Wraps ib_insync pointed at IB Gateway (paper account, port 4002).
Presents the same public interface as AlpacaTrader so LiveEngine can use
either broker without changes.

OCC symbol handling:
  Padded form (internal): 'QQQ   260228C00450000'
  Stripped form:          'QQQ260228C00450000'
  IBKR Option contract:   symbol='QQQ', lastTradeDateOrContractMonth='20260228',
                           strike=450.0, right='C', exchange='SMART'

Note: IBKR's avgCost for options is reported per share (×100 = per contract).
"""

import logging
import re
from datetime import datetime

from ib_insync import IB, Option, MarketOrder

from src.constants import OCC_STRIKE_MULTIPLIER

logger = logging.getLogger(__name__)

_SNAPSHOT_WAIT_S = 0.5  # seconds to wait for snapshot market data from IBKR


# ---------------------------------------------------------------------------
# OCC symbol utilities
# ---------------------------------------------------------------------------

def _strip_occ(occ_symbol: str) -> str:
    """'QQQ   260228C00450000' → 'QQQ260228C00450000'"""
    return occ_symbol.replace(" ", "")


def _parse_occ(occ_symbol: str) -> dict:
    """Parse an OCC option symbol into its components.

    Accepts both padded ('QQQ   260228C00450000') and stripped
    ('QQQ260228C00450000') forms.

    Returns dict with keys:
        underlying  : str         e.g. 'QQQ'
        expiry_yymmdd : str       e.g. '260228'
        expiry_yyyymmdd : str     e.g. '20260228'  (IBKR format)
        expiry      : datetime
        option_type : str         'C' or 'P'
        strike      : float       e.g. 450.0
        raw_symbol  : str         padded OCC form
    """
    stripped = _strip_occ(occ_symbol)
    m = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', stripped)
    if not m:
        raise ValueError(f"Cannot parse OCC symbol: {occ_symbol!r}")

    underlying = m.group(1)
    yymmdd = m.group(2)
    option_type = m.group(3)
    strike = int(m.group(4)) / OCC_STRIKE_MULTIPLIER
    expiry = datetime.strptime(yymmdd, "%y%m%d")
    # underlying is always ≤6 chars after regex match; ljust(6) pads to standard OCC root width
    raw_symbol = f"{underlying.ljust(6)}{yymmdd}{option_type}{m.group(4)}"

    return {
        "underlying":      underlying,
        "expiry_yymmdd":   yymmdd,
        "expiry_yyyymmdd": "20" + yymmdd,
        "expiry":          expiry,
        "option_type":     option_type,
        "strike":          strike,
        "raw_symbol":      raw_symbol,
    }


# ---------------------------------------------------------------------------
# IBKRTrader
# ---------------------------------------------------------------------------

class IBKRTrader:
    """IBKR paper trading client.

    Parameters
    ----------
    host : str
        IB Gateway / TWS hostname.
    port : int
        4002 = IB Gateway paper, 7497 = TWS paper.
    client_id : int
        Must differ from IBKRStreamer's client_id.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 4002,
                 client_id: int = 2):
        self._ib = IB()
        try:
            self._ib.connect(host, port, clientId=client_id)
        except Exception as exc:
            logger.error(
                "IBKRTrader: failed to connect to IB Gateway at %s:%s — %s",
                host, port, exc,
            )
            raise
        logger.info(
            "IBKRTrader connected at %s:%s (clientId=%s)", host, port, client_id
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_contract(self, occ_symbol: str) -> Option:
        """Build and qualify an IBKR Option contract from an OCC symbol."""
        parsed = _parse_occ(occ_symbol)
        contract = Option(
            symbol=parsed["underlying"],
            lastTradeDateOrContractMonth=parsed["expiry_yyyymmdd"],
            strike=parsed["strike"],
            right=parsed["option_type"],
            exchange="SMART",
            currency="USD",
        )
        self._ib.qualifyContracts(contract)
        return contract

    # ------------------------------------------------------------------
    # Public interface (matches AlpacaTrader)
    # ------------------------------------------------------------------

    def get_option_mid_price(self, occ_symbol: str) -> float | None:
        """Fetch the mid-price of an option from IBKR live quotes.

        Returns (bid + ask) / 2 if both are valid, else the last price,
        else None. LiveEngine treats None as a runtime error in live trading.
        """
        contract = None
        try:
            contract = self._get_contract(occ_symbol)
            ticker = self._ib.reqMktData(contract, "", snapshot=True)
            self._ib.sleep(_SNAPSHOT_WAIT_S)
            if ticker.bid is not None and ticker.ask is not None:
                if ticker.bid > 0 and ticker.ask > 0:
                    return (ticker.bid + ticker.ask) / 2.0
            if ticker.last is not None and ticker.last > 0:
                return ticker.last
        except Exception as exc:
            logger.warning("Option quote unavailable for %s: %s", occ_symbol, exc)
        finally:
            if contract is not None:
                try:
                    self._ib.cancelMktData(contract)
                except Exception:
                    pass
        return None

    def buy_option(self, occ_symbol: str, qty: int) -> str:
        """Place a market BUY for qty contracts. Returns IBKR order ID string."""
        contract = self._get_contract(occ_symbol)
        order = MarketOrder("BUY", qty)
        trade = self._ib.placeOrder(contract, order)
        self._ib.sleep(1)
        logger.info(
            "BUY %dx %s — orderId=%s", qty, _strip_occ(occ_symbol), trade.order.orderId
        )
        return str(trade.order.orderId)

    def sell_option(self, occ_symbol: str, qty: int) -> str:
        """Place a market SELL to close qty contracts. Returns IBKR order ID string."""
        contract = self._get_contract(occ_symbol)
        order = MarketOrder("SELL", qty)
        trade = self._ib.placeOrder(contract, order)
        self._ib.sleep(1)
        logger.info(
            "SELL %dx %s — orderId=%s", qty, _strip_occ(occ_symbol), trade.order.orderId
        )
        return str(trade.order.orderId)

    def buy_equity(self, symbol: str, qty: int, signal: int) -> str:
        """Place a market BUY for qty shares. Returns IBKR order ID string.

        The *signal* parameter indicates direction (+1 long, -1 short).
        For the initial implementation only long (BUY) is supported.
        """
        from ib_insync import Stock
        contract = Stock(symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)
        action = "BUY" if signal >= 0 else "SELL"
        order = MarketOrder(action, qty)
        trade = self._ib.placeOrder(contract, order)
        self._ib.sleep(1)
        logger.info("BUY EQUITY %dx %s — orderId=%s", qty, symbol, trade.order.orderId)
        return str(trade.order.orderId)

    def sell_equity(self, symbol: str, qty: int) -> str:
        """Place a market SELL to close qty shares. Returns IBKR order ID string."""
        from ib_insync import Stock
        contract = Stock(symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)
        order = MarketOrder("SELL", qty)
        trade = self._ib.placeOrder(contract, order)
        self._ib.sleep(1)
        logger.info("SELL EQUITY %dx %s — orderId=%s", qty, symbol, trade.order.orderId)
        return str(trade.order.orderId)

    def get_order_status(self, order_id: str) -> str:
        """Return the lowercase fill status for a previously placed order.

        Returns 'filled', 'submitted', 'presubmitted', etc., or 'unknown'
        if the order cannot be found.
        """
        try:
            for trade in self._ib.trades():
                if str(trade.order.orderId) == str(order_id):
                    return trade.orderStatus.status.lower()
        except Exception as exc:
            logger.warning("get_order_status: error querying order %s: %s", order_id, exc)
        return "unknown"

    def get_option_positions(self, underlying: str = "QQQ") -> list[dict]:
        """Return open QQQ option positions from the IBKR paper account.

        Each returned dict has the same keys as AlpacaTrader.get_option_positions:
        symbol, qty, avg_entry_price, current_price, side, underlying, expiry,
        option_type, strike, raw_symbol, entry_iv.

        Note: IBKR avgCost is reported per share (÷100 for per-contract price).
              current_price is not available from the positions snapshot;
              set to float("nan") as a sentinel — engine re-fetches via get_option_mid_price.
              entry_iv is not stored by IBKR; set to None.
        """
        positions = self._ib.positions()
        results = []
        for pos in positions:
            c = pos.contract
            if c.secType != "OPT" or c.symbol != underlying:
                continue
            # lastTradeDateOrContractMonth is YYYYMMDD (8 chars)
            exp_str = c.lastTradeDateOrContractMonth  # e.g. '20260228'
            yymmdd = exp_str[2:]                      # strip leading '20' → '260228'
            strike_int = int(c.strike * OCC_STRIKE_MULTIPLIER)
            raw_symbol = f"{underlying.ljust(6)}{yymmdd}{c.right}{strike_int:08d}"

            results.append({
                "symbol":          raw_symbol.replace(" ", ""),
                "qty":             int(pos.position),
                "avg_entry_price": float(pos.avgCost) / 100.0,  # per-share → per-contract
                "current_price":   float("nan"),
                "side":            "long" if pos.position > 0 else "short",
                "underlying":      underlying,
                "expiry":          datetime.strptime(exp_str, "%Y%m%d"),
                "option_type":     c.right,
                "strike":          float(c.strike),
                "raw_symbol":      raw_symbol,
                "entry_iv":        None,
            })
        return results

    def cancel_all_orders(self):
        """Cancel all pending orders (safety call at shutdown)."""
        self._ib.reqGlobalCancel()
        logger.info("All pending IBKR orders cancelled")
