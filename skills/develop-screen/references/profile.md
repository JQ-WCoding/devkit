# Repo profile

`<repo>/.devkit/develop-screen/profile.md` (local and Git-excluded like the rest of `.devkit/`). It holds what differs per repo, so the skill body stays the same everywhere. Every section is optional; a missing one uses the default. Link the repo's rules instead of copying them.

| Section | Holds | Default |
|---|---|---|
| Language | Document language for the spec, questions and report | The language of the repo's `docs/rules/`, else the user's |
| Folders | Work folder per screen, SQL folder, deck folder | `.devkit/work/<screen ID>/` (spec, `img/`, SQL together), deck in `.devkit/work/_deck/<name>/`. A work or deck folder set outside `.devkit/` is kept out of Git at step 0 |
| Status legend | Symbols or words the documents use and what they mean, passed as `--status` (e.g. `★=new,☆=modify`); conditional meanings in prose | Korean and English status words only |
| Screen ID label | A regex for the ID label if the documents use another one (`--id-label`) | 화면ID, 화면코드, 프로그램ID, Screen ID, Program ID, Page ID |
| Glossary | Confirmed document term ↔ code term pairs with evidence (or a link to a glossary file) | none |
| Layers and rules | Implementation order and the rules doc for each layer | schema baseline → data access → service → API → UI; `docs/rules/` |
| Copy sources | A guide or table of template screens by layout; popup conventions | Pick from existing screens |
| Tracing hints | How screens call the back end (query IDs, rule paths, dynamic routes) so step 2 can trace them | Generic search |
| DB | DB agent name, schema baseline folder, dictionary queries, menu/permission/message rules | Main session, read-only tool |
| SQL files | Numbered files after `01_ddl.sql` (codes, menus, permissions) | `00_check`, `01_ddl`, `99_rollback` |
| Checks | Which checks to pick and repo quirks (lint config, JDK) | `devkit:check-runner` discovery |
| Examples | Past screens worth consulting (cases, not rules) | none |

Write a new profile only after the user approves it, from what step 2–4 learned and the repo rules. Keep it short: facts and links, no copies of `docs/rules/`.
