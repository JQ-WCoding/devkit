# C# design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Dependency inversion | `new` of services inside business code | The repo's DI container registration |
| Properties and encapsulation | Public fields, public setters on domain state | `{ get; private set; }` or `init` |
| Records · immutability | Value objects with mutable state | `record` |
| Async all the way | `.Result` or `.Wait()` on tasks | `await` through the call chain |
| `IDisposable` | New disposable resource without `using` | `using` declaration |
| SOLID rows | As in Java | — |
