# Python design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Explicit over implicit | Magic via `getattr`/`globals`, wildcard imports, hidden side effects at import time | Make the dependency visible |
| EAFP | Long chains of pre-checks before an operation that can fail | `try/except` on the specific exception |
| Duck typing · protocols | `isinstance` ladders on concrete types | A protocol or the expected method |
| Properties | Java-style `get_x/set_x` added | `@property` |
| Dataclasses | Classes that only hold fields with hand-written `__init__`/`__eq__` | `@dataclass` or the repo's model type |
| Class rows (SOLID) | Only when the change adds or extends classes | Same as Common |
