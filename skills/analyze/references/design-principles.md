# Design principles

Candidates analyze may **recommend**; a project may decline any of them. Only names are listed.

## How to use

1. Judge language and shape from the **changed files**, not the repo. Function-style or module-style code gets no class principles (SOLID, inheritance).
2. Skip every principle the repo declined (next section).
3. Keep only names whose signal appears **in this change**, suggesting only what the repo already uses (its DI, state library, module style). At most 3. No signal, no section.
4. Write them in the analysis doc's "Design principles (recommendation)" section with the evidence `file:line`. Never turn them into requirement items or verification items.
5. A recommended principle with no repo decision gets repo status `undecided` and one question at the 🛑 gate: "adopt for `<layer>`?" (adopt / decline / decide later). Once recorded it is not asked again.

## Names to consider

- Common (not Shell or HCL): single responsibility, DRY, KISS · YAGNI, separation of concerns, composition over inheritance, Law of Demeter, encapsulation
- Class-based code: SOLID
- TypeScript · JavaScript: immutability, pure functions, type-level contracts, module boundaries
- Python: explicit over implicit, EAFP, protocols, properties, dataclasses
- Java: immutable values, static factories · builders
- Kotlin: null safety, `val` over `var`, data · sealed classes
- C#: async all the way, records, `IDisposable`
- PHP: strict types, PSR
- C++: RAII, rule of zero/five, const correctness, ownership in interfaces
- Go: small consumer-side interfaces, errors as values, `context`, package boundaries
- Shell (idioms only): fail fast, quoting, idempotency
- HCL (idioms only): modules, per-environment values, explicit dependencies, pinned versions

## Repo decisions

- Where: a `## Design principles` section in the layer doc of the changed path (`docs/rules/<layer>.md`), as `Principle | Decision | Reason · date` with Decision `adopted` or `declined`.
- `declined`: never recommend it again for that layer. `adopted`: still recommend only when its signal appears, marked "adopted".
- Writing the user's answer into the layer doc is a `docs/rules` change: it follows the [rules-change gate](cross-check.md#rules-change-gate) (evidence type `decision`) and becomes the last docs step of the implementation plan (analyze itself writes only the analysis doc).
- `docs/rules/` exists but no layer doc covers the path: in the same gate question, offer to create that layer doc (one doc per layer, not `common.md`). If accepted, the docs step creates it from the setup [layer-doc template](../../setup/references/templates.md#layer-doc) with only the `Applies to:` path, the language facts seen in the change, and the `## Design principles` section; it links it from `docs/rules/README.md`. If declined, record the answer only in the analysis doc's decision log.
- No `docs/rules/` at all: record the answer only in the analysis doc's decision log. Never create `docs/rules/` for this (that is `devkit:setup`).
