# Design principles by language

Contents: How to use · Repo decisions · Common · Language files

Candidate principles analyze may **recommend** for a change. They are not rules and not requirement items: a project may decline any of them. Rows hold only the signal that makes a principle relevant and what to look at; the principles themselves are general knowledge and are not explained here.

Languages: GitHub Octoverse 2025 top 10 by contributors (TypeScript, Python, JavaScript, Java, C#, PHP, Shell, C++, HCL, Go) plus Kotlin.

## How to use

1. Language and shape come from the **changed files**, not the repo: a Java API and a TypeScript web app in one repo get different rows, and function-style or module-style code gets no class rows.
2. Read the repo decisions (next section). Skip every principle the repo declined.
3. Read only the [language files](#language-files) of the changed files' languages; a language not listed gets only the Common table. From the Common table (not for Shell or HCL) and the language table, keep only rows whose signal appears **in this change**. At most 3. No signal, no section. When a language file you read has a row pointing to Java ("as in Java", "Same as Common and Java"), also read [java.md](design-principles/java.md).
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

## Language files

| Language | File |
|---|---|
| TypeScript, JavaScript | [typescript-javascript.md](design-principles/typescript-javascript.md) |
| Python | [python.md](design-principles/python.md) |
| Java | [java.md](design-principles/java.md) |
| Kotlin | [kotlin.md](design-principles/kotlin.md) |
| C# | [csharp.md](design-principles/csharp.md) |
| PHP | [php.md](design-principles/php.md) |
| C++ | [cpp.md](design-principles/cpp.md) |
| Go | [go.md](design-principles/go.md) |
| Shell | [shell.md](design-principles/shell.md) |
| HCL (Terraform) | [hcl.md](design-principles/hcl.md) |
