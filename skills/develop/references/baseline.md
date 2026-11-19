# Baseline: keep and repro rows

```bash
B="${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/baseline.py"
python3 -I "$B" before --repo <repo> [--task <ID>] --id <row ID> --kind keep|repro [--ignore <regex> ...] [--repro-path <file> ...] (-- <command> | --from-file <output> [--match <regex>])
python3 -I "$B" after  --repo <repo> [--task <ID>] --id <row ID> [--from-file <output>]
```

- Run every `before` before the first edit; it stamps HEAD and the paths already changed, and a capture taken after editing shows up in `verify`. For a `repro`, only its own new test may exist yet, declared with `--repro-path` (any other changed path fails the row); capture `keep` rows before writing it.
- What to run, by repo shape: existing tests near the keep-as-is items; else a command with fixed inputs (CLI output, API call, read-only query); else a saved output from any tool via `--from-file`. Nothing runnable, or base not runnable: the row is `not run`.
- `keep` runs twice; if the outputs differ it is `unstable`. Add `--ignore` rules for times, IDs or order under a new ID before any edit.
- `after` reuses the stored command and ignore rules. `keep`: `same`/`differs`; `repro`: `green`/`red` (a `--from-file` repro needs `--match <regex>`: red while found, green once absent).
- Capture the smallest output that shows the behavior, never credentials. Outputs stay in the work folder; records keep hashes.
- Limit: this catches drift and self-fitting, not a deliberate workaround such as stashing edits before capture.
