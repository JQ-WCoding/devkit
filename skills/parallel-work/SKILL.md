---
name: parallel-work
description: Splits a request into independent tasks, runs them in parallel worker sessions (each edit task in its own git worktree), then collects the reports and, after confirmation, commits, merges, runs the integrated check and cleans up. Use for "run these in parallel", "split these requests and work on them at once", "merge the finished parallel work". Not for a single task or a few-line change.
argument-hint: "<request (number the items or put each on its own line)>"
---

# Parallel request execution

The central session (this one) splits the request, assigns tasks and collects results. Each worker does only its own task.
Commits, merges, cleanup and writes to external services happen only in the central session, after user confirmation.

The work spans several turns: copy this checklist into your response and tick it off step by step. Don't skip steps. In in-place mode, mark 4-1 to 4-3 as "n/a".

```
Parallel work progress:
- [ ] 0. Choose modes (launcher, workspace)
- [ ] 1. Split the request → approval (base branch, screen check)
- [ ] 2. Prepare workspaces → launch workers
- [ ] 3. Collect reports → check actual results → results table
- [ ] 4-1. Commit → 4-2. Merge point → 4-3. Merge → 4-4. Integrated check
- [ ] 4-5. Screen check (if chosen) → 4-6. Apply fixes, then 4-4 again
- [ ] 4-7. Clean up (only after checks, final review and their fixes)
```

`<scripts>` below and in the reference files is this skill's `scripts` folder: `${CLAUDE_PLUGIN_ROOT}/skills/parallel-work/scripts`. Write it out as an absolute path in commands; the shell may not have `CLAUDE_PLUGIN_ROOT` set.

## 0. Choose modes

Two independent choices. Each mode has its own reference file: read the two that apply in full now. The other mode files are not needed.

**Launcher** — decide from the environment variables `ORCA_TERMINAL_HANDLE` and `HC_TERMINAL_ID` (`echo "$ORCA_TERMINAL_HANDLE|$HC_TERMINAL_ID"`; PowerShell: `"$env:ORCA_TERMINAL_HANDLE|$env:HC_TERMINAL_ID"`).

- `ORCA_TERMINAL_HANDLE` set → `orca`: one supervised Orca worker per task. Read [launcher-orca.md](references/launcher-orca.md).
- `HC_TERMINAL_ID` set (`t<number>`) → `hc`: one Herdr child Claude session per task. Read [launcher-hc.md](references/launcher-hc.md).
- Both set → ask the user which one. Neither → `subagent`: one Agent-tool subagent per task; tell the user in one line that subagents will be used. Read [launcher-subagent.md](references/launcher-subagent.md).

**Workspace** — decide from `git rev-parse --show-toplevel`. Below, `<repo>` is that path (in-place mode: the current working folder).

- Succeeds → `worktree`: each edit task gets its own worktree and task branch. Read [workspace-worktree.md](references/workspace-worktree.md).
- Fails → 🛑 ask "This is not a git repository. Run `git init`?"
  - Yes: `git init` → show the first-commit candidates with `git status --short` (suggest `.gitignore` entries for dependencies, build output and secrets) → after approval, stage files by name and make the first commit with the message the user chooses → `worktree`. A worktree needs at least one commit.
  - No: `in-place`: all workers share the folder; no branches, commits or merges. Read [workspace-in-place.md](references/workspace-in-place.md).

## 1. Split the request

1. Split the request into tasks with one completion criterion each. Split a sentence that holds several jobs; merge sentences that share one goal.
   If only one task results, don't use this skill: say so and do it in this session.
2. Estimate each task's scope (files, modules, APIs, DB objects). If unclear, ask `devkit:code-reader` and keep only its conclusion.
3. Decide what runs in parallel.
   - Default: tasks whose files and modules don't overlap run in parallel.
   - Exception: tasks that edit the same file or shared module, or where one uses the other's result (API, type, schema, DB object), are combined into one worker or ordered.
   - A few-line task gets no worker; the central session does it in step 4 ("central-direct").
   - Tasks on different files but the same feature flow (e.g. an auth filter and the login controller) are marked "integration check needed".
   - The workspace file may tighten these rules; follow it.
4. For each task, decide:
   - **Kind**: `edit` if it changes code, DB objects or docs; `read` if it only investigates or answers.
   - **slug**: lowercase letters, digits and hyphens, 32 characters max. Used as the folder, branch and worker name.
   - **Open points**: choices the request doesn't settle (behavior, scope, naming).
   - Any extra fields the workspace file adds.
