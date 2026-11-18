# Design principles by language

Contents: How to use · Repo decisions · Common · TypeScript and JavaScript · Python · Java · Kotlin · C# · PHP · C++ · Go · Shell · HCL (Terraform)

Candidate principles analyze may **recommend** for a change. They are not rules and not requirement items: a project may decline any of them. Rows hold only the signal that makes a principle relevant and what to look at; the principles themselves are general knowledge and are not explained here.

Languages: GitHub Octoverse 2025 top 10 by contributors (TypeScript, Python, JavaScript, Java, C#, PHP, Shell, C++, HCL, Go) plus Kotlin.

## How to use

1. Language and shape come from the **changed files**, not the repo: a Java API and a TypeScript web app in one repo get different rows, and function-style or module-style code gets no class rows.
2. Read the repo decisions (next section). Skip every principle the repo declined.
3. From the Common table (not for Shell or HCL) and the language table, keep only rows whose signal appears **in this change**. At most 3. No signal, no section.
4. Write them in the analysis doc's "Design principles (recommendation)" section with the evidence `file:line`. Never turn them into requirement items or verification items.
5. A recommended principle with no repo decision yet gets repo status `undecided` and one question at the 🛑 gate: "adopt for `<layer>`?" (adopt / decline / decide later). Once recorded it is not asked again.

## Repo decisions

- Where: a `## Design principles` section in the layer doc of the changed path (`docs/rules/<layer>.md`), as `Principle | Decision | Reason · date` with Decision `adopted` or `declined`.
- `declined`: never recommend it again for that layer. `adopted`: still recommend only when its signal appears, marked "adopted".
- Writing the user's answer into the layer doc is a `docs/rules` change: it follows the [rules-change gate](cross-check.md#rules-change-gate) (evidence type `decision`) and becomes the last docs step of the implementation plan (analyze itself writes only the analysis doc).
- `docs/rules/` exists but no layer doc covers the path: in the same gate question, offer to create that layer doc (one doc per layer, not `common.md`). If accepted, the docs step creates it from the setup [layer-doc template](../../setup/references/templates.md#layer-doc) with only the `Applies to:` path, the language facts seen in the change, and the `## Design principles` section; it links it from `docs/rules/README.md`. If declined, record the answer only in the analysis doc's decision log.
- No `docs/rules/` at all: record the answer only in the analysis doc's decision log. Never create `docs/rules/` for this (that is `devkit:setup`).

## Common

| Principle | Signal in the change | What to check |
|---|---|---|
| Single responsibility | A class, module or function gains a second reason to change (e.g. a service starts formatting output or calling a new external system) | Can the new concern live in its own unit, following an existing split in the repo |
| DRY | The change copies a block that already exists (same query, same validation, same mapping) | Is there a shared helper to reuse; is the duplication the same knowledge or only similar text |
| KISS · YAGNI | New abstraction, option, flag or extension point with one caller | Does a requirement item need it now |
| Separation of concerns | Business logic added to a controller, view, template, SQL or config | Which layer the repo puts that logic in |
| Composition over inheritance | New subclass to reuse a few methods, or an inheritance chain of 3+ levels | Would a field or a helper do |
| Law of Demeter | Chains reaching through several objects (`a.getB().getC().do()`) in new code | Ask the nearest object instead |
| Encapsulation | Mutable internal state made public or returned directly (collections, setters added for one caller) | Can callers get a copy, read-only view or intent method |

## TypeScript and JavaScript

| Principle | Signal in the change | What to check |
|---|---|---|
| Immutability | Mutating arguments, shared state or store objects in place | Return new objects; follow the repo's state library rules |
| Pure functions | Logic mixed with I/O, DOM or fetch in one function | Split the computation so it can be called without side effects |
| Type-level contracts (TS) | `any`, unchecked casts, optional fields used as required | Narrow the type or validate at the boundary |
| Module boundaries | Deep imports into another feature's internals | Import from the module's public entry |
| Class rows (SOLID, LSP) | Only when the changed code is class-based | Same as Common and Java |

## Python

| Principle | Signal in the change | What to check |
|---|---|---|
| Explicit over implicit | Magic via `getattr`/`globals`, wildcard imports, hidden side effects at import time | Make the dependency visible |
| EAFP | Long chains of pre-checks before an operation that can fail | `try/except` on the specific exception |
| Duck typing · protocols | `isinstance` ladders on concrete types | A protocol or the expected method |
| Properties | Java-style `get_x/set_x` added | `@property` |
| Dataclasses | Classes that only hold fields with hand-written `__init__`/`__eq__` | `@dataclass` or the repo's model type |
| Class rows (SOLID) | Only when the change adds or extends classes | Same as Common |

## Java

| Principle | Signal in the change | What to check |
|---|---|---|
| Open-closed | New `if/switch` branch on a type code in a place that already has several | A strategy or polymorphic method, if the repo already uses one |
| Liskov substitution | Subclass overriding to throw, no-op or narrow behavior | Callers of the base type still work |
| Interface segregation | Adding a method to a wide interface that most implementers leave empty | A smaller interface |
| Dependency inversion | `new` of a service, repository or client inside business code | Injection the repo already uses (constructor injection in Spring) |
| Immutable values | Value objects with setters, mutable collections exposed | `final` fields, records, unmodifiable views |
| Static factories · builders | Constructors with many same-typed parameters | Builder or named factory |

## Kotlin

| Principle | Signal in the change | What to check |
|---|---|---|
| Null safety | `!!` or platform types from Java passed on unchecked | Handle null at the boundary |
| `val` over `var` | New mutable properties or `MutableList` exposed | Read-only types in the public API |
| Data and sealed classes | Value holders written as regular classes; type codes with `when` and `else` | `data class`; `sealed` hierarchy so `when` is exhaustive |
| Extension functions | Utility classes of static helpers | Extensions, if the repo uses them |
| Java rows | SOLID rows apply as in Java | — |

## C#

| Principle | Signal in the change | What to check |
|---|---|---|
| Dependency inversion | `new` of services inside business code | The repo's DI container registration |
| Properties and encapsulation | Public fields, public setters on domain state | `{ get; private set; }` or `init` |
| Records · immutability | Value objects with mutable state | `record` |
| Async all the way | `.Result` or `.Wait()` on tasks | `await` through the call chain |
| `IDisposable` | New disposable resource without `using` | `using` declaration |
| SOLID rows | As in Java | — |

## PHP

| Principle | Signal in the change | What to check |
|---|---|---|
| Strict types | New file without `declare(strict_types=1)` where the repo uses it; untyped parameters and returns | Type declarations |
| Dependency injection | `new` of services or static facades inside domain code | The framework container (Laravel, Symfony) |
| Separation of concerns | SQL or business logic in templates or controllers | Service, repository or model layer the repo uses |
| PSR | Autoloading or naming that breaks PSR-4/PSR-12 where the repo follows them | Follow the repo's standard |
| SOLID rows | As in Java | — |

## C++

| Principle | Signal in the change | What to check |
|---|---|---|
| RAII | Raw `new`/`delete`, manual `close`/`unlock` | Smart pointers, scoped guards |
| Rule of zero/five | Class owning a resource with only some of copy/move/destructor defined | Define all or none |
| Const correctness | New methods or parameters that do not modify but are not `const` | `const` and `const&` |
| Ownership in interfaces | Raw pointer parameters with unclear ownership | `unique_ptr` for transfer, reference for borrow |
| SOLID rows | Class hierarchies with virtual methods | As in Java |

## Go

| Principle | Signal in the change | What to check |
|---|---|---|
| Small interfaces at the consumer | A large interface defined next to its only implementation | Define a small interface where it is used |
| Errors as values | Ignored errors (`_ =`), `panic` for expected failures, lost context | Return and wrap with `%w` |
| Composition | Struct embedding used to fake inheritance | Explicit fields or small interfaces |
| Context | Blocking calls or goroutines without `context.Context` | Pass the caller's context |
| Package boundaries | `util`/`common` packages growing; import cycles worked around | Package by what it provides |

## Shell

Idiom rows only: no Common table, no OOP or SOLID rows. Recommend only when a script changes.

| Principle | Signal in the change | What to check |
|---|---|---|
| Fail fast | New script or long block without `set -euo pipefail` (or the repo's equivalent) | Unchecked failures continuing silently |
| Quoting | Unquoted variable expansions, word splitting on paths | `"$var"`, arrays for argument lists |
| Idempotency | Steps that fail or duplicate on re-run (`mkdir`, appends) | `mkdir -p`, existence checks |

## HCL (Terraform)

Idiom rows only: no Common table, no OOP or SOLID rows. Recommend only when infrastructure code changes.

| Principle | Signal in the change | What to check |
|---|---|---|
| DRY via modules | The same resource block copied across environments | An existing module or `for_each` |
| Separation of environments | Environment values hard-coded in resources | Variables and per-environment tfvars or workspaces |
| Explicit dependencies | Ordering relied on implicitly | References or `depends_on` |
| Pinned versions | Provider or module without version constraints | Pin as the repo does |
