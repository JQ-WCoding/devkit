# Blueprint: project work flow skill (project-flow)

A skill that keeps the common `devkit:analyze`/`devkit:develop` flow and adds only **the steps that repeat in this repo**. Do not duplicate the common flow. Name it after this repo's task (e.g. `screen-dev`, `pg-integration`, `mes-report`).

## Conditions to build (evidence)

One of the following has repeated 3+ times.

- A fixed-format input (slide design spec, screen definition, spreadsheet requirements, partner integration spec) must be read the same way every time
- A verdict missing from the common analysis doc is needed every time (spec status verdict, menu/permission/code registration, partner auth procedure)
- The same project-specific verification follows implementation (mockup comparison, partner test server calls, equipment simulator)

## Files to create

- `SKILL.md` — skeleton below
- `input-template.md` (optional) — mapping table from the specific input format to sections of the analysis doc
- `glossary.md` (optional) — input terms ↔ code terms. Only mappings the user confirmed
- `evals/evals.json`

## SKILL.md skeleton

```markdown
---
name: {{task name}}
description: When developing {{target}} from {{specific input}}, runs the devkit:analyze/develop flow plus this repo's own steps ({{list of step names}}). Use for requests like "{{2–3 real request phrases}}".
argument-hint: "{{input format}}"
---

# {{task name}}

The flow follows `devkit:analyze` → 🛑 → `devkit:develop`. Below are only the steps added in between.

| Inserted at | Specific step | Output |
|---|---|---|
| analyze step 0 | {{reading input: method per format}} | "Requirement summary" of the analysis doc |
| after analyze step 3 | {{specific verdict}} | Section added to the analysis doc |
| develop step 3 | {{specific verification}} | "Verification plan" of the analysis doc |

## {{one section per specific step}}

Only judgment criteria, commands and prohibitions. Rules are links to `docs/rules/`.
```

## Leave out

- Descriptions of common-flow steps (analysis format, risk check, DB change SQL, report format) — they are in `devkit:analyze`/`develop`.
- Judgments used only once — the analysis doc's "Decision log" is enough.
