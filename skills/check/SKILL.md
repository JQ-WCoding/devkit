---
name: check
description: Run only the lint, type, build and test checks related to the change and report real results. Only when the user invokes it.
disable-model-invocation: true
argument-hint: "[lint | type | build | test] [paths...]"
---

# Selective verification

Pick and run only the checks that are needed. Skipping them never blocks work, commits or PRs.

## 1. Run through check-runner

Hand the run to `devkit:check-runner`; it finds the commands (repo rules, else `discover.py`), picks the ones for the change and follows its own run rules. Pass:

- repo root, and the changed paths: the argument paths, else `git status` and `git diff --name-only`
- the kinds from the argument, if any
- the absolute path of `${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/discover.py`, and the CI config path if there is one, to compare candidates against the checks CI actually runs

If it finds no candidates, ask the user for the commands.

## 2. Rows it did not run

For `needs install` and `not run` rows, ask the user once with the reason per row. Run only the approved ones yourself: a dependency install (lock files or installed modules may change), tests that need a DB or external service after confirming the target environment. Checks that need a running app use `devkit:run-app` when the repo has `.devkit/runtime.json`; otherwise the user starts it. Autofix (`--fix`, formatters) only after confirmation, and only on lines within the request. Do not stash, change the staging area or switch branches for a check.

## 3. Results

Report the commands run, exit codes, and only the errors related to the change (a count for pre-existing ones). Write checks that were not run as `not run`.

The final `CHECKS:` line is check-runner's last line; if you ran rows yourself, form it again over all chosen commands by the Report rules in `${CLAUDE_PLUGIN_ROOT}/agents/check-runner.md`. Record it (add `--task <ID>` when working from an analysis doc):

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/record_run.py" --repo <repo root> --line "<CHECKS: line>"
```

Report the `verdict:` word it prints, never "passed" for a PARTIAL. That JSON record is the only evidence file; do not write other logs or reports into the repo.
