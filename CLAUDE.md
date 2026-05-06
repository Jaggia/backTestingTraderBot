# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-instrument options & equities backtesting framework with pluggable signal strategies (indicator pairs, EMA 233, sequential trigger chains). Supports multiple data sources (Databento, Alpaca, TradingView), live paper trading on two brokers (Alpaca, IBKR), Monte Carlo simulation, and a Streamlit dashboard.

Important Note -> This is the venv path for this project :
source ./venv/bin/activate
## Commands

### Running Backtests

The shell scripts live in `scripts_bash/`, use a hardcoded venv path, and call into `main_runner/`:

```bash
# Databento data (default / closest to Interactive Brokers)
./scripts_bash/run_backtest_db.sh
# Or directly:
/path/to/venv/python main_runner/run_backtest_db.py 2025-11-10 2026-02-13

# Alpaca data (auto 3-month warm-up for indicators)
./scripts_bash/run_backtest_alpaca.sh
# Or directly:
/path/to/venv/python main_runner/run_backtest_with_alpaca.py 2025-11-10 2026-02-13

# TradingView data (PST→EST conversion, no separate warm-up)
./scripts_bash/run_backtest_tv.sh
# Or directly:
/path/to/venv/python main_runner/run_backtest_tv.py 2025-11-10 2026-02-13
```

Edit dates inside the `.sh` files or pass as CLI args. The venv lives at `./venv_stonkerino/`.

### Monte Carlo Simulation

Bootstrap trade P&Ls with replacement to produce a distribution of equity curves. Two ways to run:

**Post-processor** (on any existing results folder):
```bash
./scripts_bash/run_mc.sh results/db/February-24-2026_to_February-28-2026_run-February-27-2026/equities/5min
./scripts_bash/run_mc.sh results/db/February-24-2026_to_February-28-2026_run-February-27-2026/equities/5min 2000  # custom N
# Or directly:
/path/to/venv/python main_runner/run_monte_carlo.py <results_dir> [--n 1000] [--seed 42]
```

**Inline** (run MC immediately after a backtest):
Set `RUN_MC=true` in any `run_backtest_*.sh` script, or pass `--mc` directly:
```bash
/path/to/venv/python main_runner/run_backtest_db.py 2025-11-10 2026-02-13 --mc
```

Outputs to `{results_dir}/monte_carlo/`: `mc_equity_fan.png`, `mc_distributions.png`, `mc_report.md`, `mc_metrics.csv`.

### Live Paper Trading

```bash
# Databento → Alpaca paper trading
./scripts_bash/run_live.sh
# Or directly:
/path/to/venv/python live_runner/run_live_db.py

# IBKR → IBKR live trading
/path/to/venv/python live_runner/run_live_ibkr.py
```

`run_live_db.py` streams real-time 1-min bars from Databento, aggregates to 5-min, runs signals + live engine, and routes orders to Alpaca paper trading. `run_live_ibkr.py` uses IBKR market data and order routing (requires IB Gateway running).

### Dashboard

```bash
streamlit run scripts_py/dashboard.py
```

Browse backtest results across data sources and dates. 4 views: Overview, Trade Explorer, Comparison, Cross-Run.

### Tests

