# Blueprint: workspace-cleanup skill

Finds temp files made during work and moves them to the trash after confirmation. `disable-model-invocation: true`.

## Files to create

- `SKILL.md` — 3 steps: scan → confirm → clean and report
- `scripts/scan.py` — a list-only scan (deletes nothing). Takes the repo root and current session ID as arguments. No hard-coded paths
- `evals/evals.json`

## Classification (same table in the script and SKILL.md)

| Class | Content | Handling |
|---|---|---|
| Removal candidates | `_dryrun*`, `_tmp*`, `tmp*`, `scratch*` folders under the root or `docs/`; `*.bak`, `*.orig`, `*.tmp`, `*~`, `*.swp`, `*.rej`; capture images outside the work folder; temp scripts and notes at the root | Clean after confirmation |
| Needs confirmation | Other untracked files not of the shapes above | List only; act only when the user points to them |
| Protected | Tracked files, in-progress changes to source and DB baselines, {{this repo's local work folder}}, rules and guide docs, tests, build output, dependencies and logs, `.claude/`, `CLAUDE.md`, `.env*` | Not listed, not touched |
| Past session scratchpads | Scratchpad folders except the current session's | Only when the user wants |

## Must include

- Do not treat "untracked or ignored by Git" as temporary.
- Delete only with `trash` (no `rm`). After cleaning, confirm with `git status --porcelain` that tracked files and in-progress changes are intact.
- Do not say "clean" while needs-confirmation items remain. Tell the user files can be restored from the trash.
- Do not wire it to a hook or automatic run at task end.
