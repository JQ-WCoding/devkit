---
name: develop
description: Implement an approved analysis doc — code, DB change and rollback SQL, regression check, per-requirement report. Use for "implement what we analyzed", "implement this", "fix the bug". Without an analysis, run devkit:analyze first.
argument-hint: "[task ID | analysis doc path]"
---

# Implement

Make no changes outside the approved plan. If something in the plan cannot be done as written, stop and say so.

## 0. Preconditions

- Find the analysis doc: argument → the analysis just approved in this conversation → an `analysis.md` in the work folder (the local work-folder rule in `docs/rules/`, else `.devkit/work/`) whose branch name or issue key matches → the most recent `analysis.md` (confirm which). If none, run `devkit:analyze` first. For a tiny change (one file, a few lines, no risk-check items), you may show a three-line summary without an analysis doc and ask once whether to proceed.
- If related files changed since the analysis's base commit (`git log <base commit>..HEAD -- <files>`), say so and ask whether to update the analysis.
- Branch: unless the user asks, work on the current branch. When asked for a new branch, follow the naming rule in `docs/rules/git.md` (else `feat/<task ID>-<short name>`, `fix/…`).
- If the working tree has changes unrelated to this task, say so and do not touch those files.

## 1. Implement

- Do the plan one step at a time, in order. When a step is done, mark it `done` in the analysis doc.
- Follow the approach of the existing files you are imitating and `docs/rules/`. By default do not modify shared modules, shared styles or shared components; if it is truly needed, give the reason and confirm first.
- Every changed line must map to a requirement item. Defects you happen to see are not fixed; list them in the report.
- When editing files with a script, preserve line endings (CRLF/LF) and encoding.

## 2. DB change (if any)

- If the repo manages the schema (migration tool, init scripts, DDL baseline, ORM entities), change it that way first. If there is a migration tool, create the executable SQL as a new migration file of that tool and include it in the commit.
- Executable SQL that the repo does not manage goes in the work folder. Numbers are the run order: `00_check.sql` (read-only pre-check, e.g. duplicate count) → `01_…`, `02_…` (data cleanup, change, inserts; re-runnable) → `99_rollback.sql` (rollback, including the previous definition if an existing object changed). With several DB vendors, split by suffix such as `01_change.<db>.sql`.
- If the repo applies the schema automatically at startup, a new constraint can fail on existing data and the app will not start. Explain the apply order (data cleanup → deploy) at the 🛑 gate.
- If the original definition is needed, fetch it with a read-only query or ask the user. Do not run write SQL.

## 3. Verify

- Automated checks: suggest the checks for the changed subprojects via `devkit:check` (a user-invoked skill, so ask whether to run it, or follow its steps if the user asked for checks).
- Behavior check: do not start servers yourself. Check screens and APIs only in an environment the user started, and confirm saved values by querying again. Insert recognizable dummy test data and report what was left behind.
- Regression: go through the analysis doc's **keep-as-is list** one by one.
- If there is a design or mockup, capture the result screen and compare item by item. Do not say "matches the requirement" just because the build passes.
- If something fails, fix it and run the same verification again. Write verification that was not run as `not run`.

## 🛑 DB apply

If there is a DB change, explain the target (local, dev, prod), run order, account and transaction COMMIT point, and let a human run it. After it runs, check object state and data with queries together. Applying to production is outside this skill.

## 4. Report

- Per requirement item: `implemented / deferred (reason) / needs confirmation`
- Changed files, SQL files, verification run and results (including `not run`), test data left behind, defects found but not fixed
- One line on next steps: commit with `devkit:commit`, push with `devkit:push`, PR/MR with `devkit:pr-publish` — done when requested
- Add decisions made during implementation to the analysis doc's "Decision log"
