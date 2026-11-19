# C++ design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| RAII | Raw `new`/`delete`, manual `close`/`unlock` | Smart pointers, scoped guards |
| Rule of zero/five | Class owning a resource with only some of copy/move/destructor defined | Define all or none |
| Const correctness | New methods or parameters that do not modify but are not `const` | `const` and `const&` |
| Ownership in interfaces | Raw pointer parameters with unclear ownership | `unique_ptr` for transfer, reference for borrow |
| SOLID rows | Class hierarchies with virtual methods | As in Java |
