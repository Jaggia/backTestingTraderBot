---
name: interpret-mc-results
description: Interpret Monte Carlo simulation output for a completed backtest. Reads the mc_report.md, applies the full decision framework (edge validity, sequencing luck, ruin risk, drawdown budget, consecutive loss planning), and delivers a structured verdict. Use after any backtest run with --mc, or when the user asks to analyse MC output.
---

> **Deep reference:** `journal/tutorials/monte_carlo/` (5-part series). This skill distils the rules from those docs so you don't need to re-read them. Link to specific parts when you cite a concept.

## Step 0 — Locate the MC output

If the user provides a results path, use it. Otherwise find the most recent run:

```bash
ls -td results/db/*/options/5min/monte_carlo/ | head -1
# or for equities:
ls -td results/db/*/equities/5min/monte_carlo/ | head -1
```

Read the following files from that directory:
- `mc_report.md` — percentile table + risk of ruin
- `../report.md` — backtest summary (trade count, win rate, avg win/loss, exit reasons)
- `../config.yaml` — config snapshot at run time (initial capital, sizing mode, contracts)

Also read `mc_metrics.csv` only if you need to compute a custom statistic not in the report.

---

## Step 1 — Sanity-check the sample size

Pull `total_trades` from `../report.md`.

| Trade count | Reliability verdict |
|---|---|
| < 30 | **Exploratory only** — wide CIs, unstable P5/P95. State this upfront. |
| 30–100 | **Directional** — P25/P75 stable, P5/P95 noisy. Flag it. |
| 100–500 | **Good** — all percentiles reliable. |
| 500+ | **Excellent** — fine-grained distribution. |

If < 30 trades: prefix the entire interpretation with a warning and temper all conclusions.

---

## Step 2 — Apply the five-point decision checklist

Work through these in order. Record pass/fail for each.

### Check 1 — Is the median return positive?
- **Pass:** P50 Total Return > 0
- **Fail:** Strategy loses money in the typical ordering → **reject the strategy**
- If fail: stop here, state the conclusion, do not continue to other checks.

### Check 2 — Does the edge survive most orderings?
- **Strong pass:** P25 Profit Factor > 1.0 (edge survives in at least 75% of orderings)
- **Weak pass:** P25 PF between 0.95–1.0 (fragile edge, note it)
- **Fail:** P25 PF < 0.95 → signal logic is weak, edge doesn't survive bad luck
- If P75 PF < 1.0: even lucky orderings don't save it → hard reject.

### Check 3 — Is risk of ruin acceptable?
- **Pass:** Risk of ruin < 5%
- **Caution:** 5–15% → note sizing risk, suggest reducing contracts
- **Fail:** > 15% → capital destruction is plausible, do not deploy
- Note: MC gives a *lower bound* on ruin risk (it cannot generate losses larger than the worst observed trade). Always treat 0% as "extremely low" not "impossible."

### Check 4 — Was the actual result lucky or typical?
Read the **Profit Factor percentile rank**.

| Rank | Interpretation | Action |
|---|---|---|
| P75–P100 | Lucky sequencing — ordering was favorable | Note: forward performance likely closer to P50 |
| P25–P75 | **Neutral** — result is representative | High confidence in the observed edge |
| P5–P25 | Unlucky — bad ordering dragged results down | True edge is likely *better* than observed |
| < P5 | Extremely unlucky | Still pass, but flag as unusual |

Also check Total Return rank — it should tell a consistent story with PF rank. If they diverge significantly (e.g., return is P80 but PF is P40), note the discrepancy.

### Check 5 — Is the P5 max drawdown within the risk budget?
- P5 max drawdown is the stress-test number: 95% of orderings produced a *shallower* drawdown than this.
- Compute dollar amount: `P5_dd_pct × initial_capital` from config.yaml.
- Ask: could the account survive this drawdown and continue trading?
- For 1-contract fixed sizing on options: this is rarely an issue. For percent-of-equity sizing or multiple contracts: flag if P5 DD > 10% of capital.

---

## Step 3 — Interpret the consecutive losses metric separately

This metric is unique: it is **path-order dependent** and often the most surprising number.

- The actual consecutive loss streak sits at a percentile rank.
- If rank < 25th: the actual backtest experienced fewer consecutive losses than most orderings — **live trading will likely feel harder** than the backtest did.
- **Live trading budget rule:** Use the P50 consecutive loss number as the minimum you should mentally and financially prepare for. Use P75 as your planning number.
- State explicitly: *"In a typical ordering you should expect N consecutive losses at some point; in a bad-luck ordering, up to M."*

---

## Step 4 — Assess the return confidence interval width

Compute the 90% CI: `[P5 return, P95 return]`.

| CI width | What it means |
|---|---|
| Entirely positive (P5 > 0) | Strong evidence of real edge — all orderings profitable |
| Straddles zero (P5 < 0 < P95) | Edge exists but small; a bad-luck ordering loses money |
| Entirely negative | Reject — even the median ordering is a loss (caught by Check 1) |

Note the CI width as a measure of strategy consistency. A narrow CI (< 1% spread) means results are stable across orderings. A wide CI (> 3%) means a few large trades dominate — highly path-dependent.

---

