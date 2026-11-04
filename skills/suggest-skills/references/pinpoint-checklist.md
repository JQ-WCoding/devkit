# Pinpoint checklist

Contents: Adoption criteria · Six sources · Questions by area · Candidate format · Discard

Used by both analysis subagents and the main agent. Raise candidates only with evidence.

## Adoption criteria

A candidate becomes a rule row only if all three hold.

1. **Specific to this project** — general knowledge could not guess it (this repo's module names, path shapes, naming, exceptions).
2. **Breaking it costs something** — leads to defects, rework, review rejection, outages or bad data.
3. **Has evidence** — `file:line`, a commit hash, a config file or an interview answer. Without evidence raise it only as `needs confirmation`.

## Six sources

| Source | What | How to find (fingerprint section → check directly) | Rule shape |
|---|---|---|---|
| S1 mandatory shared modules | Shared communication, storage, code lookup or UI kit everyone must go through | Top of "Most-used internal modules" and "Call receivers" → search files that **don't** use the module and decide exception or violation | `Use X; no new direct Y` + `Existing exceptions: …` |
| S2 contracts and naming | API path shape, paging input/output keys, response keys, field case, DB object prefixes and column suffixes, file placement | "Path shapes", "Java mappings", DDL/mapper file names, column name frequency | `Keep <pattern>`, naming table |
| S3 incident-born gotchas | Why the same place broke repeatedly, counter-intuitive behavior, performance traps | "Fix commits" and "Fix hotspots" → read the commit diff and judge whether the cause can recur. "Warning comments" | `When <situation>, <method>; no <wrong method> (one-phrase reason)` |
| S4 exemplar files | File to copy when building a new screen, API or query | Among files of the same kind, one that uses every shared module and has a fresh last change in `git log`. Hotspot leaders may be unstable, so check the diff | `The exemplar screen is [file](link)` |
| S5 process and policy | Who starts servers, DB write approval, verification duty, branch and PR flow, sharing scope | Not knowable from code → interview. CI config, branch list and commit history only support the proposed default | Sentences in `common.md` and `git.md` |
| S6 environment facts | Versions, ports, profiles, how to run, DB connection path, deploy flow | Manifests, config files, Dockerfile, CI → user confirmation | `environments.md` table + as-of date and checked scope |

## Questions by area

Pick only questions that fit the stack. Parentheses are examples; do not ask about concepts this repo does not have.

**Screens (SPA, server-rendered templates, mobile)**

- Which shared module does server communication or rendering go through (API client, shared hook, template layout, shared fragment)? Are files that bypass it exceptions or violations?
- Are there shared UI building blocks (component kit, form fragments, grid, modal)? When may you deviate and when not?
- Where do option lists and code values come from (server lookup, constants, enums)? Was hard-coding ever fixed as a violation?
- Where are form input validation and error display done (client, server, both)? Was a mismatch between server length/format validation and the screen ever fixed?
- File location, extensions, import aliases, routing (menu) registration?
- Style variables and themes, i18n message key usage? Is there a test that checks message files stay in sync?

**Server (API, batch, message consumers)**

- Is the entry-point shape fixed (REST path rule, dynamic dispatch, command pattern)? Is it unsafe to conclude "unused" from string search alone?
- Where are transaction boundaries defined (annotation, AOP, naming rule, middleware)?
- What does persistence use (ORM repository, SQL mapper, query builder, procedures, shared util)? Any bulk-processing or N+1 traps?
- What is the convention for returning errors (exception handler, error codes, message keys)? Was an exception hidden as success ever fixed?
- Where is input boundary validation done (length, range, allowed binding fields)? Was a 500 from a boundary value ever fixed?
- Parameter contracts for paging, i18n and data scope (organization, user, seller, etc.)?
- Any trace of repeatedly fixing comment or documentation format?
- **Scan side features separately** — reports, file upload/download, file storage, auth-excluded paths, external integrations and schedulers have rules different from the core flow. If the fingerprint's "Top extensions" lists non-source extensions (report layouts, `.proto`, `.graphql`, templates, etc.), ask for each kind: "where it lives, how it is called, what field names must match, what counts as success, where to look on failure".

**DB**

- Where is the schema managed (migration tool, init scripts, DDL baseline, ORM auto-generation)? Is it applied at startup? What else must change with a schema change (per-DB-vendor scripts, entities, seed data)?
- Are naming rules (prefixes, suffixes, index and constraint names) visible from name frequency?
- Common columns (created/updated time, author, deleted flag), constraint policy (FKs or not), how in-use flags are written?
- Where are metadata such as code values, menus, messages and permissions kept, and in what order are they registered?
- Must scripts be safe to rerun (`IF NOT EXISTS`, `ON CONFLICT`)? With procedures or views, must the original definition be kept before changing?

**Infra and environment**

- How to run locally, ports, profiles, runtime versions (engines field, `.nvmrc`, toolchain, wrappers, devcontainer)?
- Connection path to DB and external services (local container, VPN, tunnel)? Where do settings get overridden (env vars > config files, etc.)?
- Which branches CI runs on, which check commands it actually runs, which branches deploy on merge?
- Do repo-wide file checkers (nohttp, license header, markdownlint, spell check) apply to docs too?

**Git and process**

- Commit subject format (conventional ratio, type, scope, language, mood) and trailers (required `Signed-off-by`, etc.)? Fix commits may be marked in any language (e.g. `fix`, `prevent`, or Korean `수정`, `방지`), and warning comments too (e.g. `WARNING`, `NOTE`, or Korean `주의`).
- Branch flow (work → dev → main, etc.), merge method (merge, squash, rebase), protection settings?
- PR/MR host and whether a CLI (`gh`/`glab`) is available, PR template and contribution guide (`CONTRIBUTING`, README section, `.github/`)?

## Candidate format

Subagents return only this table (`confirmed` rows first, up to 15 rows).

```markdown
| Area | Rule candidate (one line, rule style) | Source | Evidence | Confidence |
|---|---|---|---|---|
| front | Use `api/client.ts`; no new direct fetch | S1 | src/api/client.ts:12 · imported by 214 files · direct fetch in 3 files (login, upload) | confirmed |
| back | List queries keep `PageRequest` input and `total` output | S2 | src/common/Page.java:8 · 41 queries | confirmed |
| db | Bulk saves use batch INSERT | S3 | a1b2c3d fix: upload timeout · row-by-row insert loop in the diff | guessed |
```

- `Confidence` is either `confirmed` (opened the evidence code or config and saw the behavior) or `guessed` (saw only frequency, names, comments or commit messages). If mixed, write `guessed` and say in the evidence cell what you looked at.
- Raise exemplar file candidates as `S4` rows with one phrase in the evidence cell on why it is the exemplar.
- Raise items needing an interview as `S5` rows, with the proposed default and its evidence in the evidence cell.

## Discard

- General best practices, anything in language or framework docs.
- Anything linters, type checks, compilers or **existing tests** already prevent.
- Taste visible in one file only (indentation, etc.). Indentation and line endings end with one line: "follow surrounding files".
- Rows brought from other projects without evidence.
- Conventions of code no longer used (if recent commits changed the approach, follow the new one).
