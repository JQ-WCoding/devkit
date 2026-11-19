# TypeScript and JavaScript design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Immutability | Mutating arguments, shared state or store objects in place | Return new objects; follow the repo's state library rules |
| Pure functions | Logic mixed with I/O, DOM or fetch in one function | Split the computation so it can be called without side effects |
| Type-level contracts (TS) | `any`, unchecked casts, optional fields used as required | Narrow the type or validate at the boundary |
| Module boundaries | Deep imports into another feature's internals | Import from the module's public entry |
| Class rows (SOLID, LSP) | Only when the changed code is class-based | Same as Common and Java |
