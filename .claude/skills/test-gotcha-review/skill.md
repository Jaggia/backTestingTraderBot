---
name: test-gotcha-review
description: Pre-commit test quality check specific to this codebase. Invoke with /test-gotcha-review before committing new tests, or when the user asks "check my tests", "review these tests", or "pre-commit check". Reviews recently written tests against known gotchas encountered in this repo.
---

## Arguments

```
$ARGUMENTS
```

If arguments name a specific file or test class, scope the review to that. Otherwise, review all modified test files (`git diff --name-only HEAD` filtered to `tests/`).

---

## Purpose

This is not a generic test style guide. It is a checklist of **specific failure modes encountered in this codebase** during development. Each item below has been directly observed as a source of false positives, missed bugs, or misleading coverage.

Run through every item in order. For each, either confirm it's clean or flag it with file + line number.

---

## Step 0 — Identify scope

```bash
git diff --name-only HEAD | grep "^tests/"
```

If no test files are staged, also check:

```bash
git diff --name-only --cached | grep "^tests/"
```

Read each modified test file before starting the checklist.

---

## Checklist

### 1. Mock patches the wrong target (false positive)

**What to look for:** `@patch("src.module.ClassName")` or `monkeypatch.setattr("src.module.func")` where the patch target is the *definition* site, but the code under test imports it via a *different* path.

**Rule:** Patch where it's **used**, not where it's **defined**.

```python
# WRONG — patches the definition, but engine.py imported it already
@patch("src.options.greeks.black_scholes")

# RIGHT — patches where engine.py actually looks it up
@patch("src.backtest.engine.black_scholes")
```

**Check:** For every `@patch` or `monkeypatch.setattr`, confirm the target path matches the `import` statement in the module being tested.

---

### 2. Test asserts on mock call, not on real behavior (tautology)

**What to look for:** Tests that only assert `mock_x.assert_called_once_with(...)` with no assertion on what the function under test *returned* or *changed*.

```python
# WEAK — only proves the mock was called, not that the logic is correct
def test_entry_logic(monkeypatch):
    mock_build = MagicMock(return_value=fake_entry)
    monkeypatch.setattr("src.backtest.engine.build_entry", mock_build)
    run_backtest(bars, config)
    mock_build.assert_called_once()  # ← proves nothing about correctness
```

**Rule:** Every test must assert on at least one observable output: return value, side effect, log message, or raised exception. Mock call assertions are supporting evidence, not the primary assertion.

---

### 3. Engine tests use `BacktestEngine(...)` with no assertion on result (dead test)

**Specific to `tests/backtest/test_engine.py`.**

During this session, several tests instantiated `BacktestEngine(...)` but assigned the result to an unused variable — Pylance flagged these, and they were removed. The pattern is:

```python
engine = BacktestEngine(...)   # engine never used → Pylance warning, test proves nothing
```

**Fix:** Either drop the assignment entirely (if testing constructor side effects via mocks), or assign and assert on `engine.run()` or `engine.trades`.

**Check:** Grep for `engine = BacktestEngine` in test files. Each must be followed by a meaningful assertion or the assignment must be removed.

---

### 4. Staleness guard: test checks old `RuntimeError`, not new `None + WARNING`

**Specific to option price lookup tests.**