```bash
pytest tests/                        # All tests
pytest tests/test_indicators.py -v   # Single test file
pytest --cov=src tests/              # With coverage
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Data Flow

```
Data Loading → Indicator Calculation → Signal Generation → Backtest Engine → Analytics/Visualization
```

### Key Modules

- **`src/data/`** — Data loaders for Alpaca CSVs, TradingView CSVs (PST→EST), Databento API (options + equities with local caching), and 1-min→5-min aggregator
- **`src/data/aggregator.py`** — `aggregate_1m_to_5m()`: resamples 1-min OHLCV to 5-min (open: first, high: max, low: min, close: last, volume: sum), filters to 09:30–15:55, drops incomplete bars. Validated 100% match against native Alpaca 5-min
- **`src/indicators/`** — SMI (`smi.py`), Williams %R (`williams_r.py`), VWAP (`vwap.py`), EMA (`ema.py`)
- **`src/signals/indicator_pair_pipeline.py`** — Unified signal generation for indicator pair and EMA 233 systems. Supports generic indicator pairs, armed mode (arm/fire), resampled intrabar-cross systems, and trigger chains.
- **`src/signals/sequential_logic.py`** — Sequential trigger chain logic: arm on first indicator, fire on second, with configurable sync window.
- **`src/signals/strategy.py`** — `SignalStrategy` ABC + `IndicatorPairStrategy` / `Ema233Strategy` / `TriggerChainStrategy` concrete classes + `create_strategy()` factory registered via `_STRATEGY_MAP`.
- **`src/backtest/engine.py`** — Bar-by-bar backtesting loop using pre-extracted numpy arrays. Handles entry sizing, exit checks (profit target, stop loss, opposite signal, EOD, expiration), and P&L tracking. Uses a `pending_entry` buffer: signal on bar `i` fills at bar `i+1`'s open (no lookahead bias)
- **`src/backtest/trade_logic.py`** — Shared entry/exit logic (`build_entry()`, `check_exit()`), `BarContext`, `ExitConfig`, and `ExitResult` dataclasses. Single ruleset used by both backtest and live engines
- **`src/backtest/portfolio.py`** — Portfolio state: cash, open positions, closed trade log, equity curve
- **`src/options/`** — Position dataclass (`position.py`), Black-Scholes Greeks (`greeks.py`), BS pricing fallback (`option_pricer.py`), strike selection logic (`strike_selector.py` — ATM, 1_ITM, 1_OTM, etc.), entry construction (`entry_logic.py`), exit checking (`exit_rules.py`), utilities (`utils.py`)
- **`src/analysis/metrics.py`** — Performance stats: Sharpe, Sortino, max drawdown, win rate, profit factor
- **`src/analysis/visualize.py`** — PNG chart generation (equity curve, drawdown, signal overlays)
- **`src/analysis/monte_carlo.py`** — Bootstrap Monte Carlo simulation over trade P&Ls; produces equity fan chart, distribution plots, and summary report
- **`src/live/`** — Live trading module: `databento_streamer.py` (Databento WebSocket 1-min→5-min aggregator), `ibkr_streamer.py` (IBKR market data streamer), `live_engine.py` (mirrors backtest bar-by-bar logic), `alpaca_trader.py` (Alpaca paper trading client), `ibkr_trader.py` (IBKR order routing), `broker_protocol.py` (shared broker interface/protocol)

### Entry Points

- **`main_runner/run_backtest_db.py`** — Databento data path (default). Loads 3 months prior data for indicator warm-up, outputs to `results/db/`
- **`main_runner/run_backtest_with_alpaca.py`** — Alpaca data path. Loads 3 months prior data for indicator warm-up, outputs to `results/alpaca/`
- **`main_runner/run_backtest_tv.py`** — TradingView data path. No warm-up needed, outputs to `results/tv/`
- **`live_runner/run_live_db.py`** — Live paper trading entry point (Databento + Alpaca). Uses Databento WebSocket streamer + Alpaca paper trading client
- **`live_runner/run_live_ibkr.py`** — Live trading entry point (IBKR). Uses IBKR market data streamer + IBKR order routing

### Configuration

All strategy parameters live in **`config/strategy_params.yaml`**: timeframe, trade mode (equities/options — "both" has been removed, run two separate backtests instead), indicator settings, sync window, exit rules, position sizing, cost model, and data paths. No code changes needed to adjust parameters.

### Scripts

- **`scripts_py/download_and_aggregate_databento.py`** — Downloads Databento 1-min equity bars (XNAS.ITCH `ohlcv-1m`), aggregates to 5-min, saves as monthly CSVs. Databento doesn't offer native 5-min for equities. Usage: `python scripts_py/download_and_aggregate_databento.py [start] [end]`
- **`scripts_py/download_options_databento.py`** — Pre-warms the Databento options cache before a backtest run. Computes signals, identifies contracts that would be traded, downloads full trading-day 1-min bars for each. Usage: `python scripts_py/download_options_databento.py [start] [end]`
- **`scripts_py/validate_aggregator.py`** — Validates the aggregator by comparing aggregated Alpaca 1-min vs native Alpaca 5-min data
- **`scripts_py/armed_mode_comparison.py`** — Runs 12 backtests across data sources × lookforward modes × armed/non-armed, outputs to `results/others/`
- **`scripts_py/dashboard.py`** — Streamlit results dashboard (read-only). Browses `results/{db,alpaca,tv}/` folders
- **`scripts_py/latest_smi_wPr_vwap.pine`** — TradingView Pine Script strategy definition (reference implementation)

### Data Layout

- Alpaca equities: `data/Alpaca/equities/QQQ/[1min|5min]/[YYYY]/QQQ_[1min|5min]_YYYYMM.csv`
- TradingView equities: `data/TV/equities/QQQ/5min/<date-range>.csv`
- DataBento equities (raw): `data/DataBento/equities/QQQ/1min/QQQ_1min_{start}_to_{end}.csv`
- DataBento equities (aggregated): `data/DataBento/equities/QQQ/5min/[YYYY]/QQQ_5min_YYYYMM.csv`
- DataBento options: `data/DataBento/options/QQQ/[1min|5min]/[YYYY]/[MM].csv`

### Output

Results are organized by data source under `results/`:

```
results/
├── db/          # Databento (default)
├── alpaca/      # Alpaca
├── tv/          # TradingView
└── others/      # Comparison reports (armed_mode_comparison.md)
```

Each source folder is organized as `{source}/{Month-DD-YYYY}/{mode}/{timeframe}/` containing:
- `backtest.csv` — trade log
- `report.md` — markdown report
- `equity_curve.png`, `drawdown.png`, `signals.png` — charts
- `equity_data.csv` — equity curve with cash column (used for interactive dashboard charts)
- `price_data.csv` — close prices for trading period (used for dashboard signals overlay)
- `config.yaml` — config snapshot at run time

### Journal

`journal/` has four layers — agents are responsible for keeping all of them in sync:

- **`log/`** — chronological narrative entries (blog-style, one per session). The user never has to touch anything else; agents write both the log entry and update the reference docs as part of the same step.
- **`decisions/`** — distilled rationale for key design choices (why we did X)
- **`runbooks/`** — step-by-step operational guides (how to run things)
- **`concepts/`** — reference and educational docs (what things are)
- **`docs/`** — living state: `_state.md` (current config + TODOs) and `_modules.md` (module notes)

**When writing a journal entry:**
1. Read `journal/INDEX.md` — understand the structure and next log number
2. Write a numbered narrative entry in `journal/log/` (e.g. `009-feature-name.md`)
3. Update or create the relevant file in `decisions/`, `runbooks/`, or `concepts/` if something meaningful changed
4. Update `journal/docs/_state.md` if config or TODOs changed
5. Add the new log entry to the `## Dev Log` table in `INDEX.md`

