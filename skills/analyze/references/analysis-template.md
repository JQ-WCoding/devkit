# Analysis doc template

Write to `<work folder>/<task ID>/analysis.md`. Delete sections that do not apply. Mark estimates `Estimate:` and unknowns `needs confirmation`.

```markdown
# <task ID> <title>

- Source: <issue link · file · paste> · date read · type: feature | change | bug | investigation
- Branch: <current or proposed> · base commit: <short SHA>

## Requirement summary
Split the requirement into numbered items. Quote the source wording briefly and write interpretations separately.

| No. | Requirement | Source wording | Interpretation · question | Done when (evidence type) |
|---|---|---|---|---|

Cross-check mode: the status per item from `cross-check/results.md`, and a "Not turned into rules" list from `not-rules.md`.

## Terms
Requirement terms ↔ code terms (table, class, screen names). Only unfamiliar domain terms.

| Term | Code term | Evidence (glossary row, owner source, `file:line`) |
|---|---|---|

## Current behavior
What happens today for this requirement, as `file:line` in the order entry point (screen · API · batch · message) → processing → storage.

## If it is a bug
- Symptom · reproduction steps · expected behavior
- Cause, with evidence (`file:line`, logs, data). If not confirmed, the hypothesis and how to check it
- Whether the same cause exists elsewhere

## Differences from the requirement
| No. | Current | After | Where to change |
|---|---|---|---|

## Impact
| Area | Target | Change | Evidence |
|---|---|---|---|
| Screen · API · batch · DB · external integration · permission · config · docs | | add/modify/delete | |

### Keep-as-is list
Things that do not change but could break: other features using the same tables, APIs or components, side effects, pre-save validation, permission scope. Used for the regression check after implementation.

## Risk check
Only items whose signal appears. | Item | Question | Current · answer (evidence) | Action |

## Design principles (recommendation)
Not requirement items; develop and the verifier do not judge against them. Only principles whose signal appears in this change, at most 3, per `design-principles.md`. Repo status from the layer doc's `## Design principles` section.

| Principle | Signal (`file:line`) | Suggestion | Repo status (adopted · undecided) |
|---|---|---|---|

## Implementation plan
Precedent: <existing commit or file to follow>

In order. Per step: file to change · one-line change · how to verify.

## DB change (if any)
Objects · change · impact on existing data · location of change SQL and rollback SQL. A human runs them.

## Executable premises
Statements the change relies on that a run can check (API call, screen action, read-only query). develop executes each before reporting; one not executed stays `not run`. Kind: `premise` (default; rows without one) · `keep` (a keep-as-is item a run can observe) · `repro` (bug: fails before the fix). `keep`/`repro` run on pre-change code before the first edit (Before), then after.

| ID | Kind | Premise | How to execute | Before | After · run record |
|---|---|---|---|---|---|

## Verification plan
| Check | Method (automated check · screen · API · DB query) | Data |
|---|---|---|

## Needs confirmation
- [ ] Decisions a person must make. If there are options, list them with a recommendation.

## Decision log
The user's wording verbatim; your reading apart. Only the wording counts as a decision.

| Date | Question | Answer (verbatim) | Interpretation | Re-check when |
|---|---|---|---|---|
```
