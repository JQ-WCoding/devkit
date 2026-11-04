---
name: analyze
description: Before changing code, turn a requirement, issue or bug (any source) into an analysis doc — current-code trace, impact, common risk check, implementation plan — and get approval. Use for "analyze this issue", "where do I fix this", "find the bug cause", "check impact".
argument-hint: "<issue link | file path | requirement> [task ID]"
---

# Analyze

Decide what to change, why and how far before touching code. This skill **does not edit files** (it writes only the analysis doc). Anything the input cannot settle is not filled in by guesswork; mark it `needs confirmation` and ask at the 🛑 gate.

| Reference | When |
|---|---|
| [analysis-template.md](references/analysis-template.md) | Analysis doc format |
| [risk-checklist.md](references/risk-checklist.md) | Step 4 risk check |

## 0. Read the input

Any task source is fine.

| Input | How to read |
|---|---|
| Pasted text, images, attachments | Read as is. Open images with Read |
| Local file (Markdown, Obsidian note, PDF, document) | Read the path. Look for linked notes and attachments in the same folder |
| GitHub/GitLab issue | `gh issue view <number> --comments` / `glab issue view <number> --comments` |
| Jira, Notion, Confluence, Google Docs and other links | Read with an MCP tool or CLI connected to this session. If none, ask the user to paste the content |

- Write to a tracker (comments, status changes) only on request.
- Task ID: argument → issue key (`ABC-123`, `#45`) → date plus short name (`2026-11-04-refund-partial`).
- Work folder: the local work-folder rule in `docs/rules/` if any, else `<repo>/.devkit/work/`. If Git would track it (`git check-ignore -q` fails), add `.devkit/` to `.git/info/exclude` and say so.

## 1. Break down the requirement

Split the requirement into numbered items and keep the source wording apart from your interpretation. For vague wording ("as appropriate", "like before", "etc."), write the interpretation and list it under `needs confirmation`. Set the type: feature | change | bug | investigation.

## 2. Trace the current code

- Skim the repo rules (`CLAUDE.md`, `docs/rules/`) first to align terms and structure.
- Follow entry points (screen, API, batch, message consumer) → processing → storage (table, file, external) as `file:line`. With several entry points or more than 10 files to scan, hand them to `devkit:code-reader` in parallel, one per entry point. Smaller than that, read directly.
- With dynamic calls (string paths, reflection, config routing), do not conclude "unused" from a text search alone.
- **Bug**: define the minimal reproduction steps and confirm the cause with evidence (code, logs, data). If not confirmed, write the hypothesis and how to check it. Look for the same cause elsewhere. If production data must be queried, use read-only queries only, after confirming the target DB.

## 3. Differences and impact

- Per requirement item: `current / after / where to change`. Items with no change are marked as untouched.
- Impact: screens, APIs, batches, DB, external integrations, permissions, config, docs. Record other features that use the same tables, APIs or shared components as the **keep-as-is list**.

## 4. Risk check

From [risk-checklist.md](references/risk-checklist.md), pick **only items whose signal appears** and write the question and answer (evidence or `needs confirmation`). Do not list items that do not apply.

## 5. Implementation plan

- Order: schema and data migration → data access (queries, mappers, repositories) → domain and services → API → UI → config and docs. Follow the repo rules if they set an order.
- Per step: files to change, one-line description, how to verify. Write the existing implementation to follow (a recent commit or file of the same kind) as `Precedent:`.
- If there is a DB change, decide where the change SQL and rollback SQL go (a human runs them).
- Verification plan: automated checks (to pick from `devkit:check`), screen and API checks, test data, regression check of the keep-as-is list.

## 🛑 Approval

Save the analysis doc and show a summary (number of requirements, places that change, cautions from the risk check, whether there is a DB change, expected scope). Ask the `needs confirmation` items with AskUserQuestion (with options and a recommendation). Record the answers with the date in the doc's "Decision log".

If the user only wanted the analysis, stop here. If they say to proceed, move on to `devkit:develop`.

## Report

Analysis doc path, number of requirement items, remaining `needs confirmation`, number of implementation steps. For a bug, state clearly whether the cause is confirmed ("confirmed" / "Hypothesis: …").
