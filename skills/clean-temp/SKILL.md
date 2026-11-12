---
name: clean-temp
description: Finds temp files Claude left in the repo while working (dry-run folders, .bak/.tmp files, root temp scripts, captures) and other sessions' scratchpads, then moves the ones the user picks to the OS trash. Only when the user invokes it.
disable-model-invocation: true
argument-hint: "[all | paths...]"
---

# Temp file cleanup

Never delete work in progress; this comes first. "Untracked or ignored by Git" does not mean "temporary". Handle only what the script classifies, and remove only with its `trash` command after user confirmation. Never use `rm` or another permanent delete.

`<script>` is `${CLAUDE_PLUGIN_ROOT}/skills/clean-temp/scripts/clean_temp.py`. Write it out as an absolute path in commands; the shell may not have `CLAUDE_PLUGIN_ROOT` set.

## 1. Scan

The scan only lists. Pass this session's scratchpad path when there is one; it is never listed.

```bash
python3 -I <script> scan <repo root> [--scratchpad <this session's scratchpad path>]
```

| Class | Contents | Handling |
|---|---|---|
| Removal candidates | `_dryrun*`, `_tmp*`, `tmp`, `tmp_*`, `tmp1`, `scratch*`, `test-results` and similar folders at the root or under `docs/` (not `templates/` or `temperature/`); `*.bak`, `*.orig`, `*.tmp`, `*~`, `*.swp`, `*.rej` anywhere. Untracked only, not ignored: images at the root or directly in `docs/`, scripts and notes at the root. A temp folder holding protected files is split into its other files | Clean up after confirmation |
| Needs review | Other untracked files | Show the list only; clean up only what the user names |
| Protected | Tracked files; any path through `src`, `test(s)`, `node_modules`, `build`, `out`, `dist`, `target`, `logs`, `.venv`, `.worktrees`, `.devkit`, `.claude` and other tool folders; `CLAUDE.md`, `AGENTS.md`, `.env*`, `.mcp.json`; the repo's `protect` globs | Not listed and never touched |
| Other sessions' scratchpads | Sibling folders of this session's scratchpad, with size and last change | Only when the user wants; a recent last change may be a live session (e.g. a parallel-work worker) |

**Repo-specific protections** live in `<repo>/.devkit/clean-temp/config.json` (local, like `.devkit/peer-review/`):

```json
{"protect": ["database/", "docs/design/[!_]*", "docs/rules/"]}
```

Globs match repo-relative paths; `*` also matches `/`; a trailing `/` means everything under it. If there is no config and the repo rules or `CLAUDE.md` name local work folders to keep (specs, mockups, work SQL), propose `protect` entries for them and write the file after approval, then scan again.

## 2. Confirm

Show the removal candidates and the needs-review list with path, size and reason, and ask which to clean up. Propose all removal candidates by default. If an item's contents are unclear, open it first to check whether it is an output of this work. If the user already set a scope (`all`, or named paths), use exactly that scope.

## 3. Clean up and report

```bash
python3 -I <script> trash <repo root> [--scratchpad <this session's scratchpad path>] <selected paths...>
git status --porcelain
```

- The script checks every path first and moves nothing if any is tracked, protected, holds a protected path, is this session's scratchpad, or is outside the repo and scratch root. A symlink is moved as the link, never its target. Report refusals as they are; don't work around them.
- If no trash tool exists (Linux without `gio` or `trash-cli`), report the next action it gives. Don't fall back to deleting.
- Use `git status` to confirm tracked files and in-progress changes are intact. Report the cleaned paths and sizes and the needs-review items left in place, and mention the files can be restored from the trash. If needs-review items remain, don't call the tree "clean".

## Out of scope

- Build output and dependencies, logs, DB objects, containers and backups.
- Other repositories and general files in the system temp folder.
- Hooks or automatic runs at the end of a task.
