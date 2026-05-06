Do a test-quality audit of this repository.

Repo:
./claudeCoding/backTestingTraderBot

Environment:
- Before running anything, use:
  `source ./venv/bin/activate`

Goal:
- Determine whether the test suite is proving the behavior that matters, or merely proving mocked expectations and duplicated implementation.

This is not a generic testing review. Make it specific to this repo’s use cases:
- backtesting
- live trading
- options logic
- market-data loading
- broker integration boundaries
- config/schema handling

Look for:
- False positives
- Over-mocking of critical paths
- Tests that patch the exact function they claim to validate
- Tests that restate implementation instead of exercising it
- Gaps around failure handling, missing data, stale data, timezones, calendars, live-vs-backtest parity, and option pricing
- Tests that depend on local env state or cached data without making that explicit
- Important production paths with no direct assertions
- Docs/README/examples that imply coverage which the tests do not actually provide

How to review:
1. Identify the most important production behaviors in the repo.
2. Map those behaviors to the tests that are supposed to cover them.
3. Check whether the tests execute the real code path or bypass it.
4. Run targeted tests and the full suite if practical.
5. Highlight missing tests and misleading tests separately.

Output format:
- Findings first, ordered by severity.
- For each finding include:
  - severity
  - title
  - what the test currently proves
  - what it fails to prove
  - concrete file references and line numbers
  - category: false positive / weak coverage / env-coupled / doc-coverage mismatch / integration gap
- Then include:
  - Highest-value tests to add or rewrite
  - Areas where the suite appears strong
