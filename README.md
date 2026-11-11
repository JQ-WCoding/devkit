# devkit

A Claude Code team dev kit that sets up the same development workflow in any repository and any business domain. It ships no project rules up front and depends on no task tracker (Jira, Notion, Obsidian, GitHub Issues …). It contains the **workflow** (analyze → implement → verify → commit → push → PR/MR), **working principles** (minimal scope, claim only what was checked, optional verification, human approval points), and **tools that grow evidence-based rules and skills for each repository**.

Skills and docs are written in English; Claude answers in the user's language, and `devkit:setup` writes repository docs in the language chosen in its interview.

## What's inside

| Stage | Name | What it does |
|---|---|---|
| Always | Session hook `using-devkit` | Injects the judgment principles (6 lines) at session start, resume, clear and compaction. A repo's `CLAUDE.md` and `docs/rules/` take precedence |
| Always | Guard hook `hooks/guard.py` | Enforces Git and server-start rules in code right before shell commands run (see "Guard hook") |
| Analyze | `/devkit:analyze` | Reads a requirement, issue or bug from any source; traces current code → gap → impact → common risk check → implementation plan in an analysis doc; asks for approval |
| Implement | `/devkit:develop` | Implements the approved plan, DB change and rollback SQL, verification and regression check, per-requirement report |
| Verify | `/devkit:check` | Finds lint, type, build and test commands and runs only the related ones (user-invoked only) |
| Commit | `/devkit:commit` | Commits named files following the repo's Git rules |
| Push | `/devkit:push` | Checks outgoing commits and whether the remote is ahead, blocks protected-branch and force pushes, then pushes |
| PR/MR | `/devkit:pr-publish` | Review → title and body draft → confirmation → create or update the PR/MR with `gh`/`glab` |
| Review | `/devkit:peer-review` | Reviews teammates' commits on a shared branch since the last review (commit format per `docs/rules/`, must-fix vs optional defects), drafts per-developer feedback and tracks findings until fixed |
| Setup | `/devkit:setup` | Lays down the shared rules skeleton `docs/rules/` (common, Git, environments; layer docs and onboarding when needed), the local router `CLAUDE.md` and `.gitignore` |
| Setup | `/devkit:suggest-skills` | Proposes rule rows, project skills and agents from code pinpoints, repeated tasks and user corrections; builds only the chosen ones |
| Explore | Agent `devkit:code-reader` | Handles multi-file exploration and returns only conclusions (Sonnet, read-only) |

The common risk checklist in `analyze` covers failure points that recur in every domain: consistency, concurrency, idempotency, state transitions, money, time zones, data scope, personal data, external integrations, bulk processing and deployment compatibility.

