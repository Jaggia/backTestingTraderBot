---
name: validate-tv-backtest
description: Validate a TradingView QQQ backtest by downloading TV data, running the backtest, and comparing results against a TradingView screenshot. Use when the user provides a TradingView strategy report screenshot for comparison.
---

# Validate TV Backtest Skill

When the user provides a TradingView strategy report screenshot (PNG image), follow these steps:

## Step 1: Read the Screenshot

Use the Read tool to view the screenshot image. Extract these metrics from the TradingView strategy report:
- **Date range** (e.g., "Dec 15, 2025 — Mar 20, 2026")
- **Total P&L** (USD and percentage)
- **Max equity drawdown** (USD and percentage)
- **Total trades**
- **Profitable trades** (percentage and count)
- **Profit factor**

Convert the date range to YYYY-MM-DD format for CLI args (e.g., 2025-12-15 and 2026-03-20).

## Step 2: Download TV Data

Run the TradingView data downloader to get fresh QQQ 5-min data:

```bash
python src/data/tv_qqq_5min.py
```

Verify the output CSV filename contains the expected date range. The file is saved to `data/TV/equities/QQQ/5min/`.

**Important:** The downloader fetches the latest N bars. If the screenshot's date range is old and no longer covered by the latest bars, warn the user that the data may not match.

## Step 3: Run the Backtest

Run the TradingView backtest with the extracted dates:

```bash
python main_runner/run_backtest_tv.py <START_DATE> <END_DATE>
```

Capture the output metrics from the backtest results.

## Step 4: Compare Results

Present a comparison table:

| Metric | TradingView | Our Backtest | Delta |
|---|---|---|---|
| Total P&L | ... | ... | ... |
| Total Return % | ... | ... | ... |
| Max Drawdown % | ... | ... | ... |
| Total Trades | ... | ... | ... |
| Win Rate | ... | ... | ... |
| Profit Factor | ... | ... | ... |

## Step 5: Generate Validation Report

After comparing, generate a markdown report and save it inside the backtest results directory.

1. Find the results directory from the backtest output (it will be logged as `results/tv/<date_folder>/equities/5min/`)
2. Create a `tv_validation/` subfolder inside it
3. Write `tv_validation/validation_report.md` with this structure:

```markdown
# TradingView vs Backtest Engine — Validation Report

**Date Range:** <human-readable date range>
**Strategy:** SMI|W%R|VWAP
**Asset:** QQQ (Equities, 5min)
**Validated on:** <today's date>
**TV Data File:** `data/TV/equities/QQQ/5min/<csv-filename>.csv`

## Comparison

| Metric | TradingView | Backtest Engine | Delta | Notes |
|---|---|---|---|---|
| **Total P&L** | ... | ... | ... | ... |
| **Total Return** | ... | ... | ... | ... |
| **Max Drawdown** | ... | ... | ... | ... |
| **Total Trades** | ... | ... | ... | ... |
| **Win Rate** | ... | ... | ... | ... |
| **Profit Factor** | ... | ... | ... | ... |

## Verdict: PASS / FAIL

<Analysis of discrepancies — PASS if P&L within 2% relative and trade count within +/- 1>

## Engine Config at Run Time

<Table of config params from config/strategy_params.yaml>

## Screenshot

<Relative path link to the TV screenshot image>
```

## Step 6: Interpret

Provide brief analysis of any discrepancies:
- A +/- 1 trade difference is expected (backtest_end exit vs TradingView's handling of the final bar)
- P&L within 1-2% relative difference is excellent alignment
- Drawdown differences of ~0.5% are normal due to intrabar fill timing differences
- Larger discrepancies may indicate config drift — check `config/strategy_params.yaml`

If the image path is provided as an argument to the skill, read it directly. If not, ask the user for the screenshot path.
