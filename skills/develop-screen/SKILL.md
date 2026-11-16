---
name: develop-screen
description: Turns a screen design document (화면설계서 / UI spec / storyboard as an attached or local pptx, pdf, slide images, or a Google Slides/Drive/Figma link a connected tool can read) into working screens. Splits the deck into pages, writes a per-screen spec with status (new/modify/keep/delete), traces the impact in the current code, designs DB changes, gets approval, then implements UI, API, data access and SQL, checks the result against the mockup and reports per feature number. Repo-specific folders, layers, status symbols, glossary and checks come from the repo's .devkit/develop-screen/profile.md. Use for "화면설계서 보고 개발해줘", "설계서 p12 구현", "이 PDF 화면 만들어줘", "implement this UI spec". Not for changes requested without a design document (devkit:analyze), code review, or report/print layouts.
argument-hint: "<file path | attachment | link> [p<N> ...] [screen ID]"
---

# Screen design document → screens

Follow the steps in order. At a 🛑 gate, do not move on without user approval. What the document cannot decide is never filled in by guesswork: mark it `needs confirmation` and settle it at 🛑A.

Progress:
- [ ] 0 Input and profile
- [ ] 1 Spec (status)
- [ ] 2 Impact
- [ ] 3 DB
- [ ] 🛑A Design approval
- [ ] 4 Implement
- [ ] 5 SQL
- [ ] 6 Verify
- [ ] 🛑B DB apply
- [ ] 7 Report

| Reference | When |
|---|---|
| [inputs.md](references/inputs.md) | Step 0: reading each input type and link |
| [profile.md](references/profile.md) | Step 0: the repo profile format, and writing one when the repo has none |
| [spec-template.md](references/spec-template.md) | Step 1: the spec format |

## 0. Input and profile