## Step 5 — Flag known limitations

Always state these, briefly:

1. **Autocorrelation:** Bootstrap assumes each trade is independent. For 0-DTE options (each trade opens and closes same day), this assumption is reasonable. For multi-day holds, mention block-bootstrap as a caveat.
2. **Regime changes:** MC can only recombine trades that already happened. It cannot simulate market regimes not in the sample. Longer backtests spanning multiple regimes produce more trustworthy MC output.
3. **Fat tails:** MC cannot generate a loss larger than the worst observed trade. Risk of ruin is a lower bound.
4. **MC ≠ overfitting detector:** A clean MC result on an overfit backtest looks healthy. MC validates ordering robustness, not signal validity.

---

## Step 5.5 — Position sizing validation (if available)

Check whether `mc_sizing.md` exists in the same `monte_carlo/` directory.

**If it does not exist:** Skip this step. At the end of Step 6, offer:
> *"Run with `--sizing --sizing-tolerance 10` to determine the optimal number of contracts before P95 drawdown exceeds your risk budget."*

**If it exists:** Read it and incorporate the findings into your verdict.

### What to extract from `mc_sizing.md`

- `recommended_n` — the largest contract count where P95 worst-case drawdown ≤ tolerance
- The P95 DD% at `recommended_n` and at `recommended_n + 1` (shows why it was capped)
- The tolerance that was used (e.g. 10% of capital)
- The P50 return% at `recommended_n` (upside at the safe size)

### How to interpret

| Outcome | What it means | What to say |
|---|---|---|
| `recommended_n ≥ 2` | Can safely scale beyond 1 contract | State the recommended size and the P95 DD at that level |
| `recommended_n == 1` | Edge is real but thin; scaling quickly blows through the budget | Note that 1 contract is the safe ceiling |
| `recommended_n == 0` | Even 1 contract exceeds the P95 DD tolerance | Flag as a **SIZING CONCERN** — add to verdict header |

### What to state explicitly

- *"Sizing validation (tolerance = X%) recommends max **N contracts**. At Nc: P95 worst-case drawdown = -Y% ($Z) — within budget. At N+1c: -A% ($B) — exceeds tolerance."*
- If `recommended_n == 0`: *"Even 1 contract exceeds the X% tolerance — consider a tighter stop-loss or wait for a larger trade sample."*
- Mention the P50 return at `recommended_n` so the user knows the upside at the recommended size.

### Verdict adjustment

- If `recommended_n ≥ 1` and the 5-point checklist passes: no change to verdict header (sizing is additive good news).
- If `recommended_n == 0`: downgrade **DEPLOY-READY** → **SIZING REVIEW** even if the 5-point checklist passes. The edge exists but is too fragile to deploy at even 1 contract within the stated budget — revisit tolerance or stop width.

---

## Step 6 — Deliver the verdict

Structure your output as follows:

### Verdict header
One of:
- **DEPLOY-READY** — all 5 checks pass, result is near P50 (neutral luck)
- **DEPLOY WITH CAUTION** — all 5 pass but edge is fragile (P25 PF near 1.0) or result is above P75 (lucky)
- **SIZING REVIEW** — edge is real but P5 drawdown exceeds comfort; suggest reducing contracts
- **SIZING CONCERN** — all 5 checks pass but sizing validation shows even 1 contract exceeds DD tolerance
- **WEAK EDGE** — Check 2 fails; signal logic needs review
- **REJECT** — Check 1 or Check 2 (hard) fails

### Five-check table
| Check | Result | Pass? |
|---|---|---|
| P50 return > 0 | +X.XX% | ✅/❌ |
| P25 profit factor > 1.0 | X.XX | ✅/⚠️/❌ |
| Risk of ruin < 5% | X.X% | ✅/⚠️/❌ |
| Actual PF rank in P25–P75 | Nth percentile | ✅/⚠️ |
| P5 max DD within budget | -X.XX% (~$XXX) | ✅/⚠️/❌ |
| Sizing: recommended contracts (if mc_sizing.md exists) | N contracts @ -X.XX% P95 DD | ✅/⚠️/❌ |

### Consecutive loss planning
*"Budget for N–M consecutive losses in live trading (actual was K, but the median ordering produces N)."*

### Return CI
*"90% of orderings produce returns between P5% and P95% — CI [straddles zero / entirely positive]."*

### Known limitations (1–2 sentences each, only the applicable ones)

---

## Reference

Full theoretical background: `journal/tutorials/monte_carlo/`
- [01 — Intuition](../../../../../journal/tutorials/monte_carlo/01-intuition.md): what MC is, sequencing luck, the forest metaphor
- [02 — The Math](../../../../../journal/tutorials/monte_carlo/02-the-math.md): bootstrap resampling, all metric formulas
- [03 — Quant Applications](../../../../../journal/tutorials/monte_carlo/03-quant-applications.md): the 6-point checklist, position sizing via MC, ruin estimation
- [04 — Pitfalls](../../../../../journal/tutorials/monte_carlo/04-pitfalls.md): autocorrelation, regime changes, overfitting, fat tails
- [05 — Our Implementation](../../../../../journal/tutorials/monte_carlo/05-our-implementation.md): code walkthrough, worked example, decision framework
