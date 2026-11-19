---
name: analyze
description: Before changing code, turn a requirement, issue or bug (any source) into an analysis doc and get approval; on request, cross-checks intent sources against current state with separate analysts. Use for "analyze this issue", "where do I fix this", "find the bug cause", "check impact", "cross-check this rules draft".
argument-hint: "<issue link | file path | requirement> [task ID]"
---

# Analyze

Decide what to change, why and how far before touching code. This skill **does not edit files** (it writes only the analysis doc). Anything the input cannot settle is not filled in by guesswork; mark it `needs confirmation` and ask at the 🛑 gate.

| Reference | When |
|---|---|
| [analysis-template.md](references/analysis-template.md) | Analysis doc format |
| [risk-checklist.md](references/risk-checklist.md) → [risk-checklist/](references/risk-checklist/) | Step 4: the area index, then only the area files whose signal appears |
| [design-principles.md](references/design-principles.md) → [design-principles/](references/design-principles/) | Step 4, unless only prose docs or images change: core, then only the changed files' language files |
| [cross-check.md](references/cross-check.md) | Cross-check mode, glossary format, rules-change gate |

## 0. Read the input

Read any source with the tools connected to this session (`gh`/`glab` for issues); if none can read it, ask the user to paste it.

- Write to a tracker (comments, status changes) only on request.
- Task ID: argument → issue key (`ABC-123`, `#45`) → date plus short name (`2026-11-04-refund-partial`).
- Work folder: the local work-folder rule in `docs/rules/` if any, else `<repo>/.devkit/work/`. If Git would track it (`git check-ignore -q` fails), add `.devkit/` to `.git/info/exclude` and say so.

## 1. Break down the requirement

Split the requirement into numbered items and keep the source wording apart from your interpretation. For vague wording ("as appropriate", "like before", "etc."), write the interpretation and list it under `needs confirmation`. Set the type: feature | change | bug | investigation.

## 2. Trace the current code

- Skim the repo rules (`CLAUDE.md`, `docs/rules/`) first to align terms and structure; read `docs/rules/glossary.md` in full if it exists.
- **Cross-check mode** (the user asks for it; offer it once when the input is a `docs/rules` draft or touches a glossary term): follow [cross-check.md](references/cross-check.md) instead of tracing here first. Only its `proceed` items get a plan; the rest go to the 🛑 gate.
- Follow entry points (screen, API, batch, message consumer) → processing → storage (table, file, external) as `file:line`. With several entry points or more than 10 files to scan, hand them to `devkit:code-reader` in parallel, one per entry point. Smaller than that, read directly.
- With dynamic calls (string paths, reflection, config routing), do not conclude "unused" from a text search alone.
- **Bug**: define the minimal reproduction steps and confirm the cause with evidence (code, logs, data). If not confirmed, write the hypothesis and how to check it. If two earlier fixes resting on the same premise failed, write that premise down and check it directly before planning a third. Look for the same cause elsewhere. If production data must be queried, use read-only queries only, after confirming the target DB.

## 3. Differences and impact

- Per requirement item: `current / after / where to change`. Items with no change are marked as untouched.
- Impact: screens, APIs, batches, DB, external integrations, permissions, config, docs. Record other features that use the same tables, APIs or shared components as the **keep-as-is list**.

## 4. Risk check

Read the area index in [risk-checklist.md](references/risk-checklist.md), then only the area files whose signal appears. Pick **only items whose signal appears** and write the question and answer (evidence or `needs confirmation`). Do not list items that do not apply.

Then design principles, skipped when the change touches only prose docs or images: read [design-principles.md](references/design-principles.md) and only the language files of the changed files, judge the language and code shape of the **changed files**, skip principles the layer doc declined, and recommend at most 3 whose signal appears in this change. They are recommendations, not requirement items: develop and the verifier do not judge against them. No signal, no section.

## 5. Implementation plan

- Order: schema and data migration → data access (queries, mappers, repositories) → domain and services → API → UI → config and docs. Follow the repo rules if they set an order.
- Per step: files to change, one-line description, how to verify. Write the existing implementation to follow (a recent commit or file of the same kind) as `Precedent:`.
- If there is a DB change, decide where the change SQL and rollback SQL go (a human runs them).
- Verification plan: automated checks (run through `devkit:check-runner`), screen and API checks, test data, regression check of the keep-as-is list.

## 🛑 Approval

Save the analysis doc and show a summary (number of requirements, places that change, cautions from the risk check, whether there is a DB change, expected scope).

Stop for approval only when a human must decide: `needs confirmation` items that a read or run cannot settle, cross-check questions, a DB change, a change to shared modules or components, a delete, an `undecided` recommended design principle, or the user asked only for the analysis. A recommended `undecided` design principle gets one question on adopting it for that layer. Ask those with AskUserQuestion (with options and a recommendation) and record the answers with the date in the doc's "Decision log", the user's wording apart from your reading. Otherwise log `no gate: <reason>` there and go on.

Either way, copy the doc to `analysis.approved.md` next to it (again after any later approved amendment); the verifier judges against that copy. Then move on to `devkit:develop`, unless the user only wanted the analysis.

## Report

Analysis doc path, number of requirement items, remaining `needs confirmation`, number of implementation steps. For a bug, state clearly whether the cause is confirmed ("confirmed" / "Hypothesis: …").
