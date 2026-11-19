# PHP design principles

Language rows for [design-principles.md](../design-principles.md); apply its How to use and Repo decisions.

| Principle | Signal in the change | What to check |
|---|---|---|
| Strict types | New file without `declare(strict_types=1)` where the repo uses it; untyped parameters and returns | Type declarations |
| Dependency injection | `new` of services or static facades inside domain code | The framework container (Laravel, Symfony) |
| Separation of concerns | SQL or business logic in templates or controllers | Service, repository or model layer the repo uses |
| PSR | Autoloading or naming that breaks PSR-4/PSR-12 where the repo follows them | Follow the repo's standard |
| SOLID rows | As in Java | — |
