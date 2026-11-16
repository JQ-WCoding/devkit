# Runtime harness config

`<main repo>/.devkit/runtime.json` (local, like the rest of `.devkit/`; Git-excluded). Worktrees under the repo use the main repo's file.

```json
{
  "java_home": "/path/to/jdk",
  "preflight": [
    {"name": "db-tunnel", "tcp": "127.0.0.1:11521", "hint": "Open the VPN and the DB tunnel, then run up again"}
  ],
  "services": [
    {"name": "api", "cwd": "api", "port": 8080,
     "cmd": ["./gradlew", "--no-daemon", "bootRun", "--args=--server.port={port}"],
     "env_file": "api/local.env",
     "health": "http://localhost:{port}/actuator/health", "timeout": 420},
    {"name": "web", "cwd": "web", "port": 3000, "depends": ["api"],
     "cmd": ["npm", "run", "dev", "--", "--port", "{port}", "--strictPort"],
     "env": {"API_TARGET": "http://localhost:{api.port}"},
     "health": "http://localhost:{port}/", "timeout": 90}
  ]
}
```

| Key | Meaning |
|---|---|
| `java_home` | Sets `JAVA_HOME` and puts its `bin` first on `PATH` (top level or per service) |
| `env`, `path_prepend` | Added to every service's environment; service-level keys of the same names add more and win. Put no secrets in `env` |
| `env_file` | `KEY=VALUE` file (relative to the checkout; `#` comments, `export`, quotes allowed) loaded before `env`, top level or per service. Use it for secrets: its values go only to the process, never to output, state or records |
| `preflight[]` | TCP endpoints that must already accept connections. `hint` is shown on failure |
| `services[].cmd` | Argument list, run without a shell from `cwd` (relative to the checkout) |
| `services[].port` | Port in the main checkout. Pass it to the server through `{port}` so worktree instances get theirs |
| `services[].health` | URL that answers 2xx/3xx once ready; 4xx/5xx counts as not ready. `tcp://host:port` checks only the socket. Default `tcp://localhost:{port}` |
| `services[].timeout` | Seconds to become healthy (default 120) |
| `services[].depends` | Services listed earlier that `up` starts first |

Placeholders in `cmd`, `env`, `path_prepend` and `health`: `{port}` (this service), `{<service>.port}`, `{root}` (the checkout), `{instance}`.

## Instances, ports and files

- Instance: `main` for the main checkout, the worktree folder name for a worktree.
- Ports: the main checkout uses the configured ports. A worktree takes the first free slot k (1–9) and every port shifts by k×10 (8001 → 8011). The slot is kept until `down`.
- State and logs: `<main repo>/.devkit/runtime/<instance>/state.json` and `<service>.log`. `devkit:clean-temp` never touches `.devkit/`.
- Records: `up` writes a `runtime` record with `record_run.py` (see [record_run.py](../../check/scripts/record_run.py)): `.devkit/work/<task>/runs/` with `--task`, else `.devkit/runs/`.
- The harness stops only the process groups it started. `down` waits for each port to free and warns when something else still holds it.

## Guard

The devkit guard still asks before direct server commands (`npm run dev`, `bootRun` …). A repo can let specific ones through in `.devkit/guard.json`; each pattern must match a whole command segment:

```json
{"allow_server": [{"pattern": "npm run dev( .*)?", "reason": "web dev server for screen checks"}]}
```
