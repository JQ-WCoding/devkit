---
name: run-app
description: Starts, checks and stops a repo's app servers (API, web) without an IDE from the repo's .devkit/runtime.json. Use for "서버 띄워줘", "start the API and web", "check it on a running server", "stop the servers", and before screen or API checks. Without the config it offers to write one; never opens tunnels or VPNs.
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

- Only when `<main repo>/.devkit/runtime.json` exists. Without it the script refuses: say the repo has not opted in and, unless the repo rules say the developer starts servers, offer to write the config ([config.md](references/config.md)) from the repo's run docs and build files — no service without evidence for its command and port, secrets only through `env_file`. Show it, write it after approval, then run `status` (it reads the config and starts nothing). If the user declines, they start servers themselves.
- Only the central session or `devkit:develop` starts servers. Parallel workers never do (their brief forbids it); the central session starts one for a worktree with `--repo <worktree>` when a screen check needs it (an `env_file` missing from the worktree is read from the main checkout).
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
