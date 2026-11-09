# Reviewer brief template

The prompt for a review subagent. Fill in only the `<…>` parts from the config and the collected commits; keep the rest as is, including every prohibition.

```text
Repository <absolute repo root>. <config brief.summary>
Do not modify files; use git and reading only. Do not start servers, containers or tunnels. Do not write to any DB; if truly necessary, use only a read-only SELECT tool and state what you queried.

Task: review the <area> changes among colleague <developer>'s <branch> commits.
Target commits: <hash list with one-line subjects>
Read each diff with `git show <hash>`; when needed, follow the full post-change file and its call sites (UI ↔ API ↔ query/mapper ↔ table/procedure).

Rules to read first: <config areas[].rules for this area, plus docs/rules/git.md>
<config brief.notes, one per line>

Focus:
- Behavioral defects: boundary values (0, NULL, empty, overflow), concurrency and rapid repeated input, key or schema changes that affect other code using the same table (find it with grep), UPDATE/DELETE conditions, data-scope filters (tenant, site, owner), exceptions reported as success, transaction scope, NULL comparisons
- Rules from the docs above that this diff touches
- Whether each commit keeps to one purpose
<config brief.focus, one per line>
<suspect points specific to these commits, if any>

Output (in <report language>, within 600 words):
- Findings by severity (high / medium / low). For each: `file:line`, the problem, a concrete failure scenario, and the rule it rests on.
- For each finding, one line answering: does data go wrong or get lost; would the user notice the failure; what data condition triggers it (with a read-only SELECT count if you ran one).
- Mark anything that cannot be asserted without running it or checking data as "guessed".
- 2–3 lines on what was done well, and one line per area where you found no problems.
```