5. Run at most 3 workers at once unless the user sets another limit. Launch the rest as earlier ones finish.
6. Decide once — **screen check**: whether to start a server and check the merged result in the browser, and where. "n/a" if there is no UI.
   - The user starts the server with their usual setup, at the location the workspace file gives. Get approval for any branch switch now.
   - Decide whether checks that write data (save, delete) are allowed. If so, list the targets and how to revert them. If not decided, screen checks only read and observe requests.
7. 🛑 Show a table and get approval: launcher · workspace (plus the items its file adds) · screen check (yes/no, location, write checks and how to revert) · per task: kind · slug · scope · parallel/ordered/combined/central-direct · open points. Get the user's answers to open points now. Unanswered ones go into the brief as "don't implement; report the options".

## 2. Prepare workspaces → launch workers

1. Prepare workspaces as the workspace file describes.
2. **Read** [worker-brief.md](references/worker-brief.md) and fill it in (drop the lines for modes not in use).
3. Launch workers as the launcher file describes. Launch the workers that run together at the same time.
4. While workers run, the central session may do central-direct work that doesn't depend on the merge (investigation, checks).

## 3. Collect

- Wait for and receive reports as the launcher file describes. Never write up a worker's result before its report arrives.
- Don't trust reports alone: check the actual changes as the workspace file describes.
- If a worker asks for a lookup or a decision, the central session answers it through the launcher, or asks the user when it is the user's call.
- Instructions that change a task's scope need user approval first.
- Ordered tasks start after the earlier task finishes (the workspace file says exactly when).
- When every worker has reported, show a table per task: task · result (done / blocked / decision needed) · files changed · checks run · remaining work.

## 4. Commit, merge, check, clean up

Each step happens only after 🛑 user confirmation. Push only when asked separately.

1. **Commit**, 2. **Merge point**, 3. **Merge** — worktree mode only; follow workspace-worktree.md. In in-place mode, go straight to 4-4.
4. **Integrated check** — check the combined result once more, even if every worker's own checks passed.
   - Scope: the changed-files list from the workspace file. Take check commands from the repo rules (`docs/rules/`, `CLAUDE.md`); otherwise find candidates with `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/discover.py" <merge point>` (same absolute-path rule). Pick lint, type, build and test for the changed parts (not just one of them), and list the commands — plus any dependency install they need — in this step's confirmation. Follow `devkit:check`'s rules while running (no servers, no autofix over whole files).
   - Run at the merge point (in-place: `<repo>`). Do central-direct tasks first. When the merge point is the main repo, `.worktrees/` still holds the task copies until 4-7: if a test runner or linter would walk into it, pass its ignore option (or run at a merge worktree) and say so in the results.
   - Long checks run in the background as the launcher file describes. Chain commands with `&&` so failures show in the exit code, write output to a log file, and read the log's tail to confirm the check really ran. If it finished in seconds, first suspect a missing tool (`command not found` in the log, exit code 127).
   - Trace each "integration check needed" flow through the code once more (e.g. where both tasks meet on one request path).
   - Results table: merged tasks (branches) · checks run · result · checks not run and why.
   - On failure, stop and report the files and tasks involved. Fix as in 4-6. Roll back only on user request, as the workspace file describes.
5. **Screen check** — only if chosen in step 1. The user starts the server.
   - Tell the user where to start it and to stop any server already on the same port first. Don't check against a server started from another path: find the listener's folder (orca: `orca ports --json`; macOS/Linux: `lsof -nP -iTCP:<port> -sTCP:LISTEN -t`, then `lsof -a -p <pid> -d cwd -Fn`; Windows: `Get-NetTCPConnection -LocalPort <port> -State Listen` → `Get-Process -Id <OwningProcess>`); ask the user if it is still unclear. Confirm the browser actually receives the new code.
   - For each task, decide in a table what to look at (screen behavior, requests, DB rows, logs), check it, and fill in the results in the same table.
   - Run write checks only on the targets approved in step 1. Revert afterwards, confirm the original state with a read, and note it in the table.
6. **Fixes from checks** (integrated check, screen check and final review alike; 🛑 after approval)
   - Default: send the problem and the scope to fix to the worker that did the task (launcher file) → check its report → in worktree mode, commit in its worktree and merge again → run the integrated check again.
   - Exception: a fix of a few lines, or one spanning several tasks, is done by the central session itself at the merge point (in-place: `<repo>`); in worktree mode, as a new commit.
7. **Clean up** — only after the integrated check, the screen check (if any) and any final review the user added (`/code-review` etc.) are finished and their fixes are in. Don't end workers before then; fixes go to them (orca: the launcher file says how). Clean up workers as the launcher file describes, then workspaces as the workspace file describes.

## Never

- Mark a worker's report "done" without checking it. If something wasn't verified, say so.
- Run `git init` without user approval.
