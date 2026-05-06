---
name: update-docs
description: Update project documentation after a coding session. Writes a journal log entry, updates _state.md and _modules.md, and fixes any stale content in README.md and CLAUDE.md. Use after implementing features or making significant changes.
---

You are performing a documentation update for the backTestingTraderBot backtesting project. Follow these steps precisely.

## Context

$ARGUMENTS

## Step 1 — Understand what changed

Run these to get the full picture:
- `git log --oneline -10` — recent commits
- `git diff HEAD~1` (or `git diff HEAD~N` if multiple commits this session) — what actually changed in code and docs

## Step 2 — Write a journal log entry

1. Read `journal/INDEX.md` to find the next log number and understand existing structure
2. Read `journal/docs/_state.md` and `journal/docs/_modules.md` for current project state
3. Write a new numbered entry in `journal/log/` (e.g. `009-short-name.md`)

The log entry must follow this structure:
- **Header**: `# Session NNN — Title` + date
- **What changed**: bullet list of concrete changes made (code, config, docs)
- **Why**: rationale for each decision (link to decisions/ doc if one exists or was created)
- **Key details**: anything a future reader needs to understand the implementation
- Keep it narrative and honest — this is a dev log, not a PR description

## Step 3 — Update living state docs

Update `journal/docs/_state.md` if any of these changed:
- Active config values (trade_mode, indicators, exits, sizing)
- TODO item status (mark done if completed)
- Exit priority order
- Live runner behaviour
- Options data flow

Update `journal/docs/_modules.md` if any module's behaviour changed:
- New exit logic
- New parameters cached
- Changed method signatures or behaviour
- New scripts or entry points

## Step 4 — Create or update decisions/runbooks/concepts if warranted

- **decisions/**: if a non-obvious design choice was made this session, write or update a decision doc
- **runbooks/**: if the way to run something changed, update the relevant runbook
- **concepts/**: if a new concept was introduced (new indicator, new pricing model, etc.)

Only create new files if the content is genuinely new. Update existing files otherwise.

## Step 5 — Update INDEX.md

Add the new log entry to the `## Dev Log` table in `journal/INDEX.md`. Format:
```
| NNN | `log/NNN-name.md` | YYYY-MM-DD | One-line summary |
```

If you created or updated a decisions/runbooks/concepts file, update its table too.

## Step 6 — Check README.md and CLAUDE.md for staleness

Scan for anything that no longer matches the actual code:
- Script paths, file names, directory structure
- Config keys or values shown in examples
- Feature descriptions, exit rules, data source details
- Architecture diagrams or data flow descriptions

Fix any stale content found. Do not rewrite sections that are still accurate.

## Step 7 — Summarise

Report back to the user:
- Which journal file was written
- Which docs were updated and why
- Any stale README/CLAUDE.md content that was fixed
- Anything you noticed that should be addressed in a future session
