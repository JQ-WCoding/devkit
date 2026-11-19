# Kotlin design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Null safety | `!!` or platform types from Java passed on unchecked | Handle null at the boundary |
| `val` over `var` | New mutable properties or `MutableList` exposed | Read-only types in the public API |
| Data and sealed classes | Value holders written as regular classes; type codes with `when` and `else` | `data class`; `sealed` hierarchy so `when` is exhaustive |
| Extension functions | Utility classes of static helpers | Extensions, if the repo uses them |
| Java rows | SOLID rows apply as in Java | — |