## Coding Standards

These apply to all new and modified code. No exceptions.

- **Logging, not print.** Use `import logging; logger = logging.getLogger(__name__)` in every module. Use `logger.info/warning/error/debug`. The only allowed `print()` calls are intentional user-facing tabular displays (e.g. `print_metrics()`).
- **Entry points call `setup_logging()`** from `src/utils/logging_config.py` before anything else, then wrap `main()` in a top-level `try/except KeyboardInterrupt + Exception` that logs the error and calls `sys.exit(1)`.
- **No silent exception swallowing.** A bare `except Exception as e: print/log and return empty` is forbidden. Always `logger.error(...); raise` so the caller decides whether to halt or continue.
- **Validate CLI args at entry points.** If a date or path arg is malformed, log a clean error and `sys.exit(1)` before any work begins.
- **Rationale:** see `journal/decisions/007-logging-and-error-handling.md`

## Testing Standards

These apply to all new features and bug fixes. No exceptions.

### RG-TDD workflow (mandatory)

1. Write a failing test first that specifies the expected behavior — **red**
2. Confirm it fails for the right reason (behavior, not an import error or typo)
3. Write minimum code to make it pass — **green**
4. Commit red + green together

**For refactors:** write characterization tests first (pin current behavior as expected values), then refactor until green.

### Every implementation must

- Have a corresponding test file in the correct `tests/` subdirectory (mirrors `src/` structure)
- Cover the happy path, at least one edge case, and any error/exception path
- Not use `print()` — use pytest `caplog` to assert on logging output
- Update `journal/docs/_modules.md` with the new module entry
- Add a journal log entry (follow the existing numbered sequence in `journal/INDEX.md`)

### Test file naming

Mirrors the source path: `src/signals/ema_pipeline.py` → `tests/signals/test_ema_pipeline.py`

### Test categories

- **Pure functions** (`indicators/`, `analysis/metrics.py`, `backtest/trade_logic.py`): straightforward RG-TDD, no fixtures needed
- **Stateful engine tests** (`backtest/engine.py`, `live/live_engine.py`): build a small fixture DataFrame with known inputs and assert on exact outputs
- **External dependency tests** (`data/` loaders, `live/` traders): use mocks/monkeypatching — never hit real APIs or read real data files in tests

### Characterization test pattern (for refactors)

Run the current code, capture the output, pin it as the expected value, then refactor until the test stays green.

**Full step-by-step workflow:** see `.claude/skills/rg-tdd/skill.md`

## Key Design Decisions

- **Indicators pre-computed** on full dataset, then engine iterates bar-by-bar over numpy arrays for speed
- **Next-bar-open fill** — signal on bar `i` is stored in a `pending_entry` buffer and filled at bar `i+1`'s open. Eliminates same-bar lookahead bias. See `journal/decisions/008-backtest-accuracy-standards.md`
- **Fixed stop/limit levels** set at entry (TradingView `strategy.exit()` style), checked against intrabar high/low
- **Options pricing** uses Databento market data when available, falls back to Black-Scholes
- **All timestamps are EST/EDT**; TradingView loader handles PST→EST conversion
- **Options P&L** uses 100× multiplier (standard contract size)
- **Databento equities** downloaded as 1-min (only schema available for XNAS.ITCH), aggregated to 5-min via `aggregate_1m_to_5m()`. `load_databento_equities()` handles both flat (raw download) and organized (YYYY/monthly CSVs) directory structures