1. **Profile**: read `<repo>/.devkit/develop-screen/profile.md` if it exists. It sets the work and SQL folders, the document language, status symbols, glossary, layer order, copy sources, DB agent and checks. Without one, use the defaults in [profile.md](references/profile.md) and offer once, after 🛑A, to save what you learned as the profile.
2. **Tools**: check once (ToolSearch for deferred tools) which of these are available and report them in one line each as `available / missing → fallback`: the document connectors the link needs, a browser tool for screen checks, a read-only DB query tool, the profile's DB agent, `devkit:spec-analyst`, `devkit:code-reader`. Do not stop for a missing tool; use the fallback in [inputs.md](references/inputs.md).
3. **Split** (run; the deck folder is the profile's, default `<work>/_deck/<deck name>/`):
   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/develop-screen/scripts/extract_deck.py" <input> <deck folder> --pages <N...> [--status "<profile symbols>"] [--id-label "<profile regex>"]
   ```
   It handles pptx (presentation order, notes, slide images), pdf, image files or folders, and exported text. Page numbers are the document's order, not numbers printed on the slides; cross-check the screen ID and title of every requested page against its image.
4. **Mockup**: get an image of every requested page (slide images from the split, `Read` of the PDF page, or a connector thumbnail). A mockup outranks the text for columns, required marks, masking, button positions and layout. Unreadable or cut-off parts are `needs confirmation`; ask for an original capture.
5. Read consecutive pages with the same screen ID (tabs, popups) as one bundle. If the document points to another file (program list, code table), look for it next to the deck and read it as supporting input.

## 1. Spec → status

Give `devkit:spec-analyst` the page text, notes and image paths, the [spec template](references/spec-template.md) path, the profile's status legend and the document language, and the spec path to write (`<work>/<screen ID>/spec.md`). It fills only what the document shows.

Status comes from the page's mark (`index.tsv` `status`, the badge on the image, the profile's symbols). `A → B` means B; a date note (`10/21 수정`) is not a status.

| Status | Next |
|---|---|
| new | 2-new |
| modify | 2-modify. If the page does not say what changes, identical feature wording is not evidence of no change: compare with the previous version of the document if one sits next to it, else list mockup-vs-current-screen differences and ask at 🛑A |
| keep | No development; report and stop |
| delete | Confirm the scope (menu, code, data) with the user |
| unclear / unmarked / symbol and badge disagree | Stop and ask |

## 2. Impact (`devkit:code-reader`)

**new**
- Confirm by screen ID that no screen, endpoint or query already exists. If one does, stop and report.
- Pick an existing screen of the same layout as the copy source (the profile may name a guide). Take only its behaviour wiring (query, save, popup); take layout, split direction, columns and popup shape from the mockup.
- For create/edit popups, compare a few existing popups and pick the closest to the mockup; if unsure, show candidates.
- Place files next to existing screens of the same menu group.

**modify**
- Trace from the screen file every call that carries a query, endpoint or save path → data access → tables and procedures. Dynamic calls (string paths, config routing) exist; never conclude "unused" from a text search alone.
- Per feature number: `current / requested / difference`. Features with no change are not touched.
- **Keep-as-is list**: side effects, pre-save validation, data scope, chained queries, other screens and reports on the same query, table or key. It drives the regression check.
- Renames: find hardcoded labels and message keys; if a key is shared with other screens, ask at 🛑A. Unknown document ↔ code terms: check the profile glossary, else mark `Estimate:` and ask.
- A different approach in the mockup (grid edit ↔ popup) is recorded as a difference, not implemented, until 🛑A. A cut-off mockup is not a request to drop columns.
- Ask whether screens cloned from the same source need the same change. Report defects outside the scope; do not fix them.

## 3. DB

Use the profile's DB agent if it names one (else the main session with a read-only query tool). Find related tables and procedures in the schema baseline and data-access code; for procedures, the parameter order, result convention and callers; for modify, a mockup item ↔ column table and dependent objects. New objects are a design proposal following the repo's DB rules; nothing is final before 🛑A.

Live checks go into `<sql>/00_check.sql`. With a read-only query tool, record the target (DB, account) first and run only SELECT and describe. Without one, hand the SQL to the user; results stay `unverified` until they come back. An object missing from a dictionary query may be outside the account's permissions; never conclude "does not exist" from 0 rows.

## 🛑 A. Design approval

Show the spec summary (status, scope, layout, API, new or changed DB objects, needs confirmation) and ask what the document cannot decide (scope, keys, data granularity, code scheme, shared keys, security). Record answers in the spec's decisions table with the date and departures from the document under "Changes from the document". Add confirmed term mappings to the profile glossary.

## 4. Implement

Follow the profile's layer order (default: schema baseline → data access → service/rule → API → UI) and the repo rules it links. For modify, change only the requested parts and keep the keep-as-is list intact.

- Match an existing implementation of the same kind for queries, saves, transactions and procedure calls.
- Shared styles and shared components stay as they are; if they truly cannot do the job, give the reason and confirm first. Preserve line endings when editing with a script.
- Out-of-scope features decided at 🛑A go to the spec's "Deferred" section.

## 5. SQL (`<sql>/`)

`00_check.sql` (SELECT only) → `01_ddl.sql` (CREATE for new, ALTER / CREATE OR REPLACE for modify, same definition as the schema baseline) → further numbered files the profile lists (codes, menus, permissions; re-runnable, existing values preserved) → `99_rollback.sql` (including the previous definitions of changed objects). A human runs them.

## 6. Verify

- Checks: pick from the profile's checks (or `devkit:check`) through `devkit:check-runner` and record the `CHECKS:` line with `record_run.py` (`devkit:develop` shows how, `--task <screen ID>`).
- Running app: `devkit:run-app up --task <screen ID>` when the repo has `.devkit/runtime.json`, else only an environment the user started. Stop what you started at the end.
- **Mockup comparison (required before reporting)**: capture each screen and popup with a browser tool and compare it item by item with the mockup (split direction, columns, required marks, masking, buttons, titles), in a table in the spec. A passing build is not "matches the document".
- **Behaviour**: query → create → re-query → edit → re-query, confirming saved values with a DB read. For modify, walk the keep-as-is list. Use recognisable dummy data and report what is left behind. The user does password logins; ask again if a new tab needs one.
- Have `devkit:verifier` judge the spec (feature numbers and keep-as-is list) against the diff and record its `VERDICT:` line.
- Write anything not run as `not run`.

## 🛑 B. DB apply

Confirm the target DB first. By default the developer runs write SQL. Explain the order (`01` → … → numbered files), the account and the COMMIT point, then re-query object state and data together. Never use a write tool, even if the query tool has one. Say if the app must be restarted.

## 7. Report

In the document language: per feature number `implemented / deferred (reason) / needs confirmation`, changed files, SQL files, checks run with results and record paths (including `not run`), mockup comparison result, test data left behind, servers still running. Commit, push and PR only on request (`devkit:commit`, `devkit:push`, `devkit:pr-publish`).
