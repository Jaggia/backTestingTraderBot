# Quick Start: Running Backtests

## Shell Scripts (Recommended)

The easiest way to run backtests is using the provided shell scripts. Just edit the dates and run!

### Databento Data Backtest (Default)

```bash
# Edit the dates in the script
nano scripts_bash/run_backtest_db.sh  # or open with your editor

# Then run it
./scripts_bash/run_backtest_db.sh
```

**What it does:**
- Loads Databento equity data from `data/DataBento/equities/QQQ/5min/`
- Automatically adds 3-month indicator warm-up period
- Closest to Interactive Brokers market data
- Saves results to `results/db/`

---

### Alpaca Data Backtest

```bash
# Edit the dates in the script
nano scripts_bash/run_backtest_alpaca.sh  # or open with your editor

# Then run it
./scripts_bash/run_backtest_alpaca.sh
```

**What it does:**
- Loads Alpaca equity data from `data/Alpaca/equities/QQQ/5min/`
- Automatically adds 3-month indicator warm-up period
- Computes Sortino, Sharpe, and other metrics
- Saves results to `results/alpaca/`

---

### TradingView Data Backtest

```bash
# Edit the dates in the script
nano scripts_bash/run_backtest_tv.sh  # or open with your editor

# Then run it
./scripts_bash/run_backtest_tv.sh
```

**What it does:**
- Loads TradingView CSV data from `data/TV/equities/QQQ/5min/2025-11-10-TO-2026-02-13.csv`
- Converts PST timestamps to EST automatically
- No warm-up period (data already filtered)
- Saves results to `results/tv/`

---

## Direct Python Execution

If you prefer running Python directly:

### Databento (default):
```bash
python main_runner/run_backtest_db.py 2025-11-10 2026-02-13
```

### Alpaca:
```bash
python main_runner/run_backtest_with_alpaca.py 2025-11-10 2026-02-13
```

### TradingView:
```bash
python main_runner/run_backtest_tv.py 2025-11-10 2026-02-13
```

---

## Monte Carlo Simulation

Bootstrap trade P&Ls to get a distribution of equity curve outcomes.

### Inline (runs immediately after a backtest):
```bash
python main_runner/run_backtest_db.py 2025-11-10 2026-02-13 --mc
# Or set RUN_MC=true inside run_backtest_db.sh
```

### Post-hoc (on any existing results folder):
```bash
./scripts_bash/run_mc.sh results/db/February-24-2026_to_February-28-2026_run-February-27-2026/equities/5min
# Or directly:
python main_runner/run_monte_carlo.py results/db/February-24-2026_to_February-28-2026_run-February-27-2026/equities/5min --n 2000
```

Outputs `mc_equity_fan.png`, `mc_distributions.png`, `mc_report.md`, and `mc_metrics.csv` in a `monte_carlo/` subfolder.

---

## Live Paper Trading

### Databento stream → Alpaca paper orders:
```bash
./scripts_bash/run_live.sh
# Or directly:
python live_runner/run_live_db.py
```

Requires `ALPACA_UN`, `ALPACA_PW`, and `DATA_BENTO_PW` exported in your shell.

### IBKR stream → IBKR paper orders:
```bash
python live_runner/run_live_ibkr.py
```

Requires IB Gateway (or TWS) running with paper account credentials and the API socket enabled (port 4002 for IB Gateway, 7497 for TWS). Connection settings are read from `config/strategy_params.yaml` under the `live` key — no environment variables needed.

---

## Results Dashboard

```bash
streamlit run scripts_py/dashboard.py
```

Browse all backtest results across data sources and dates. Four views: Overview, Trade Explorer, Comparison, Cross-Run.

---

## Project Structure

```
.
├── scripts_bash/
│   ├── run_backtest_db.sh      ← Easy Databento backtest (edit dates here)
│   ├── run_backtest_alpaca.sh  ← Easy Alpaca backtest (edit dates here)
│   ├── run_backtest_tv.sh      ← Easy TradingView backtest (edit dates here)
│   ├── run_mc.sh               ← Monte Carlo post-processor
│   └── run_live.sh             ← Live paper trading (Databento + Alpaca)
│
├── main_runner/                ← Backtest runner package
│   ├── run_backtest_db.py
│   ├── run_backtest_with_alpaca.py
│   ├── run_backtest_tv.py
│   └── run_monte_carlo.py
│
├── live_runner/                ← Live trading entry points
│   ├── run_live_db.py          ← Databento stream → Alpaca paper orders
│   └── run_live_ibkr.py        ← IBKR stream → IBKR paper orders
│
├── scripts_py/
│   └── dashboard.py            ← Streamlit results dashboard
│
├── data/                       ← Historical data
│   ├── Alpaca/equities/QQQ/...
│   ├── TV/equities/QQQ/...
│   └── DataBento/...
│
├── config/strategy_params.yaml ← Edit strategy parameters
├── src/                        ← Core modules
├── results/                    ← Backtest output
└── README.md                   ← Full documentation
```

---

## Tips

1. **Edit dates easily**: Open the `.sh` scripts in `scripts_bash/` in any text editor and change the date strings
2. **Default data source**: Databento is the default and closest to Interactive Brokers
3. **View results**: Check `results/{db,alpaca,tv}/` for CSV trade log, markdown report, and charts
4. **No warm-up for TV**: TradingView script requires explicit date range (no auto warm-up)
5. **Warm-up for Databento/Alpaca**: These scripts automatically load 3 months prior for indicator warm-up

---

## Example Workflow

```bash
# 1. Edit and run Databento backtest (default)
nano scripts_bash/run_backtest_db.sh    # Change dates if needed
./scripts_bash/run_backtest_db.sh       # Run it

# 2. Check results
ls results/db/

# 3. Browse via dashboard
streamlit run scripts_py/dashboard.py

# 4. Run Monte Carlo on the results
python main_runner/run_monte_carlo.py results/db/<run-folder>/equities/5min

# 5. Compare with Alpaca data
./scripts_bash/run_backtest_alpaca.sh
```
