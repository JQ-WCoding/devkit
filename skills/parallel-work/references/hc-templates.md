# hc templates for non-Claude workers

Examples for `~/.config/herdr-core/templates/<name>.md`, created only as launcher-hc.md says. Check the options against the installed CLI's `--help` first. Keep the body short: the worker brief, sent as the task, carries the rules.

## codex

```markdown
---
name: codex
description: Codex worker for devkit parallel-work
command: codex --no-daemon --approve-for-me
---
Follow the worker brief below exactly, including how to report.
```

- With a model: add `-m <model>` and save as `codex-<model>`.
- Not yet verified: whether the sandbox lets the worker reach hc for `hc send` and `hc run`. Check this on the first launch.

## antigravity

```markdown
---
name: antigravity
description: Antigravity worker for devkit parallel-work
command: <confirm with the user: interactive launch command and auto-approval options>
---
Follow the worker brief below exactly, including how to report.
```

- Left blank on purpose: ask the user for the command before creating this template.
