# Java design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Open-closed | New `if/switch` branch on a type code in a place that already has several | A strategy or polymorphic method, if the repo already uses one |
| Liskov substitution | Subclass overriding to throw, no-op or narrow behavior | Callers of the base type still work |
| Interface segregation | Adding a method to a wide interface that most implementers leave empty | A smaller interface |
| Dependency inversion | `new` of a service, repository or client inside business code | Injection the repo already uses (constructor injection in Spring) |
| Immutable values | Value objects with setters, mutable collections exposed | `final` fields, records, unmodifiable views |
| Static factories · builders | Constructors with many same-typed parameters | Builder or named factory |
