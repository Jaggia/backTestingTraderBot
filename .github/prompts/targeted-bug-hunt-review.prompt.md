Do a targeted bug-hunting review of this repository.

Repo:
./claudeCoding/backTestingTraderBot

Environment:
- Before running anything, use:
  `source ./venv/bin/activate`

Purpose of this review:
- This is a focused bug-finding pass, not a broad holistic review.
- Assume separate prompts already exist for deep backtest-engine review, deep live-engine review, and production-readiness review.
- Use this review when the goal is to surface concrete correctness bugs and high-confidence bug risks quickly.

Context:
- This repo includes backtesting, live trading, options logic, data-loading code, strategy configuration, and tests.
- It is the kind of codebase where subtle correctness bugs matter more than style issues.

Focus only on bugs and concrete behavior risks:
- Trading logic bugs
- State-machine bugs
- Exit/entry ordering bugs
- Timezone/session/calendar bugs
- Race conditions / thread-safety issues
- Data freshness / stale-data bugs
- Backtest realism bugs
- Live-vs-backtest mismatch bugs
- Missing-data behavior that should fail but does not
- Integration bugs hidden by mocks

What to inspect carefully:
- The main engines and shared trade logic
- Options entry/exit/pricing paths
- Data loaders and cache/network behavior
- Broker adapters and live polling paths
- Strategy config handling
- Tests that claim to cover these areas

What not to spend time on:
- Naming nitpicks
- Formatting
- Minor refactors unless they expose a correctness problem
- Broad readiness/process commentary unless it directly explains a bug

How to work:
1. Identify the main runtime paths.
2. Trace the highest-risk paths end to end.
3. Use tests to help locate claims, but do not trust them without checking the production path.
4. Run targeted tests where useful.
5. Report only bugs or strong bug risks with evidence.

Output format:
- Findings only, ordered by severity.
- For each finding include:
  - severity
  - title
  - exact failure mode
  - why it matters in practice
  - file references and line numbers
  - whether it is proven or a strong risk
- Then include:
  - Top 3 fixes to do first
  - Any important areas you could not fully validate
