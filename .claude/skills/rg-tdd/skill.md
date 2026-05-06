---
name: rg-tdd
description: Red-Green TDD workflow for this codebase. Invoke when the user says "use TDD", "write tests first", "red green", or /rg-tdd. Guides you through writing a failing test, making it pass, and committing both together.
---

## Arguments

```
$ARGUMENTS
```

Parse the target from the arguments — the function, class, or behavior that needs testing.

---

## Step 0 — Identify the target

Determine exactly what needs testing:
- Function name and module path (e.g., `src/signals/ema_pipeline.py::generate_ema_signals`)
- What behavior is being specified (new feature, bug fix, or refactor)
- Which test category applies (see below)

**Three test categories in this codebase:**

| Category | Examples | Approach |
|---|---|---|
| Pure functions | `src/indicators/`, `src/analysis/metrics.py`, `src/backtest/trade_logic.py` | Call with known inputs, assert outputs — no fixtures needed |
| Stateful engine | `src/backtest/engine.py`, `src/live/live_engine.py` | Build a small fixture DataFrame with known OHLCV bars; assert on trade log or equity curve |
| External dependencies | `src/data/` loaders, `src/live/alpaca_trader.py`, `src/live/ibkr_trader.py` | Use `monkeypatch` or `unittest.mock` — never hit real APIs or read real data files |

---

## Step 1 — Find the right test file location

Test files mirror the `src/` directory structure under `tests/`:

```
src/signals/ema_pipeline.py      →  tests/signals/test_ema_pipeline.py
src/analysis/metrics.py          →  tests/analysis/test_metrics.py
src/backtest/trade_logic.py      →  tests/backtest/test_trade_logic.py
src/data/aggregator.py           →  tests/data/test_aggregator.py
src/options/greeks.py            →  tests/options/test_greeks.py
```

Check if the file already exists. If it does, read it first to understand what's already covered and append to it. If it doesn't, create it with the standard header:

```python
import pytest
import logging
```

Create any missing `__init__.py` files in new subdirectories so pytest discovers them.

---

## Step 2 — Write the red test

A good failing test:
- Has a descriptive name: `test_<function>_<scenario>` (e.g., `test_generate_signals_returns_empty_on_flat_price`)
- Uses **concrete, hard-coded values** — not random or computed from the implementation
- Asserts on the exact output: return value, raised exception, or log message
- Fails because the **behavior is wrong or missing**, not because of an import error or missing fixture

**Templates by category:**

### Pure function
```python
def test_compute_smi_returns_nan_before_warmup():
    import pandas as pd
    from src.indicators.smi import compute_smi

    close = pd.Series([100.0] * 5)  # fewer bars than warm-up period
    result = compute_smi(close, k=5, d=3, signal=3)

    assert result.isna().all(), "Expected all NaN before warm-up"
```

### Stateful engine (fixture DataFrame)
```python
import pandas as pd
import pytest

@pytest.fixture
def flat_bars():
    """5 flat 5-min bars — no signal should fire."""
    idx = pd.date_range("2025-01-02 09:30", periods=5, freq="5min", tz="America/New_York")
    return pd.DataFrame({
        "open": [400.0] * 5,
        "high": [401.0] * 5,
        "low":  [399.0] * 5,
        "close":[400.0] * 5,
        "volume":[1000] * 5,
    }, index=idx)

def test_engine_no_trades_on_flat_bars(flat_bars):
    from src.backtest.engine import run_backtest
    trades = run_backtest(flat_bars, config={...})
    assert len(trades) == 0
```

### External dependency (mock)
```python
from unittest.mock import MagicMock, patch

def test_load_equity_data_calls_correct_path(tmp_path, monkeypatch):
    from src.data.databento_loader import load_databento_equities

    mock_read = MagicMock(return_value=pd.DataFrame())
    monkeypatch.setattr("pandas.read_csv", mock_read)

    load_databento_equities("2025-01-01", "2025-01-31", data_dir=str(tmp_path))

    mock_read.assert_called_once()
```

### Logging assertion (use caplog, never print)
```python
def test_missing_file_logs_error(caplog):
    import logging
    from src.data.databento_loader import load_databento_equities

    with caplog.at_level(logging.ERROR):
        with pytest.raises(FileNotFoundError):
            load_databento_equities("2025-01-01", "2025-01-31", data_dir="/nonexistent")

    assert "not found" in caplog.text.lower()
```

---

## Step 3 — Confirm red

Run the test and verify it fails:

```bash
source ./venv/bin/activate && \
  python -m pytest tests/path/to/test_file.py::test_function_name -v 2>&1 | tail -20
```

**Check the failure reason:**
- `FAILED ... AssertionError` — correct, the behavior is missing or wrong
- `ERROR ... ImportError` or `ModuleNotFoundError` — stop, fix the import first
- `ERROR ... fixture 'xyz' not found` — stop, fix the fixture first

If the test passes immediately, the behavior already exists — reassess what you're testing.

**If no venv is available locally:** document the test in the file, add a comment `# pending execution — confirm red before proceeding`, and note it in your journal entry.

---

## Step 4 — Write minimum green implementation

Write the smallest code change that makes the test pass. Do not add features beyond what the test requires.

Rules:
- No `print()` — use `logger = logging.getLogger(__name__)`
- Raise exceptions explicitly; never swallow them silently
- If adding a new module, follow the logging standard from `## Coding Standards` in `CLAUDE.md`

---

## Step 5 — Confirm green

```bash
source ./venv/bin/activate && \
  python -m pytest tests/path/to/test_file.py::test_function_name -v 2>&1 | tail -10
```

Expected output: `PASSED`. If it still fails, iterate on the implementation — do not weaken the test.

Run the full test suite to check for regressions:

```bash
source ./venv/bin/activate && \
  python -m pytest tests/ -q 2>&1 | tail -20
```

---

## Step 6 — Check for additional test cases

After the happy path is green, check for gaps:

| Case type | Questions to ask |
|---|---|
| Edge cases | Empty input? Single element? Boundary values (e.g., exactly at warm-up length)? |
| Error paths | Invalid arguments? Missing file? Malformed data? Does it raise the right exception? |
| Logging | Does it log at the right level? Does `caplog` capture the expected message? |
| Regression | Does the full suite still pass? |

Add each additional test case before committing. Keep each test focused on one behavior.

---

## Step 7 — Commit

Stage only the test file(s) and implementation file(s) — not config, data files, or results:

```bash
git add tests/path/to/test_file.py src/path/to/implementation.py
git commit -m "test: red+green for <what>"
```

Commit message format: `test: red+green for <what>`

Examples:
- `test: red+green for compute_smi NaN before warm-up`
- `test: red+green for engine no-trade on flat bars`
- `test: red+green for load_databento_equities mock path`

---

## Step 8 — Update _modules.md and journal

**Update `journal/docs/_modules.md`:** add or update the entry for the module you just tested. Include what it does, what the tests cover, and any known gaps.

**Add a journal log entry:**
1. Read `journal/INDEX.md` to get the next log number
2. Write `journal/log/<NNN>-<slug>.md` — short narrative: what you built, what the tests cover, any design decisions
3. Update `journal/docs/_state.md` if TODOs changed
4. Add the entry to the `## Dev Log` table in `journal/INDEX.md`
