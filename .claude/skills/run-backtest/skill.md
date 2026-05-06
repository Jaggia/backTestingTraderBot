---
name: run-backtest
description: Run a QQQ backtest with optional MC analysis and deliver a structured interpretation. Accepts partial arguments — anything not specified falls back to current config defaults. Use when the user says "run a backtest", "backtest from X to Y", or invokes /run-backtest.
---

## Arguments

```
$ARGUMENTS
```

Parse the arguments the user provided. Everything unspecified falls back to the current config in `config/strategy_params.yaml` — read it first.

---

## Step 0 — Parse arguments and resolve defaults

Read `config/strategy_params.yaml` to know the current defaults before resolving anything.

Recognised argument forms (any combination, any order):

| What the user might say | Maps to |
|---|---|
| `2025-01-01 2026-04-02` | START_DATE, END_DATE |
| `options` / `equities` | TRADE_MODE |
| `--mc` / `mc` / `with mc` / `monte carlo` | RUN_MC=true |
| `--no-mc` / `no mc` / `skip mc` | RUN_MC=false (explicit override) |
| `alpaca` / `tradingview` / `tv` / `databento` | DATA_SOURCE |
| `ATM` / `1_OTM` / `1_ITM` etc. | STRIKE_SELECTION (options only) |
| `--n 2000` / `n=2000` | MC_SIMULATIONS (default 1000) |
| `ema_233` / `ema` / `system 2` | SIGNAL_SYSTEM=ema_233 |
| `smi_wr` / `smi` / `system 1` | SIGNAL_SYSTEM=smi_wr |

**Default resolution rules:**
- START_DATE: if not given, ask the user — this is the only required parameter with no sensible default.
- END_DATE: if not given, use today's date (read from system or `date` command).
- TRADE_MODE: from `strategy.trade_mode` in config (currently `options`).
- DATA_SOURCE: from `data.data_source` in config (currently `databento`).
- STRIKE_SELECTION: from `options.strike_selection` in config (currently `1_OTM`).
- SIGNAL_SYSTEM: from `strategy.signal_system` in config (default `smi_wr`).
- RUN_MC: default **true** unless the user explicitly disables it (`--no-mc`, `no mc`, `skip mc`).
- MC_SIMULATIONS: 1000.

**If SIGNAL_SYSTEM differs from what is currently in config**, patch `config/strategy_params.yaml` before running (update `strategy.signal_system`), then restore it afterward. Use the Edit tool for this — a targeted single-line patch is fine.

Before running, print a one-line confirmation of resolved parameters:

```
Running: <START> → <END> | mode=<TRADE_MODE> | source=<DATA_SOURCE> | signal=<SIGNAL_SYSTEM> | MC=<yes/no>
```

---

## Step 1 — Pre-warm options cache (options mode only)

Skip this step if TRADE_MODE is `equities`.

```bash
source ./venv/bin/activate && \
  python scripts_py/download_options_databento.py <START_DATE> <END_DATE> 2>&1 | tail -10
```

Check the summary line. If it shows "Downloaded (new): N" > 0, note which contracts were freshly downloaded. If it errors, report the error and stop — do not proceed to the backtest.

---

## Step 2 — Run the backtest

Select the entry point based on DATA_SOURCE:

| DATA_SOURCE | Command |
|---|---|
| `databento` (default) | `python main_runner/run_backtest_db.py <START> <END> [--mc]` |
| `alpaca` | `python main_runner/run_backtest_with_alpaca.py <START> <END> [--mc]` |
| `tradingview` / `tv` | `python main_runner/run_backtest_tv.py <START> <END> [--mc]` |

Always activate the venv first:
```bash
source ./venv/bin/activate && \
  python main_runner/run_backtest_db.py <START_DATE> <END_DATE> [--mc] 2>&1 | grep -v "Cache hit" | grep -v "Requesting"
```

If the backtest errors:
- **Stale market data error** on a specific contract: this usually means an early-close day (e.g., July 3, Independence Day eve) has post-close equity bars. Identify the date from the error, strip equity bars after 13:00 EDT from the monthly 5min CSV in `data/DataBento/equities/QQQ/5min/YYYY/`, then re-run.
- **Missing equity file**: the loader will auto-download it — check if that succeeded in the logs.
- Any other error: report it verbatim and stop.

---

## Step 3 — Locate results

The results directory is logged as:
```
OOS trade log saved to results/db/<YYYY-MM-DD>/<folder>/options/5min/backtest.csv
```

Capture `<folder>` — you'll need it for the next steps. Read:
- `results/db/<YYYY-MM-DD>/<folder>/<mode>/5min/report.md` — full backtest report
- `results/db/<YYYY-MM-DD>/<folder>/<mode>/5min/config.yaml` — config snapshot

---

## Step 4 — Deliver the backtest analysis

Always produce this analysis, regardless of whether MC was run.

