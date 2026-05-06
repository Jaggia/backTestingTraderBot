Do a holistic review of this repository with the backtesting engine as the top priority.

Repo:
./claudeCoding/backTestingTraderBot

Environment:
- Before running anything, use the project venv:
  `source ./venv/bin/activate`

What this project appears to be:
- A repo for strategy research and trading execution around equities and options.
- It includes backtesting, live trading, data loading, signal generation, options logic, and reporting.
- The codebase contains paths for historical option data, live broker quotes, strategy configs, and a test suite that claims to cover both backtest and live-engine behavior.

Top priority:
- Prioritize backtest-engine accuracy above all other review areas.
- Treat anything that could make backtest results misleading, inflated, unrealistic, or non-reproducible as the highest-risk class of issue.
- Treat issues that could change perceived edge, drawdown, win rate, PnL distribution, or trade frequency as especially important.

Backtest review focus:
- lookahead bias
- future data leakage
- unrealistic entry/exit timing
- unrealistic fills
- stale or fabricated option pricing
- silent fallback behavior
- timezone/session/calendar mistakes
- warmup-window mistakes
- next-bar-open vs same-bar execution mismatches
- option expiry handling
- data-cache assumptions
- environment-dependent behavior that changes simulation results
- discrepancies between documented strategy rules and actual simulation behavior

What I want from the review:
- Review the repo at large, but anchor the review around whether the backtest can be trusted.
- Determine whether the code actually simulates what it appears intended to simulate.
- Focus on correctness, trading realism, reproducibility, and test credibility.
- Prefer real bugs and behavioral mismatches over style comments.

Required coverage:
- At minimum, include a short verdict for each of these areas even if no issue is found:
  - backtest engine
  - shared trade logic
  - options pricing/data path as used by backtests
  - portfolio / execution accounting
  - tests covering backtest behavior
  - docs/config alignment affecting backtests
- You may discuss live-trading code only insofar as it claims parity with or diverges from the backtest.

Review process:
1. Inspect the repo structure and identify the main backtest execution paths first.
2. Read the production implementation before trusting tests.
3. Treat tests as claims about behavior, then verify whether those claims are actually being exercised.
4. Compare README, docs, scripts, and config examples against the implementation.
5. Run targeted tests only when they help validate or falsify a concrete finding; do not substitute test-running for code-path analysis.
6. Run the full suite if practical.
7. Call out both concrete bugs and high-value test weaknesses.
8. Do not make code changes in this pass unless I explicitly ask later.

Guidance:
- Be skeptical.
- Treat silent fallback behavior as suspicious unless clearly justified.
- Treat over-mocked tests as weak evidence.
- Prefer concrete evidence over speculation.
- Do not label a finding as a production bug unless the failure mode is concrete and tied to a real runtime path.
- For areas that appear sound, give a one-line verdict only. Do not pad the review with reassurance.
- Do not spend more than a brief intro describing architecture. The output should be dominated by findings, evidence, and proof gaps.

Useful commands:
- `rg --files`
- `rg -n "<pattern>"`
- `pytest -q`
- `python -m pytest -q`

Output format:
- Findings first, ordered by severity.
- Within each severity level, order findings by expected impact on backtest trustworthiness and decision quality.
- For each finding include:
  - severity: High / Medium / Low
  - concise title
  - what the code appears intended to do
  - what it actually does
  - why it matters for backtest credibility
  - how you know
  - evidence with file references and line numbers
  - classification: production bug / test weakness / doc drift / design risk
  - confidence label: verified by direct code-path evidence / verified by command or test execution / inferred from implementation structure
- If a finding is inferred rather than fully proven, say what would be needed to verify it completely.
- If a finding relates to a path that already has tests nearby, explain why the existing tests did not catch it.
- If behavior depends on environment variables, cached data, timezone assumptions, trading-calendar assumptions, or provider-specific behavior, call that out explicitly.
- Then include:
  - Findings most likely to materially mislead strategy evaluation or trading decisions
  - Open questions / assumptions
  - Areas reviewed but not fully validated
  - Exact commands run and observed results
  - A short, prioritized fix plan for the highest-value issues
  - Review confidence: High / Medium / Low
  - Main reasons confidence is limited

Do not pad the answer with architecture summary unless it directly supports a finding.
