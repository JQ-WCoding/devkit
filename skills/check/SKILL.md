---
name: check
description: Run only the lint, type, build and test checks related to the change and report real results. Only when the user invokes it.
disable-model-invocation: true
argument-hint: "[lint | type | build | test] [paths...]"
---

# Selective verification

Pick and run only the checks that are needed. Skipping them never blocks work, commits or PRs.

## 1. Find the commands

1. If repo rules (`docs/rules/`, `CLAUDE.md`, project `.claude/skills/*check*`) list check commands, use them.
2. Otherwise find candidates (a script to run, no need to read it):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/discover.py" <repo root>
```

If there is a CI config, compare against the checks it actually runs. If there are no candidates, ask the user.

## 2. Choose

- With arguments, do only that kind or those paths.
- Without, look at changed files with `git status` and `git diff --name-only` and choose lint and type checks for those subprojects. Choose a build when build config, dependencies or import paths changed or the user wants one; choose tests when the changed code has tests.
- State the chosen commands and the reason in one line, then run them.

## 3. Rules while running

- Do not run commands that start servers, DBs or containers (`dev`, `start`, `serve`, `bootRun`, `docker compose up` and so on).
- If dependency installation (`npm install`, `npm ci`, `pip install` and so on) is needed, ask first. Lock files or installed modules may change.
- Do not run autofix (`--fix`, formatters) over whole files. Use it only after confirmation when the lines it changes are within the request.
- Run tests that need a DB or external services only after confirming the target environment.
- Run long builds and tests in the background and wait for the completion notice.
- Do not stash, change the staging area or switch branches for a check.

## 4. Results

Report the commands run, exit codes, and only the errors and warnings related to the change. For existing violations, judge only the ones related to this change and give a count for the rest. Write checks that were not run as `not run`; if a tool is missing, say so. Do not create evidence files or verification logs.
