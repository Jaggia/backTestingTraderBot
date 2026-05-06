#!/usr/bin/env python3
"""Replay backtest using Databento warmup + IBKR live bars for execution.

Loads historical 5-min equity data from Databento for indicator warmup,
then splices in IBKR live-captured bars for the trading period.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yaml

from src.utils.logging_config import setup_logging
from src.data.databento_loader import load_databento_equities
from src.backtest.engine import BacktestEngine
from src.analysis.metrics import (
    compute_metrics,
    compute_buy_hold_benchmark,
    count_trials,
    print_metrics,
    print_benchmark,
    save_report_md,
    save_config_snapshot,
)
from src.analysis.visualize import plot_equity_curve, plot_drawdown, plot_signals_on_price
from main_runner.base_runner import _load_config, _build_run_tag, _update_run_key

logger = logging.getLogger(__name__)


def load_ibkr_bars(csv_path: str) -> pd.DataFrame:
    """Load IBKR live-captured bars CSV into standard OHLCV DataFrame."""
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"].dt.tz_convert("America/New_York")
    df.set_index("timestamp", inplace=True)
    return df


def main() -> None:
    setup_logging()

    config = _load_config()
    from src.utils.config_utils import validate_config

    # --- Parameters ---
    trade_date = "2026-05-05"
    warmup_start = "2026-02-01"  # ~3 months warmup
    ibkr_csv = "results/live/2026-05-05_bars.csv"
    source_name = "db"
    trade_mode_override = "equities"  # IBKR live bars have no options data; use equities mode

    # Override trade mode so engine doesn't try to fetch options from Databento
    config["strategy"]["trade_mode"] = trade_mode_override
    logger.info("Trade mode overridden to: %s (IBKR live replay has no options data)", trade_mode_override)

    validate_config(config)

    # --- Load Databento warmup data ---
    logger.info("Loading Databento warmup data from %s ...", warmup_start)
    db_dir = config["data"]["databento_equities_dir"]
    db_data = load_databento_equities(db_dir, start=warmup_start, end="2026-04-29")
    logger.info("DB warmup: %d bars, %s → %s", len(db_data), db_data.index[0], db_data.index[-1])

    # --- Load IBKR live bars ---
    if not os.path.exists(ibkr_csv):
        logger.error("IBKR bars file not found: %s", ibkr_csv)
        sys.exit(1)
    ibkr_data = load_ibkr_bars(ibkr_csv)
    logger.info("IBKR bars: %d bars, %s → %s", len(ibkr_data), ibkr_data.index[0], ibkr_data.index[-1])

    # --- Splice: DB warmup + IBKR execution ---
    # Drop any DB bars that overlap with IBKR start (Apr 30)
    ibkr_start = ibkr_data.index[0]
    db_data = db_data[db_data.index < ibkr_start]
    equity_data = pd.concat([db_data, ibkr_data])
    equity_data = equity_data[~equity_data.index.duplicated(keep="last")]
    equity_data.sort_index(inplace=True)
    logger.info(
        "Combined: %d bars, %s → %s",
        len(equity_data),
        equity_data.index[0],
        equity_data.index[-1],
    )

    # --- Run backtest ---
    trade_start = pd.Timestamp(trade_date, tz=equity_data.index.tz)
    logger.info("Trading starts: %s (warmup from DB, execution from IBKR)", trade_start)

    engine = BacktestEngine(
        config=config,
        equity_data=equity_data,
        trade_start=trade_start,
        oos_start=trade_start,
    )
    portfolio = engine.run()

    trade_log = portfolio.get_trade_log()
    equity_curve = portfolio.get_equity_df()

    if trade_start and not equity_curve.empty:
        equity_curve = equity_curve[trade_start:]

    # --- Metrics ---
    from datetime import datetime
    run_dt = datetime.now()
    run_tag = _build_run_tag(config) + "_ibkr"
    n_trials = count_trials(current_tag=run_tag)

    oos_metrics = compute_metrics(trade_log, equity_curve, n_trials=n_trials)
    print_metrics(oos_metrics)

    # Buy & hold benchmark
    initial_capital = config.get("strategy", {}).get("initial_capital", 100_000)
    oos_price_data = engine.data[trade_start:]
    oos_close = oos_price_data["close"]
    strategy_final_equity = oos_metrics.get("final_equity", initial_capital)
    first_trade_price = None
    if not trade_log.empty:
        first_entry_time = pd.Timestamp(trade_log.iloc[0]["entry_time"])
        idx = oos_close.index.get_indexer([first_entry_time], method="bfill")[0]
        first_trade_price = float(oos_close.iloc[idx])
    bh_benchmark = compute_buy_hold_benchmark(
        oos_close, initial_capital, strategy_final_equity, first_trade_price
    )
    print_benchmark(bh_benchmark)

    # --- Save results ---
    _update_run_key(config, run_tag, run_dt)
    run_date_folder = run_dt.strftime("%Y-%m-%d")
    start_dt = pd.Timestamp(warmup_start)
    end_dt = pd.Timestamp(trade_date)
    date_folder = (
        f"{start_dt.strftime('%B-%d-%Y')}_to_{end_dt.strftime('%B-%d-%Y')}"
        f"_{run_tag}"
    )
    mode = config["strategy"]["trade_mode"]
    timeframe = config["strategy"]["timeframe"]
    results_dir = f"results/{source_name}/{run_date_folder}/{date_folder}/{mode}/{timeframe}"
    os.makedirs(results_dir, exist_ok=True)

    trade_log.to_csv(f"{results_dir}/backtest.csv", index=False)
    logger.info("Trade log saved to %s/backtest.csv", results_dir)

    oos_trade_data = engine.data[trade_start:]
    if not equity_curve.empty:
        plot_equity_curve(equity_curve, save_path=f"{results_dir}/equity_curve.png")
        plot_drawdown(equity_curve, save_path=f"{results_dir}/drawdown.png")
        equity_curve.to_csv(f"{results_dir}/equity_data.csv")
    if not trade_log.empty:
        plot_signals_on_price(oos_trade_data, trade_log, save_path=f"{results_dir}/signals.png")

    oos_trade_data[["close"]].to_csv(f"{results_dir}/price_data.csv")

    oos_data_range = f"{trade_start} to {equity_data.index[-1]}"
    save_report_md(oos_metrics, config, oos_data_range, f"{results_dir}/report.md", bh=bh_benchmark)
    save_config_snapshot(config, f"{results_dir}/config.yaml")

    logger.info("Results saved to %s", results_dir)
    print(f"\nResults directory: {results_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error("%s", e, exc_info=True)
        sys.exit(1)