### 4a — Performance headline

State clearly: did the strategy make or lose money? What was total return % and absolute P&L?

### 4b — Edge quality table

| Metric | Value | Signal |
|---|---|---|
| Win Rate | X% | >50% = winners more frequent; <50% = need positive expectancy from size |
| Avg Win / Avg Loss | $X / $X | Ratio should be > 1 if win rate < 50% |
| Profit Factor | X.XX | >1.0 = positive expectancy; interpret: weak (1.0–1.2), moderate (1.2–1.5), strong (>1.5) |
| Max Drawdown | -X.XX% | How deep did the equity dip at worst? |
| Sharpe / Sortino | X / X | Note: these are low for 0-DTE options vs buy-and-hold; put in context |

### 4c — Exit reason breakdown

From the Exit Reasons table in report.md. Note the stop_loss vs profit_target ratio:
- If stop_loss count >> profit_target count: strategy is stopping out more than targeting — consider if TP/SL ratio is appropriate
- If roughly balanced: healthy exit distribution

### 4d — Benchmark context

State the buy-and-hold return for the same period and the strategy outperformance/underperformance. Always contextualise: a 0-DTE options strategy with fixed 1-contract sizing on $100k is not a fair comparison to buy-and-hold QQQ — it's deploying a fraction of capital per trade. Note this explicitly.

### 4e — Trade count assessment

| Trade count | What it means |
|---|---|
| < 30 | Very thin sample — results not statistically meaningful |
| 30–100 | Directional signal only |
| 100–300 | Reasonable sample |
| 300+ | Strong sample — results are robust |

---

## Step 5 — MC interpretation (only if RUN_MC=true)

If MC was run, read `results/db/<YYYY-MM-DD>/<folder>/<mode>/5min/monte_carlo/mc_report.md` and apply the full `interpret-mc-results` skill logic inline:

### Five-point checklist
| Check | Result | Pass? |
|---|---|---|
| P50 return > 0 | X.XX% | ✅/❌ |
| P25 profit factor > 1.0 | X.XX | ✅/⚠️/❌ |
| Risk of ruin < 5% | X.X% | ✅/⚠️/❌ |
| Actual PF rank P25–P75 | Nth pct | ✅/⚠️ |
| P5 max DD within budget | -X.XX% | ✅/⚠️/❌ |

### Sequencing luck verdict
- PF rank near 50th = neutral (result is representative)
- PF rank > 75th = got lucky (forward performance likely lower)
- PF rank < 25th = got unlucky (true edge likely better)

### Consecutive loss planning
State: *"Budget for [P50 consec losses] consecutive losses minimum; [P75] in a bad-luck period. The backtest experienced [actual], which sits at the [rank]th percentile — [lucky/typical/unlucky]."*

### Return confidence interval
State whether the 90% CI (P5 to P95 return) straddles zero or is entirely positive.

### MC verdict
One of: **DEPLOY-READY** / **DEPLOY WITH CAUTION** / **SIZING REVIEW** / **WEAK EDGE** / **REJECT**

---

## Step 6 — Final summary

Close with a 3–5 bullet plain-English summary:
- What the strategy did over the period
- Whether the edge appears real (with or without MC context)
- One actionable observation (e.g., "exit distribution is balanced", "sample is thin — extend the date range", "budget for N consecutive losses before live deployment")
- If MC was NOT run: offer — *"Run with `--mc` for sequencing luck analysis and edge validation."*
- Note which signal system was used (System 1 SMI/WR or System 2 EMA 233) so comparison runs are easy to interpret

---

## Step 7 — Save the Claude analysis report

After delivering the full analysis to the user, write the entire analysis (Steps 4–6 output, including MC if it was run) as a markdown file into the results folder.

**File path:**
```
results/db/<YYYY-MM-DD>/<folder>/<mode>/5min/claude_analysis.md
```

**File structure:**

```markdown
# Claude Analysis Report

**Date Range:** <START_DATE> → <END_DATE>
**Trade Mode:** <TRADE_MODE>
**Data Source:** <DATA_SOURCE>
**MC Run:** <yes/no>
**Generated:** <today's date>

---

## Performance Headline

<content from Step 4a>

## Edge Quality

<table from Step 4b>

## Exit Breakdown

<content from Step 4c>

## Benchmark Context

<content from Step 4d>

## Trade Count

<content from Step 4e>

---

## Monte Carlo Analysis

<full MC section from Step 5 — omit this section entirely if RUN_MC=false>

---

## Summary

<bullets from Step 6>
```

Write this file using the Write tool. Do not summarise or shorten — the file should contain the full analysis exactly as delivered to the user. This is the persistent record of Claude's interpretation for this run.

---

## Defaults quick reference (as of last config read)

These are resolved at runtime from `config/strategy_params.yaml` — do not hardcode here.
Read the config in Step 0 and carry these values through all steps.