The staleness behavior changed: `_get_option_price()` now returns `None` and logs a `WARNING` instead of raising `RuntimeError`. Any test asserting `pytest.raises(RuntimeError)` for stale data is now a **false negative** — it will pass for the wrong reason (exception isn't raised at all).

**Check:** In `tests/options/` and `tests/backtest/`, search for:

```bash
grep -n "RuntimeError" tests/options/ tests/backtest/ -r
```

For stale-data tests, the correct pattern is:

```python
result = engine_with_stale_options.run()
assert result is None or trade was skipped
assert "stale" in caplog.text.lower()
```

---

### 5. EOD cutoff test doesn't use `ExitConfig.eod_cutoff_time`

**Specific to `tests/backtest/test_trade_logic.py`.**

`_is_eod()` reads from `ExitConfig.eod_cutoff_time`. Tests that hardcode `hour=15, minute=55` without actually passing a custom `eod_cutoff_time` to `ExitConfig` are not testing the configurable path — they're testing the default.

**Rule:** `TestConfigurableEodCutoff` must include at least one case where `eod_cutoff_time` is explicitly overridden (e.g., `"15:30"`) and the test confirms the earlier cutoff fires.

**Check:** Look for `ExitConfig(` calls in `test_trade_logic.py`. If none set `eod_cutoff_time` explicitly, the configurable behavior has no coverage.

---

### 6. Slippage test doesn't verify modes are exclusive

**Specific to `tests/backtest/test_portfolio.py` `TestOptionsSlippageCostModel`.**

The slippage model was fixed so options use only `slippage_per_contract` and equities use only `slippage_pct`. Tests verify each mode in isolation. What's missing: a test where **both params are set** confirms only the correct one is applied (not additive).

```python
def test_options_slippage_ignores_slippage_pct_when_both_set():
    # Set both params, verify options cost = slippage_per_contract only
    cost = portfolio._transaction_cost(mode="options", price=10.0,
        contracts=1, slippage_pct=99.0, slippage_per_contract=0.05)
    assert cost == pytest.approx(0.05)
```

---

### 7. Monte Carlo test doesn't cover the boundary (exactly 5 trades)

**Specific to `tests/analysis/test_monte_carlo.py`.**

`TestRunMonteCarloInsufficientTrades` covers 0, 1, and 4 trades as failures. It should also verify that **exactly 5 trades passes** — the boundary condition. Without this, a future change to `>= 6` would not be caught.

**Check:** Confirm there's a test case for `n=5` that does **not** raise.

---

### 8. EMA 15-min bar test uses only a uniform 5-min grid (no DST/gap scenario)

**Specific to `tests/signals/test_ema_pipeline.py` `TestIdentify15mCloseBarsGapRobustness`.**

The rewrite of `_identify_15m_close_bars()` was motivated by data gaps corrupting the sequential comparison. The tests cover a uniform gap and a clean sequence. What's missing:

- A sequence crossing a DST boundary (clock jumps, floor("15min") behavior changes)
- A sequence where a bar is missing mid-session (e.g., 09:30, 09:35, 09:45 — skipped 09:40)

These are the exact scenarios that broke the original implementation.

---

### 9. `caplog` assertions are too broad

**What to look for:** `assert "error" in caplog.text` where `caplog.text` includes output from all log levels and all loggers.

**Rule:** Always scope `caplog` to the expected level and, where possible, to the expected logger:

```python
# WEAK
assert "stale" in caplog.text

# BETTER
with caplog.at_level(logging.WARNING, logger="src.backtest.engine"):
    result = engine.run()
assert any("stale" in r.message for r in caplog.records if r.levelno == logging.WARNING)
```

**Check:** Every `caplog.text` assertion — confirm it's guarded by `caplog.at_level(logging.WARNING)` or stronger.

---

### 10. Databento loader tests don't validate `put_call` normalization end-to-end

**Specific to `tests/data/test_data_loaders.py`.**

Two tests were added verifying `ValueError` on unknown/empty `put_call`. What's not tested:

- Mixed-case input (`"call"`, `"put"`) is correctly normalized to `"C"` / `"P"` before hitting the validator
- The validator fires on the *post-normalized* column, not the raw column

A test with `put_call="call"` (lowercase) that expects no error would catch a regression if the `.str.upper().str[0]` step were removed.

---

### 11. Config override path not tested for staleness threshold

The staleness guard reads `config["data"]["max_option_staleness_minutes"]` to set the threshold (default 25 min). There is no test verifying that passing a different value in config changes the threshold.

```python
def test_staleness_threshold_is_configurable():
    # Build options data with 10-min gap
    # config["data"]["max_option_staleness_minutes"] = 5  ← should trigger
    # assert result is None + WARNING logged
    # config["data"]["max_option_staleness_minutes"] = 15 ← should not trigger
    # assert result is a price
```

Without this, the config key is effectively dead — hardcoded behavior with a config-shaped wrapper.

---

### 12. `test_data_loaders.py` external dependency tests — confirm they don't hit disk

**Check:** Every test in `tests/data/` that calls a loader function must use either `tmp_path` (pytest built-in) or `monkeypatch`/`mock` for file I/O. No test should read from `data/Alpaca/`, `data/DataBento/`, or `data/TV/` in the repo root.

```bash
grep -n "data/Alpaca\|data/DataBento\|data/TV" tests/ -r
```

Any hit here is an **env-coupled test** — it will fail on a fresh clone without data files.

---

## Step N — Summary output

After reviewing all items, output a table:

| # | Gotcha | Status | File:Line |
|---|--------|--------|-----------|
| 1 | Patch target path | ✅ clean / ⚠️ flagged | ... |
| 2 | Tautology mock asserts | ... | ... |
| ... | ... | ... | ... |

Flag severity: **⚠️ must fix before commit** vs **💡 good-to-have followup**.

Then list any new gotchas observed that aren't in this checklist — these should be added to this skill file.
