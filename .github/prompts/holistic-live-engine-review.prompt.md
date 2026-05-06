Do a holistic review of this repository with the forward-test / live engine as the top priority.

Repo:
./claudeCoding/backTestingTraderBot

Environment:
- Before running anything, use the project venv:
  `source ./venv/bin/activate`

What this project appears to be:
- A repo for strategy research and trading execution around equities and options.
- It includes backtesting, live trading, data loading, signal generation, options logic, and reporting.
- The codebase contains paths for live broker quotes, live polling, strategy configs, order handling, historical warmup data, and a test suite that claims to cover live-engine behavior.

Top priority:
- Prioritize live-engine correctness and forward-test operational safety above all other review areas.
- Treat anything that could cause the live system to trade incorrectly, miss exits, continue in a bad state, or hide failures from the operator as the highest-risk class of issue.

Live / forward-test review focus:
- live quote availability and freshness
- failure handling and fatal-error propagation
- background thread behavior and synchronization
- broker adapter assumptions
- entry/exit parity with intended strategy rules
- stale quote handling
- duplicate-entry or zombie-position risks
- reconciliation/startup assumptions
- order-status assumptions
- environment/config dependencies
- differences between live behavior and documented/backtested behavior
- observability and whether failures are surfaced loudly enough

What I want from the review:
- Review the repo at large, but anchor the review around whether the live / forward-test engine is correct and operationally safe.
- Determine whether the code actually behaves as intended under real-world runtime conditions.
- Focus on correctness, failure handling, trading safety, and test credibility.
- Prefer real bugs and behavioral mismatches over style comments.

Required coverage:
- At minimum, include a short verdict for each of these areas even if no issue is found:
  - live engine
  - broker/data-provider boundary
  - shared trade logic as used by the live engine
  - threading / polling / fatal-state handling
  - tests covering live behavior
  - docs/config alignment affecting live use
- You may discuss backtest code only insofar as it claims parity with or meaningfully diverges from live behavior.

Review process:
1. Inspect the repo structure and identify the main live execution paths first.
2. Read the production implementation before trusting tests.
3. Treat tests as claims about behavior, then verify whether those claims are actually being exercised.
4. Compare README, docs, scripts, and config examples against the implementation.
5. Run targeted tests only when they help validate or falsify a concrete finding; do not substitute test-running for code-path analysis.
6. Run the full suite if practical.
7. Call out both concrete bugs and high-value test weaknesses.
8. Do not make code changes in this pass unless I explicitly ask later.

Guidance:
- Be skeptical.
- Treat swallowed exceptions, silent degradation, stale quotes, and partial failures as major concerns unless clearly justified.
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
- Within each severity level, order findings by expected impact on trading safety, live correctness, and operator visibility.
- For each finding include:
  - severity: High / Medium / Low
  - concise title
  - what the code appears intended to do
  - what it actually does
  - why it matters for live / forward-test safety or correctness
  - how you know
  - evidence with file references and line numbers
  - classification: production bug / test weakness / doc drift / design risk
  - confidence label: verified by direct code-path evidence / verified by command or test execution / inferred from implementation structure
- If a finding is inferred rather than fully proven, say what would be needed to verify it completely.
- If a finding relates to a path that already has tests nearby, explain why the existing tests did not catch it.
- If behavior depends on environment variables, broker responses, cached state, timezone assumptions, trading-calendar assumptions, or provider-specific behavior, call that out explicitly.
- Then include:
  - Findings most likely to cause incorrect live trading or hidden runtime failure
  - Open questions / assumptions
  - Areas reviewed but not fully validated
  - Exact commands run and observed results
  - A short, prioritized fix plan for the highest-value issues
  - Review confidence: High / Medium / Low
  - Main reasons confidence is limited

Do not pad the answer with architecture summary unless it directly supports a finding.
