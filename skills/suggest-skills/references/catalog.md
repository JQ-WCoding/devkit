# Suggestion catalog

Contents: Principles · Agents · Skills · Rule rows · Not suggested

## Principles

- Suggest only when a condition is met **by evidence**: fingerprint numbers, files and commits, tasks repeated in this conversation, repeated tasks the user described.
- Do not suggest many at once. At most 3 recommended; the rest go on one line each as "next candidates".
- Do not build anything with the same role as what devkit already provides (`analyze`, `develop`, `check`, `commit`, `push`, `pr-publish`, `peer-review`, `parallel-work`, `clean-temp`, `code-reader`). User-invoked-only skills such as `check` do not appear in the session skill list. If this repo has its own check or publish procedure, first suggest adding it as rows in `docs/rules/`.
- State the cost: number of files to create, external tools or MCP needed, what must be maintained.

## Agents

All use `model: sonnet`, read-only tools, no file edits, `file:line`-centered reports, and separate confirmed from guessed. Blueprints are in `blueprints/`.

| Agent | Condition (evidence) | Blueprint |
|---|---|---|
| `db-analyst` | The fingerprint's "DB traces" shows dozens or more schema definitions (migrations, init scripts, DDL baselines, ORM entities, SQL mappers, procedures), and history often has tasks changing DB objects | `blueprints/db-analyst.md` |
| `knowledge-reader` | Business terminology or decision docs exist (wiki, notes folder, docs site, business docs under `docs/` — any tool), and tasks ask about business meaning | `blueprints/knowledge-reader.md` |
| `spec-analyst` | Developing from fixed-format plans, design specs or screen definitions recurs, and the format does not fit `analysis-template` alone | `blueprints/spec-analyst.md` |

## Skills

| Skill | Condition (evidence) | Blueprint |
|---|---|---|
| Project work flow | On top of the common `devkit:analyze`/`develop` flow, repo-specific steps (reading a specific spec format, status verdicts, menu and permission registration, mockup comparison, etc.) have repeated 3+ times | `blueprints/project-flow.md` |
| `clean-temp` protect globs (no new skill) | Temp-file cleanup was requested and this repo keeps local work folders (specs, mockups, work SQL, decks) that `devkit:clean-temp` would not know to protect | Write `.devkit/clean-temp/config.json` as `{"protect": ["<glob>", ...]}`: globs match repo-relative paths, `*` also matches `/`, a trailing `/` means everything under it (e.g. `"docs/design/[!_]*"`) |
| `visual-docs` | Requests to document flowcharts, sequences or ERDs recur, or `docs/` has several Mermaid docs | `blueprints/visual-docs.md` |
| Recurring maintenance procedure | Dozens of commits with the same verb (dependency bumps, release prep, data correction, certificate rotation, etc.) with the same checks every time | Follow the structure of `blueprints/tool-skill.md` (procedure, commands, checks, prohibitions) |
| Tool skill | An external tool that is hard to install or configure (report designer, physical device, in-house CLI, etc.) is used repeatedly and needs the same explanation each time | `blueprints/tool-skill.md` |

## Rule rows

Suggest only candidates that pass the adoption criteria in `pinpoint-checklist.md`. Add rows to the matching `docs/rules/<layer>.md` in the same style; if the layer doc does not exist, ask first whether to create it.

## Not suggested

- Skills holding only general development knowledge (generic coding style, language tutorials).
- Turning a one-off task into a skill. Up to the second time, a rule row or note is enough.
- Agents that need write access. The main agent does writes.
- Names identical to other plugin or user-level skills. If they overlap, rename or state in each description when not to use it.
