# Options & Equities Backtesting Framework

A modular Python backtesting framework with pluggable signal strategies, options Greeks tracking, live paper trading on multiple brokers, Monte Carlo simulation, and a Streamlit analytics dashboard.

## Features

- **Pluggable Signal Systems**: Indicator pair (SMI + Williams %R), EMA 233, and sequential trigger chains supporting any combination of indicators
- **Multi-instrument Trading**: Backtest equities, options (calls/puts), or both
- **Armed Mode / Trigger Chains**: First indicator arms, second fires and disarms — prevents stacking signals from a single event
- **Options Greeks**: Delta, theta, gamma, vega calculated via Black-Scholes with per-position implied volatility
- **Multiple Data Sources**: Databento (production), Alpaca (cached), TradingView (validation)
- **Live Paper Trading**: Databento streaming → Alpaca paper orders, or IBKR streaming → IBKR orders
- **Monte Carlo Simulation**: Bootstrap trade P&Ls to produce equity curve distributions and percentile bands
- **Streamlit Dashboard**: Interactive results browser with trade explorer, comparison views, and cross-run analysis
- **YAML Configuration**: Adjust all strategy parameters without code changes

## Quick Start

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Copy the example config and customize:

```bash
cp config/strategy_params.example.yaml config/strategy_params.yaml
```

Key settings in `config/strategy_params.yaml`:

```yaml
strategy:
  signal_system: trigger_chain   # indicator_pair, ema_233, or trigger_chain
  timeframe: 5min                # 1min or 5min
  trade_mode: equities           # equities or options

signals:
  trigger_chain:
    triggers:
      - indicator: smi           # First indicator arms
      - indicator: williams_r    # Second fires and disarms
    sync_window: X               # Max bars between arm and fire
    vwap_filter: false

exits:
  profit_target_pct: XX.0        # Take profit at +XX%
  stop_loss_pct: XX.0            # Stop loss at -XX%
  eod_close: false               # Close all positions at market close
```

### 3. Run a Backtest

```bash
# Databento data (default)
python main_runner/run_backtest_db.py 2025-11-10 2026-02-13

# Alpaca data
python main_runner/run_backtest_with_alpaca.py 2025-11-10 2026-02-13

# TradingView data
python main_runner/run_backtest_tv.py 2025-11-10 2026-02-13
```

### 4. Review Results

Results appear in `results/{db,alpaca,tv}/{date}/{mode}/{timeframe}/`:

- `backtest.csv` — trade log with entry/exit prices, P&L, and exit reasons
- `report.md` — performance summary
- `equity_curve.png`, `drawdown.png`, `signals.png` — charts
- `config.yaml` — config snapshot at run time

### 5. Launch Dashboard

```bash
streamlit run scripts_py/dashboard.py
```

## Signal Systems

The framework supports multiple signal strategies via `strategy.signal_system`:

| System | Config Key | Description |
|--------|-----------|-------------|
| Indicator Pair | `indicator_pair` | Two indicators with armed-mode sync window |
| EMA 233 | `ema_233` | 233 EMA intrabar cross on 15-min resampled bars |
| Trigger Chain | `trigger_chain` | Sequential 1..N indicator chain with arm/fire logic |

All strategies implement the `SignalStrategy` ABC and are registered in `src/signals/strategy.py` via `_STRATEGY_MAP`. To add a new strategy, subclass `SignalStrategy` and add it to the map.

### Available Indicators

`src/indicators/` provides: SMI, Williams %R, VWAP, EMA, RSI, MACD, TSI, StochRSI. Any combination can be wired into a trigger chain.

## Project Structure

```
backTestingTraderBot/
├── config/
│   └── strategy_params.example.yaml   # Template — copy to strategy_params.yaml
├── main_runner/                       # Backtest entry points (db, alpaca, tv)
├── live_runner/                       # Live paper trading entry points
├── scripts_bash/                      # Shell wrapper scripts
├── scripts_py/                        # Dashboard, download utilities
├── src/
│   ├── data/                          # Loaders (Alpaca, Databento, TradingView, aggregator)
│   ├── indicators/                    # SMI, Williams %R, VWAP, EMA, RSI, MACD, TSI, StochRSI
│   ├── signals/                       # Strategy pattern, indicator pair pipeline, trigger chains
│   ├── backtest/                      # Engine, trade logic, portfolio
│   ├── options/                       # Greeks, pricer, strike selector, position
│   ├── analysis/                      # Metrics, Monte Carlo, visualization
│   ├── live/                          # Streamers, traders, live engine
│   └── utils/                         # Logging config
├── tests/                             # Pytest suite (mirrors src/ structure)
├── journal/                           # Development narrative and reference docs
└── results/                           # Backtest output (gitignored)
```

## Data Sources

| Source | Timeframe | Setup | Best For |
|--------|-----------|-------|----------|
| Databento | 1min → 5min (aggregated) | API key required | Production backtesting |
| Alpaca | 1min, 5min | Cached CSVs | Development, testing |
| TradingView | 5min | Cached CSV | Chart validation |

### Databento Setup

```bash
export DATA_BENTO_PW="your_api_key_here"

# Download and aggregate to 5-min bars
python scripts_py/download_and_aggregate_databento.py 2018-05-01 2026-02-14
```

### Live Trading Environment Variables

```bash
export DATA_BENTO_PW=your_databento_key
export ALPACA_UN=your_alpaca_key
export ALPACA_PW=your_alpaca_secret
```

## Live Paper Trading

```bash
# Databento streaming → Alpaca paper orders
python live_runner/run_live_db.py

# IBKR streaming → IBKR orders (requires IB Gateway)
python live_runner/run_live_ibkr.py
```

## Monte Carlo Simulation

```bash
# Inline — runs after backtest
python main_runner/run_backtest_db.py 2025-11-10 2026-02-13 --mc

# Post-hoc — on any existing results folder
python main_runner/run_monte_carlo.py results/db/YYYY-MM-DD/options/5min --n 2000
```

## Testing

```bash
pytest tests/                        # All tests
pytest tests/test_indicators.py -v   # Single file
pytest --cov=src tests/              # With coverage
```

## Contributing

1. **New Indicators**: Add to `src/indicators/`, import in `src/signals/indicator_pair_pipeline.py`
2. **New Signal Strategy**: Subclass `SignalStrategy` in `src/signals/strategy.py`, add to `_STRATEGY_MAP`
3. **New Exit Rules**: Add to `src/backtest/trade_logic.py` and `src/options/exit_rules.py`
4. **New Metrics**: Add to `src/analysis/metrics.py`

Always add tests in `tests/` mirroring the `src/` structure.

## License

This project is provided as-is for educational and research purposes.

## Author Notes

Built over 25+ agentic coding sessions with Claude Code. See `journal/` for the full development narrative.
