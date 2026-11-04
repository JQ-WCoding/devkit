---
name: push
description: Check the commits and target, ask how to merge if the remote is ahead, then push. Use for "push", "push to remote".
argument-hint: "[remote] [branch]"
---

# Push

Branch and merge rules in `docs/rules/git.md` take precedence.

## 1. Check the target

```bash
git status --porcelain
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # fails if there is no upstream
git ls-remote --heads <remote> <branch>                 # empty means a new branch
```

| Case | Commits to push | Commits only on the remote |
|---|---|---|
| Branch exists on the remote | `git fetch --no-tags <remote> <branch>`, then `git log --oneline <remote>/<branch>..HEAD` | `git log --oneline HEAD..<remote>/<branch>` |
| New branch | `git log --oneline HEAD --not --remotes=<remote>` | None |

- Remote: argument → upstream's remote → `origin`. Branch: argument → current branch.
- Say that uncommitted changes will not be pushed (do not commit them).
- Show the list of commits to push. If commits unrelated to this task are mixed in, ask.

## 2. Blocked cases

- **Force push** (`--force`, `--force-with-lease`) is not done. Even when the user explicitly asks, show the remote commits that would be overwritten, confirm again, and then use only `--force-with-lease`. Never on protected or deploy branches.
- **Protected or deploy branches** (listed in `git.md`, else `main`, `master`, `release/*`, `prod*`): if asked to push directly, stop and say so. If the repo flow merges that branch via PR/MR, suggest `devkit:pr-publish`.
- If a pre-push hook fails, report the cause (`--no-verify` and force are blocked by the devkit guard hook).

## 3. When the remote is ahead

If there are commits only on the remote, do not push; show them and ask how to integrate. Recommend what `git.md` says; without a rule, recommend merge (`git merge <remote>/<branch>`). Rebase rewrites already shared commits, so do it only if the user chooses it. On conflicts, show the conflicted files and wait for instructions.

## 4. Push

```bash
git push <remote> <branch>            # upstream exists
git push -u <remote> <branch>         # new branch
git log -1 --format=%H <remote>/<branch>
```

## 5. Report

Report the remote, branch, pushed commit range (SHAs) and whether it is a new branch. If the CI config runs a pipeline or deploy on this branch, say so. Create the PR/MR with `devkit:pr-publish` when asked.
