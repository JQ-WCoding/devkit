---
name: pr-publish
description: Review the branch, draft a PR/MR title and body, then create or update it with gh or glab after confirmation. Use for "open a PR", "create an MR", "update the MR body".
argument-hint: "[source branch] [target branch]"
---

# PR/MR review and publish

Invoking this skill does not by itself approve code changes, commits, pushes or merges. Follow the branch and PR rules in the repo's `docs/rules/git.md` if present.

## 1. Pin the targets

- Source is the argument or the current branch. Target is the argument → the flow in `git.md` → the remote default branch (`git symbolic-ref refs/remotes/origin/HEAD`).
- Query the remote and pin the SHAs. Do not change the working tree with ad-hoc stash, checkout or reset.

```bash
git fetch --no-tags origin <source> <target>
git rev-parse origin/<source> origin/<target>
git merge-base origin/<target> origin/<source>
```

- What goes into the PR is the **remote** source. If there are local commits not yet pushed, say they are not included; push them with `devkit:push` when asked.
- Choose the tool by remote host: `gh` if the host of `git remote get-url origin` is `github.com` or a host in `gh auth status`; `glab` if it is a `gitlab` domain or a host in `glab auth status` (including self-hosted GitLab). If neither (file-path remote, not authenticated), use **draft mode**.

## 2. Review

- Read the full change list and diff at the pinned SHA, and read callers as of that SHA (`git show <sha>:<path>`). If local working files differ, do not treat them as PR code.
- Focus on real failures, data errors and regressions, API and schema contracts, permissions, transactions, and whether secrets are included. Do not demand refactoring on taste or metrics alone.
- For a large change, hand caller tracing to `devkit:code-reader` per group of files.
- If checks are needed, suggest `devkit:check` (a user-invoked skill).

## 3. Draft and 🛑 confirmation

- Show the review result (defects with file, trigger condition and impact) and the title and body draft. Title and body language and format follow `git.md` and the PR template (`.github/pull_request_template.md`, `.gitlab/merge_request_templates/`); without them, use `devkit:commit`'s format and language decision as is.
- If there is an issue key, follow the linking style in `git.md` (title prefix, `Closes #45` or `Refs ABC-123` in the body, etc.); without a rule, put only the source link in the body. Do not change tracker status.
- If there is an analysis doc (an `.devkit/work/*/analysis.md` matching the branch name or issue key; otherwise the most recent one, after confirming), summarize the requirement items, impact, verification results and DB apply steps in the body. Analysis docs and work SQL are not committed to the repo, so write the SQL steps reviewers need in the body and state "not included in this PR".
- Do not write checks that were not run as passed. AI attribution follows the trailer rule in `git.md`; without a rule, leave it out.
- Check whether an open PR/MR exists and say whether you will create or update.
- In draft mode, skip the open-PR check and the publish confirmation; deliver the title and body as a scratchpad file and in the reply, tell the user to create it on the host, and stop.
- Ask once whether to publish as is. If the user said from the start "review and publish right away" and no defects were confirmed, skip it. If there are defects, always ask again.

## 4. Publish

- Query the remote SHA again right before publishing. If it differs from the reviewed SHA, do not publish; report the added commits.
- Check authentication (`gh auth status` / `glab auth status`). If it fails, do not publish; deliver the draft so the user can create it. Do not publish by another route such as browser automation.
- Pass the body through a scratchpad file.

| Action | GitHub (`gh`) | GitLab (`glab`) |
|---|---|---|
| Find open | `gh pr list --head <source> --base <target> --json number,url` | `glab mr list --source-branch <source> --target-branch <target> -F json` |
| Create | `gh pr create --head <source> --base <target> --title "<title>" --body-file <file>` | `glab mr create --source-branch <source> --target-branch <target> --title "<title>" --description-file <file> --remove-source-branch=false --push=false --yes` |
| Update | `gh pr edit <number> --title "<title>" --body-file <file>` | `glab mr update <iid> --title "<title>" --description-file <file>` |
| Verify after publish | `gh pr view <number> --json headRefOid,baseRefName,headRefName,url` | `glab mr view <iid> -F json` |

- `--remove-source-branch` and `--squash-before-merge` on `glab mr update` are toggles, so do not use them when updating.
- After publishing, confirm source, target and head SHA match the reviewed values, and report the link.
- Merge, auto-merge, approval and reviewer/assignee changes only on request. If merging the branch leads to a deploy, say so.
- If the authenticated account is not a personal one (bot token etc.), say the author will show as that account.
