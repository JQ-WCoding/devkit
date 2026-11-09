---
name: peer-review
description: Review teammates' commits on a shared branch since the last review, draft per-developer feedback and track findings. Use for "review teammates' commits on dev", "were last review's findings fixed". Not for your own diff or a PR/MR.
argument-hint: "[author | --base <SHA> | --days N]"
---

# Peer review of a shared branch

Review other developers' commits on the shared remote branch and draft feedback per developer. Feedback stays as drafts in chat; do not post it to the Git host, messengers or trackers. Code changes, commits and DB writes are out of scope; if the user then asks to fix something, do that as separate work.

Rule sources are the repo's `docs/rules/` (and `CLAUDE.md`). Do not copy rules into the config or the report; read the sources each time.

Files: config `.devkit/peer-review/config.json`, state `.devkit/peer-review/state.json` (both local). If Git would track them (`git check-ignore -q .devkit/` fails), add `.devkit/` to `.git/info/exclude` and say so.

## 0. Config (first time only)

If the config is missing, build it per [config.md](references/config.md) from `docs/rules/git.md` and the top-level layout. Show it with the source line for each rule, 🛑 get approval, then write it. If the repo has no commit rules, say only the generic checks will run and ask whether to proceed. When the rules change later, update the config the same way.

## 1. Collect targets (run)

From the repo, passing through only the options below. An author name is not a script option: run without it, review only that developer's groups, and do not record the position in step 6.

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/peer-review/scripts/collect_commits.py" [--base <SHA>] [--days N] [--include-self]
```

- It fetches the branch and lists commits after the last reviewed SHA in the state file (no record → last 7 days; `--days` changes only that fallback, `--base` overrides the record). Your own commits (`git config user.name`) and merge commits are excluded from review.
- Output: commits per developer with format warnings (⚠️). Warnings starting with `judgment:` are conventions the rules do not state — pass them on as "needs checking", never as violations.
- Merge commits are for reference. Judge them only against the merge rules in `git.md`.
- Note the remote SHA on the first line; step 6 records it.
- If there is an "Open findings" section, do step 1-1 first. With no commits and no open findings, say so and stop.

## 1-1. Recheck open findings

For each open finding, read the current code at its `file` on the remote branch (`git show origin/<branch>:<path>`) and decide whether it still holds. "File changed since" only says where to look; it does not mean fixed.

| Result | Action |
|---|---|
| Fixed | Report as fixed with the fixing commit; close in step 6 |
| Still holds | Carry it into this report and that developer's message as "not yet addressed" |
| User judges it not a problem | Close with `--reason withdrawn` in step 6 |

## 2. Split the content review

- Group by developer × area (areas from the output). Delegate a group over 100 changed lines (+ and −) to a general-purpose subagent; read small groups yourself with `git show`.
- Launch the subagents in one message, at most 5. Write each brief from the [reviewer brief](references/reviewer-brief.md) template, filled from the config; keep all its prohibitions.
- If business meaning is unclear from code alone (quantity basis, status flow), do not guess; report it as "needs checking".
- Do not run paid cloud reviews (`/code-review ultra` etc.) unless the user asks.

## 3. Verify high-severity findings yourself

Before reporting an item a subagent rated high, read the code and call path yourself and confirm it holds. Label every item:

| Label | Meaning |
|---|---|
| verified | The main session read the code path and confirmed it |
| agent-reported | Found by a subagent, not rechecked |
| guessed | Cannot be asserted without running it or checking data |

Say so if you did not run or reproduce it against data. Drop items that do not hold.

## 3-1. Must-fix or optional

A review always finds something, so certainty is not importance. Ask three questions of each defect that holds:

| # | Question |
|---|---|
| A | Does data go wrong or get lost (wrong value, mismatch between systems, rows not saved, wrong status)? |
| B | Does the user not notice the failure (reported as success, swallowed exception, no alert)? |
| C | Does the trigger occur in real work and data? Where a read-only query tool on a non-production DB exists, count matching rows and state the count; otherwise say why it could not be checked. |

- **Must-fix**: (A or B) and C. Fix before release or before the feature goes live.
- **Optional**: everything else (UX, display-only, no matching data). Note what would change the call.
- Severity says how bad it is if it happens; must-fix/optional says whether to act now. Report both.
- A pre-existing pattern the commit only exposed stays in the report, but name the owner of that code rather than the commit author.

## 4. Report (chat, user's language)

Give `file:line`, the failure scenario and the rule, not long explanations. In order:

1. One-line conclusion: rule compliance, must-fix count, scope (period, commits, per developer)
2. Earlier findings (if step 1-1 ran): ID | developer | fixed / not addressed | evidence
3. Must-fix: item | label | A·B·C answers (with the C count) | `file:line` and scenario
4. Optional: one line each, with what would make it must-fix
5. Rule table: item | ✅/⚠️ | developer and evidence
6. Per developer: 1–2 things done well + issues raised

## 5. Per-developer message drafts

One paste-ready message per developer, in the config's `message_language` and `message_register` (default: the `docs/rules/` language, polite colleague tone).

- Facts and scenario before criticism; include one line on something done well.
- Order: must-fix (commit hash, `file:line`, scenario, one-line suggestion) → rule items → optional items marked "for reference". At most 5 items; summarize the rest as "n more in the full review".
- Ask about guessed items ("could you check …"); do not assert them.
- A developer with nothing to flag gets a short acknowledgement only.
- No AI attribution in the messages.

## 6. Record position and findings

The user decides: ask which reported items to track (default: every must-fix and every rule ⚠️ the user did not dismiss; optional items only if picked). Then:

1. Write the accepted items to a JSON list in the scratchpad (`author`, `commit`, `file` as `path:line`, `severity`, `label`, `summary` — one line) and add them.
2. Close items found fixed in step 1-1, and those the user withdrew.
3. Record the remote SHA from step 1 so the next review starts there. Do not record it if the range was changed with `--base`/`--days` or only one developer was reviewed; adding and closing findings is still fine.

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/peer-review/scripts/collect_commits.py"
python3 -I "$S" --no-fetch --findings-add <scratchpad>/findings.json
python3 -I "$S" --no-fetch --close F3 F5                     # fixed
python3 -I "$S" --no-fetch --close F4 --reason withdrawn
python3 -I "$S" --no-fetch --mark <remote SHA>
```

## On failure

- Fetch fails: ask the user to check remote access, and whether to review the locally known remote branch with `--no-fetch`.
- The recorded SHA is not in the remote history (force update etc.): the script falls back to the last N days and says so; mention it in the report.