Blueprints `suggest-skills` proposes when the conditions fit: a project-specific flow skill (adds this repo's own steps on top of `analyze` and `develop`), `db-analyst`, `knowledge-reader` and `spec-analyst` agents, `workspace-cleanup`, `visual-docs`, and external-tool skills.

## Workflow

1. First time in a repo: `/devkit:setup` → answer a few interview questions and approve the setup plan to get the rules skeleton.
2. Per task: `/devkit:analyze <issue link, file or requirement>` → approve → `/devkit:develop` → `/devkit:check` if needed → `/devkit:commit` → `/devkit:push` → `/devkit:pr-publish`.
3. As a reviewer: `/devkit:peer-review` → review what teammates pushed to the shared branch since last time. The first run builds `.devkit/peer-review/config.json` from `docs/rules/git.md`.
4. Occasionally: `/devkit:suggest-skills` → get evidence-backed candidates for this repo's rule rows, skills and agents, and build only the chosen ones. Claude suggests it once when the same task repeats or the same correction is given twice.

Analysis docs and work SQL live in `<repo>/.devkit/work/<task ID>/` (excluded from Git).

## Requirements

**Python 3.8+, available as the `python3` command.** Hooks, scans and checkers all run on Python. No other runtime (node, bash, PowerShell) is needed.

| OS | Install | Check |
|---|---|---|
| macOS | Included (otherwise `xcode-select --install` or `brew install python`) | `python3 --version` |
| Linux | Distribution package (`apt install python3` etc.) | `python3 --version` |
| Windows | Python install manager from python.org, or Python from the Microsoft Store | `python3 --version` in a new terminal |

The legacy python.org installer for Windows does not provide a `python3` command; reinstall with the install manager. If running `python3` opens the Microsoft Store, Python is not installed yet.

## Install

Needs: Claude Code, Python 3.8+, Git. `gh` or `glab` for publishing PRs/MRs.

From GitHub ([JQ-WCoding/devkit](https://github.com/JQ-WCoding/devkit)):

```bash
claude plugin marketplace add JQ-WCoding/devkit
claude plugin install devkit@devkit
```

Inside a session: `/plugin marketplace add JQ-WCoding/devkit`, then `/plugin install devkit@devkit`. Restart Claude Code after installing.

The repository is private: you need read access, and Git must be able to authenticate to GitHub (for example `gh auth login`, then `gh auth setup-git`). If the marketplace add fails with an authentication error, check that `git clone https://github.com/JQ-WCoding/devkit.git` works in a terminal.

From a local clone (for developing devkit itself; edits apply without pushing):

```bash
claude plugin marketplace add ~/work/devkit
claude plugin install devkit@devkit
```

Update: `claude plugin marketplace update devkit`, then `claude plugin update devkit@devkit`, then restart Claude Code.

## Enable by default in a team repo

Optional, by hand: `devkit:setup` does not write these keys, because teammates who got devkit as a zip may not reach the GitHub repo. If every teammate can reach it, add this to the team repo's `.claude/settings.json` (tracked in Git). When a teammate trusts the repo, the marketplace is registered and the plugin is enabled.

```json
{
  "extraKnownMarketplaces": {
    "devkit": { "source": { "source": "github", "repo": "JQ-WCoding/devkit" } }
  },
  "enabledPlugins": { "devkit@devkit": true }
}
```

- For a mirror on another Git host: `{ "source": "git", "url": "https://<host>/<group>/devkit.git" }`.
- Each teammate may need to download it once with `claude plugin install devkit@devkit --scope project`.
- In that case set `.gitignore` to `.claude/*` plus `!.claude/settings.json` rather than ignoring all of `.claude/` (`devkit:setup` asks about this in its interview).

## Guard hook

Rules that must hold every time, without exception, are enforced in code (deterministic) rather than prose (advisory). Prose keeps only the principles that need judgment, which cuts per-session tokens. The hook runs `python3` directly without a shell (exec form), so it behaves the same on macOS, Linux and Windows.

| Decision | Commands (Bash and PowerShell tools) |
|---|---|
| Deny | `git add .`, `-A`, `-u`; `git commit -a`, `-n`, `--no-verify`; `git push -f`, `--force`, `+ref`, `--no-verify`; commit messages containing AI attribution (`Co-Authored-By: Claude`, `Generated with Claude Code`) via `-m`, heredoc or a `-F` file |
| Ask | `--force-with-lease`, `--amend`, pushes to protected branches (`main`, `master`, `release/*`, `prod*`), server and container starts (`bootRun`, `spring-boot:run`, `npm run dev`, `docker compose up` etc.) |

- Disable: `DEVKIT_GUARD=off`. Repos that want AI attribution: `DEVKIT_AI_TRAILER=allow`. Both can go in the settings `env`.
- The setting that stops attribution from being written at all (`"attribution": {"commit": "", "pr": ""}`) is written by `devkit:setup` according to the interview answer.
- A guard error never blocks work (`onFailure: continue`). Ambiguous commands pass (missed detection over false positives).
- Tests: `python3 -I hooks/guard_test.py`

## Changing principles or adding skills

- Working principles: `skills/using-devkit/SKILL.md`. It goes into every session, so keep only short judgment rules there. Rules that code can decide go into `hooks/guard.py`, with cases in `guard_test.py`.
- New skills: follow `skills/suggest-skills/references/skill-authoring.md` and check with `python3 -I skills/suggest-skills/scripts/check_skill.py skills/<name>`.
- Manifest check: `claude plugin validate .`
- The installed copy is per version. To ship changes to the team, bump `version` in `.claude-plugin/plugin.json` (`plugin update` ignores changes at the same version).
- Anything that differs per project (module names, paths, naming) does not belong in devkit. Put it in each repo's `docs/rules/` and `.claude/`.

## Status

0.4.0 · 2026-11-04. Still in local trial, so no license has been chosen yet. Add a `LICENSE` before publishing.
