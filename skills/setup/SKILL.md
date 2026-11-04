---
name: setup
description: Build or extend the team's shared rules skeleton (docs/rules), local CLAUDE.md and .gitignore from a repo fingerprint and a short interview. Use for "set up devkit", "make a dev rules skeleton", "add CLAUDE.md".
argument-hint: "[repo path]"
---

# devkit base setup

Follow [method.md](references/method.md): shared source of truth `docs/rules/` + local router `CLAUDE.md`, short table-first style, policies that go into every project. Fill rule-table rows only from the fingerprint and user answers; write nothing without evidence.

| Reference | When |
|---|---|
| [method.md](references/method.md) | At the start |
| [interview.md](references/interview.md) | 🛑A |
| [templates.md](references/templates.md) | Step 2 |

Run the scripts (no need to read them). Put their output in the scratchpad.

## 0. Check the target

- Check the repo root (argument or current directory), current branch and working-tree state. If it is not a git repo, ask whether to proceed without history.
- If `CLAUDE.md` or `docs/rules/` already exists, this is **extend** mode. Treat the existing docs as the source of truth and add only missing files and sections. Never overwrite.
- If `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md` or install docs exist, read them as evidence (README often has run commands, ports and access paths). Do not delete or move them.

## 1. Collect the fingerprint

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/scan_repo.py" <repo root> --out <scratchpad>/fingerprint.json > <scratchpad>/fingerprint.md
```

From `fingerprint.md` use only what this step needs: Layout (sub-projects), Runtime environment (versions, profiles, ports, proxies), CI, DB type, Existing rules and AI config, `.gitignore` and Tracked docs/ files count, Code style, Git (remote host, branches, Merge targets, commit convention, trailers). For environment facts not in the fingerprint, read config files, CI and scripts directly and record each file read in the "Evidence files" table of `decisions.md`.

If "Possible plaintext secrets" appears, report the locations only. Never print the values or copy them into docs.

## 🛑 A. Interview

Ask with AskUserQuestion only the [interview.md](references/interview.md) items the fingerprint did not settle (4 questions per call, 2–3 calls). For environment values, show what the fingerprint found and ask only whether it is right. Record answers in `<scratchpad>/decisions.md`.

## 🛑 B. Setup plan approval

Show everything at once and get approval. Create no files in the repo before approval.

- Files to create, one line each. State that layer docs hold fact rows only (applies-to path, language, runtime, aliases, reference files) and that rule rows are added later by `devkit:suggest-skills`
- Whether to create an onboarding guide (`docs/guide/`) and its step list
- Lines to add to `.gitignore` (or "no change" and why if all are present) and the fingerprint's Tracked docs/ files count. Run `git check-ignore -v <path>` for every planned path — if a file meant to be shared is ignored, add it to the allow list or rename it to match an existing allowed name
- Whether repo-wide file checkers (nohttp, license headers, markdownlint, spell check, etc. — find them in CI and build config) also apply to the new docs, and if so, that the docs will follow those rules
- Settings file: the ".claude/settings.json" section of [templates.md](references/templates.md) — `attribution` or `DEVKIT_AI_TRAILER` depending on the AI attribution answer. If the team-devkit answer is yes, `.claude/settings.json` (with auto-install keys); if no, `.claude/settings.local.json`
- In extend mode, what will be added to each existing file

## 2. Write

Order: `docs/rules/` (README → common → git → environments → layer docs) → `docs/guide/` (if created) → `CLAUDE.md` → `.gitignore` → `.claude/settings.json` or `.claude/settings.local.json`.

- Use [templates.md](references/templates.md) as the skeleton. Fill `{{…}}` slots from the fingerprint and answers; delete the whole row when there is no evidence.
- Write environment values with their source (link to the config file) and add "as of" and "checked scope". Values the user confirmed get "user confirmed"; otherwise "from config files · not verified by running or connecting". Values with no evidence at all are `unverified`. For credentials, write only how they are delivered.
- Only add to existing files with Edit, preserving line endings (CRLF/LF).
- Do not commit. If asked, use `devkit:commit`.

## 3. Check

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/check_docs.py" <repo root>
```

It checks `CLAUDE.md`, `docs/rules`, `docs/guide`, `.claude/agents` and `.claude/skills`. ERROR: broken links, secret-shaped values, unfilled `{{…}}`, agent frontmatter. WARN: inline-code identifiers with no evidence in the repo, broken links from the root README into `docs/rules` or `docs/guide`, length.

- Fix every `ERROR` and run again.
- For a no-evidence identifier WARN, check whether it was copied from another project or is a typo, and fix it. If it is an intended external name (a tool or standard in use), rerun with `--allow <identifier>` and report why.
- Check by hand: does `CLAUDE.md` only link to rules instead of copying them, are there no general-knowledge rows, can every row's evidence be found in `fingerprint.md` or `decisions.md`?

## 4. Report

Report files created or changed, interview decisions, check results and remaining WARNs, `.gitignore` changes and `unverified` environment values. Then suggest `devkit:suggest-skills` in one line as the next step (pinpoint rules, skills and agents for this repo).
