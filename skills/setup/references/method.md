# How the rules are organised

Contents: two layers · file roles · writing style · policies for every project

Only the **structure, style and policies** carry over.

## Two layers

| Layer | Location | Git | Nature |
|---|---|---|---|
| Shared source of truth | `docs/rules/*.md` (+ `docs/guide/` onboarding if needed) | Tracked | Tool-neutral team rules. People and AI read the same docs |
| Local router | `CLAUDE.md` | Excluded by default | Area → rules doc table, when to call skills and agents. Does not copy rules |
| Project tools | `.claude/agents/`, `.claude/skills/` | Excluded by default | Skills and agents that fit only this repo (made by `devkit:suggest-skills`) |
| Local work files | `.devkit/work/` (analysis docs, work SQL) etc. | Excluded | Ignore only the work folders |

- Put `.claude/` (only `.claude/settings.local.json` when a team-shared `settings.json` is kept), `CLAUDE.md`, `CLAUDE.local.md` and other AI tools' personal config in `.gitignore`.
- `docs/` is usually tracked broadly, so ignore only the local work folders. Ignoring all of it and reopening with an allow list is used only when the user answered that way.
- Put "This folder is the source of truth for shared rules. Personal AI tool config is not part of the repo" in `docs/rules/README.md`.
- If the whole team decided to use Claude Code and devkit (interview), `CLAUDE.md` and `.claude/settings.json` (attribution setting only, no install keys) may be tracked. Rule bodies still live in `docs/rules/`.

## File roles

| File | Contents | Length |
|---|---|---|
| `CLAUDE.md` | First line links the shared rules → `Area | Doc` table → verification is optional (`devkit:check`) → temp files in the scratchpad → delegate exploration to `code-reader` → when to call project skills and agents | ~25 lines |
| `docs/rules/README.md` | `Area | Doc` index, source-of-truth statement, onboarding link | ~15 lines |
| `common.md` | Working principles · ask-first table · code style · running · verification and reporting | ~40 lines |
| `git.md` | Commit format (type, scope list, subject style, body, trailers) · branches · PR/MR · merging · never | ~80 lines |
| `environments.md` | Local run table · DB and external access paths · deploy environments · config evidence links · checked scope and date | ~90 lines |
| Layer docs (`front.md`, `back.md`, `db.md`, etc.) | One `Applies to: <path>` line → `Item | Rule` table → reference file links → one essential example | 60–110 lines each |
| `docs/guide/developer-onboarding.md` (optional) | Goal → what to get before starting → `Step | Doc | Done when` table → daily routine → credential notes → checked date and unverified scope. Only when there are 3+ setup steps not in README or external dependencies such as VPN or tunnels | ~25 lines + step docs |

Layers follow the repo structure. Give each sub-project (web, API, mobile, batch, etc.) and the DB its own doc, and merge a layer that is small. A single-module app gets one `app.md` and (if there is a DB) `db.md`. **Layer docs written by setup hold fact rows only** — the `Applies to:` path, language and runtime, extensions and import aliases, folder layout, reference files to follow (fingerprint evidence). Rule rows such as "go through …" or "… is forbidden" are added by `devkit:suggest-skills` once it finds evidence.

## Writing style

- `Item | Rule` tables by default. The rule cell joins short noun phrases with `·`: `via api/client · no new direct fetch`.
- End prohibitions with "forbidden" and pre-checks with "ask first". Add a short reason in parentheses only when it changes the next action (`per-row SQL parsing, exceeds transaction limit`).
- Say what to use by name and how to use it with a **reference file link**. No long explanations.
- At most one example code block per doc, one reference pattern.
- Do not write general best practices Claude and developers already know, or things linters and compilers already block. Exception: a layer doc's `## Design principles` section records the project's own adopt/decline decision on a general principle (evidence: user decision, asked in `devkit:analyze` and written as a docs step of its plan), never its explanation.
- Add `As of: YYYY-MM-DD` and `Checked scope` (OS and environment checked, what was not verified) to facts that can change. Unchecked values are `unverified`.
- For credentials, write only the location and delivery method (`delivered individually · never recorded in Git`).
- Link docs with relative paths, and put `[Rules index](README.md) · [Common rules](common.md)` at the top of each layer doc.

## Policies for every project

These are working attitudes, not project facts, so the template sentences are used as is (change only what the interview asked to change). They record the same content as the `using-devkit` principles in a team-shared doc — teammates who do not use devkit see the same standard.

- The common.md template's working-principle, code-style and verification sentences in templates.md, as is.
- Check the environment doc before running anything. Automation tools never start or stop servers or tunnels on their own (interview default); if the interview allows it, servers start only through `devkit:run-app`, and tunnels still never.
- DB writes only after the target and scope are approved; by default the developer runs them. Writing a fix is not approval to run it.
- No `git add .`, no `--force` or `--no-verify`; add, commit, push and PR only after user confirmation.
- Write in `git.md` that when repo rules (e.g. no commit trailers) differ from the system's default guidance, the repo rules win.
