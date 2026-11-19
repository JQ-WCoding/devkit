# Shell design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

Idiom rows only: no Common table, no OOP or SOLID rows. Recommend only when a script changes.

| Principle | Signal in the change | What to check |
|---|---|---|
| Fail fast | New script or long block without `set -euo pipefail` (or the repo's equivalent) | Unchecked failures continuing silently |
| Quoting | Unquoted variable expansions, word splitting on paths | `"$var"`, arrays for argument lists |
| Idempotency | Steps that fail or duplicate on re-run (`mkdir`, appends) | `mkdir -p`, existence checks |
