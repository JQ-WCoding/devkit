# Workspace: worktree

## Step 1 additions

- **Base branch** — decide once: the branch task branches start from and merge back into. Default: the main repo's current branch. If the user names another branch, use it for every task in this run. If the repo's git rules (`docs/rules/git.md` etc.) name a branch to start work from, propose that as the default.
- **Task branch** (edit tasks only): `fix/<slug>` for a bug fix, otherwise `feat/<slug>`. If the repo's git rules name branches differently, report that and ask the user (the script only creates feat/fix).
- **Ordered tasks**: create the later task's worktree only after the earlier task is merged and passes 4-4, from the updated base branch.
- **Screen check location**: default is the main repo switched to the base branch (get approval for the switch in step 1). Exception: if the main repo must stay as it is, the merge worktree path (4-2).
- Approval table adds: base branch · task branch per task.

## Step 2: prepare

Pick the local-only files workers need (rules, environment, local docs; not build output or logs) from `git -C <repo> status --ignored --short`. Then **run** this script from the main repo root (no need to read it):

```bash
python3 -I <scripts>/make_worktree.py <slug> <feat|fix> <base branch> [local-only paths to link ...]
```

- It creates `<repo>/.worktrees/<slug>` with the task branch cut from the base branch, and links `.env` and any given paths that git doesn't track. Where symlinks are not allowed (Windows without Developer Mode) it copies them and says so; tell the user edits to the copies don't reach the main repo.
- `CLAUDE.md` and `CLAUDE.local.md` load from the parent repo folder, and `.claude/` settings and skills come from the main checkout, so neither is linked. Don't pass `.claude`; the script skips it, along with `.git` and `.worktrees`. On `WARN: local .claude/skills|agents not in the worktree`, tell the user which ones workers may not see.
- On `ERROR`, follow the next action the message gives. Reusing an existing branch needs user approval.
- On `WARN: main repo has uncommitted changes`, tell the user those changes are not in the worktree. Leave the paths listed under `WARN: worktree shows changes that must not be committed` out of the 4-1 commit.
- Work folder: the worktree path for edit tasks, `<repo>` for read tasks.
- Never let two workers share a worktree. Only read workers share the original repo.

## Step 3: check actual results

After reading the report, run `git -C <worktree> status --short` and `git -C <worktree> diff --stat`.

## 4-1. Commit

Commit in the worktree following `devkit:commit` (its rule sources, message format and AI-attribution rule). Check `git -C <worktree> status`, stage files by name, and leave out linked or copied local-only files.

## 4-2. Merge point

Merge where the base branch is checked out. Don't switch the main repo to another branch unless that was approved in step 1. Never remove or switch a worktree this run didn't create.

- Main repo is on the base branch and clean → merge in the main repo.
- Main repo is on the base branch with uncommitted changes → stop. Show the changed files and ask the user to commit or stash them; don't stash for them.
- Base branch is checked out in another worktree (not one this run created) → stop, report its path and ask the user whether to merge there.
- Screen check in the main repo was approved and the base branch is not checked out anywhere else → switch it (`git switch <base branch>`) and merge there.
- Base branch is checked out nowhere → create a merge worktree: `git worktree add .worktrees/merge-<base branch with / replaced by -> <base branch>`. Link the same local files as in step 2 if needed.
- If the chosen merge point has uncommitted changes, stop and report.

## 4-3. Merge

Record `git rev-parse HEAD` as the pre-merge point first. Merge ordered tasks in their order with `git merge --no-ff --no-edit <task branch>`. On a conflict, run `git merge --abort` and report the conflicting files. Then do the central-direct tasks at the merge point and commit them separately.

## 4-4. Scope and rollback

- Changed files: `git diff --name-only <pre-merge point>..HEAD`.
- Roll back with `git reset` only on user request, and only to the recorded pre-merge point.

## 4-7. Clean up

After the workers are cleaned up: `git worktree remove .worktrees/<slug>` → `git branch -d <task branch>`. Never delete an unmerged branch. Remove the merge worktree the same way (never delete the base branch).

`.worktrees/` is excluded only through `.git/info/exclude` (the script adds it). Don't edit `.gitignore`.
