---
name: run-app
description: Starts, checks and stops a repo's app servers (API, web) without an IDE through the devkit runtime harness, using the repo's .devkit/runtime.json — preflight (DB tunnel and other TCP prerequisites), start in dependency order, wait for health, logs and PID state per checkout or worktree, then a runtime run record. Use for "서버 띄워줘", "start the API and web", "check it on a running server", "stop the servers", and before screen or API checks in devkit:develop and devkit:parallel-work. Not for repos without .devkit/runtime.json (the user starts servers there), and never for opening tunnels or VPNs.
argument-hint: "[preflight | up | status | down | logs] [service...]"
---

# Run the app

The harness script does the work; this skill says when to call it and what to do with the result.

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/run-app/scripts/runtime.py" --repo <checkout> <command> [args]
```

| Command | Use |
|---|---|
| `preflight` | Check prerequisites only (tunnel ports and so on). Starts nothing |
| `up [svc...] [--task <ID>]` | Preflight, start the services (plus their `depends`), wait for health, write a `runtime` run record |
| `status [--json]` | What this harness started for this checkout: pid, port, health, commit |
| `down [svc...]` | Stop what the harness started for this checkout and wait for the ports to free |
| `logs <svc> [-n N]` | Tail a service log |

The config format and the per-instance state are in [config.md](references/config.md).

## Rules

- Only when `<main repo>/.devkit/runtime.json` exists. Without it the script refuses; tell the user the repo has not opted in and that they start servers themselves (or offer to write the config from the repo's run docs after approval).
- Only the central session or `devkit:develop` starts servers. Parallel workers never do (their brief forbids it); the central session starts one for a worktree with `--repo <worktree>` when a screen check needs it.
- Never open, close or restart tunnels, VPNs or IDE runs. A failed preflight is reported with its hint; the user fixes it.
- A port already in use is never taken over. Report the listener the script names (often the user's IDE run) and ask whether they will stop it or whether to check against that server instead.
- Pass `--task <ID>` when working from an analysis doc, so the record lands in that work folder.
- Run `up` in the background when the first build is slow (a Gradle `bootRun` can take minutes), and wait for its completion notice.
- A running server writes to whatever DB its profile points to. Save and delete checks still need the target and scope approved first.
- Stop what you started when the check is done (`down`), unless the user wants it left running; say which ones are still up in the report.

## Results

- Report from the script's output: each service's result line, the URLs, and the last line `RUNTIME: PASS` / `RUNTIME: FAIL (<reason>)`. Never call a service up unless its line says `PASS`.
- On `FAIL`, quote the reason and the log tail the script printed, and read more with `logs <svc>` if needed. Do not retry the same `up` more than once without a change (config, freed port, opened tunnel).
- The record path printed as `record …` is the evidence for the run; mention it.
