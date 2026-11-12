# Worker brief template

The central session fills in `<...>` and passes the result as the worker's first message (orca: `worker-start --spec`; hc: the last argument of `hc run`; subagent: the Agent tool `prompt`).
Lines tagged with modes (`[orca]`, `[hc]`, `[subagent]`, `[worktree]`, `[in-place]`) are kept only when every bracket matches this run; `a|b` inside one bracket means either. Remove the tags from kept lines. Don't delete fields; drop only lines that don't apply.

```text
[Worker brief] <slug>

You are a worker started by the central session. Do only this one task.

## Task
- Request: <the part of the user's request this task covers, verbatim>
- Kind: <edit | read>
- Work folder: <absolute worktree path or absolute repo path>  (don't edit files outside this folder)
- Branch: <feat/slug | fix/slug | none>
- To do: <goal and completion criteria as the central session framed them, 2-6 lines>
- Settled decisions: <the user's answers to open points, or "none">
- Out of scope (don't touch): <files and modules other workers own>

## Rules
- Follow the repo's CLAUDE.md and rules docs (docs/rules/) if there are any. If you find you need to edit a file in another worker's scope, stop and report.
- Don't: git commit, push, merge or switch branches; git init; start servers; write to databases; write to external services (issues, docs, messages); start other agent sessions (hc run, orca worker-start, etc.). Exploration subagents (Agent tool) are fine.
- [subagent|orca][worktree] You start in the central session's working folder. Start every shell command with `cd <work folder> && …`, and read and edit files by absolute path under the work folder. Never edit the same-named file in the central repo.
- [in-place] Other workers are editing the same folder at the same time, and there is no git history to undo with. Only read files outside your scope. Even inside your scope, stop and report before deleting or moving anything. Ask the central session before running commands that change the whole folder, such as installing dependencies.
- [hc] Long commands such as dependency installs or builds may run as `hc run --bg --rm --no-notify --name <slug>-build -- env PATH="$PATH" sh -c '<command>'` followed by `hc wait <slug>-build`. Pass the current PATH like this instead of writing one out (the hc run shell may lack PATH setup such as nvm).
- [subagent|orca] Long commands may run with Bash run_in_background.
- Chain helper commands with `&&` and write their output to a log file; check both the exit code and the log's tail. If a command ended within seconds or exited with 127, check whether the tool was found.
- [worktree] If the worktree has no dependency folder (node_modules etc.), install dependencies before running checks.
- Don't implement unclear choices that aren't in "Settled decisions"; report the options and their impact instead.
- Run only the checks that fit what you changed: the repo's rules if any, otherwise lint/build/test from the manifests (package.json, build.gradle, pyproject.toml, …).
- After you report, the central session may send fixes from its checks. Then fix only the scope you were given and report again the same way.

## Report
- Contents: conclusion → full list of changed files with reasons → checks run and results (say so for checks you didn't run) → remaining work and open questions.
- [hc] When done or blocked: hc send <central HC_TERMINAL_ID> "[<slug>] <done|blocked|decision needed>: <one or two line summary>"
- [hc] Write the full contents to <central scratchpad>/reports/<slug>.md. After reporting, wait for the next instruction; don't end the session.
- [subagent] Your final reply is the report. First line: "[<slug>] <done|blocked|decision needed>: <one or two line summary>", then the contents. If you are blocked or need a decision, don't guess and continue; stop and report right there. Answers and further instructions will come as your next message.
- [orca] Follow the injected Orca preamble. For a decision, use its `ask` command and wait for the answer; don't guess. When done or blocked, first write the full report as your last message (first line "[<slug>] <done|blocked>: <one or two line summary>"), then send `worker_done` once with a three-sentence summary and `--outcome succeeded` (done) or `--outcome failed` (blocked).
```
