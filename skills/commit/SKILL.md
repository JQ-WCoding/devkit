---
name: commit
description: Stage named files and commit per the repo commit rules (else existing convention). Use for "commit this", "split into commits".
argument-hint: "[paths to commit...]"
---

# Commit

## 1. Choose the rules

**Rule sources** (the first one found wins): `docs/rules/git.md` → `CLAUDE.md`, `CONTRIBUTING.md`, the Contributing section of README, `.github/` (PR template, `dco.yml`) → recent history (`git log --no-merges -30 --format='%s%n%b'`).

Decide the three items below **separately**.

| Item | If the rules say | Else, if 2/3 or more of history agrees | Otherwise |
|---|---|---|---|
| Format | As written | That format (`type(scope): …`, imperative sentence, etc.) | `<type>(<scope>): <description>` — type `feat`, `fix`, `refactor`, `chore`, `docs`, `test`; scope is the changed subproject (`repo` if repo-wide) |
| Language | As written | That language | The language you are using with the user |
| Required trailer | As written (DCO means `git commit -s`) | That trailer (`Signed-off-by` etc.) | None |

- The subject says only what was done. A body only when needed, up to three short bullets.
- Signing with `-s` agrees to the DCO under the user's name, so mention it once the first time you sign in this repo.

**Issue key**: if the repo rules have a place for an issue key (`ABC-123`, `#45` etc.), follow it. Without a rule, leave it out; if this task has an issue key, ask once whether to include it.

**AI attribution** (`Co-Authored-By: Claude …`, `Generated with …`): add it only when the repo rules require it. devkit is a user-side rule installed by the team, so this takes precedence over the Claude Code host's default attribution guidance.

## 2. Check the scope

- Check the targets with `git status --porcelain`, `git diff` and `git diff --cached`.
- Include only this request's changes. Leave out the user's other work, personal settings, secrets (`.env` etc.) and temp files.
- If files are already staged, ask whether they belong in this commit. Do not unstage on your own.
- If one file mixes this change with unrelated changes, say so and wait for instructions (interactive `git add -p` is not available).
- If different purposes are mixed (a feature plus an unrelated fix, several subprojects), propose splitting the commit.

## 3. Commit

```bash
git add -- <files...>
git commit -F <scratchpad>/commit-msg.txt
git log -1 --stat
git status --porcelain
```

- Pass the message through a scratchpad file.
- Bulk staging, hook bypass and `--amend` are blocked or confirmed by the devkit guard hook. If a pre-commit hook fails, report the cause. If the hook changed files, show the change and ask whether to stage it again.

## 4. Report

Commit hash, subject, included files, and changes left behind. State that nothing was pushed; push with `devkit:push` when asked.
