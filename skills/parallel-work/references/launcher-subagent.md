# Launcher: subagent

If Agent, SendMessage or ListAgents appear only by name and not as callable tools, load them first: `ToolSearch` with `select:Agent,SendMessage,ListAgents`.

## Launch

Use the Agent tool once per task: `subagent_type` `general-purpose`, `description` `<slug>`, `prompt` the filled brief. Send all workers that run together in one response. Write down each returned agent ID next to its slug.

Subagents start in the central session's working folder. In worktree mode, make sure the brief includes the line telling the worker to `cd` into its worktree.

## Wait and receive

Completion notices arrive on their own; a subagent's final reply is its report. Don't poll, and don't guess a result before it arrives. If a subagent failed or was stopped, pass that to the user.

Subagents can't ask the user anything mid-run. The brief tells them to stop and report when they need a decision: ask the user, then send the answer with SendMessage.

## Answer, instruct, send fixes

- Answers and instructions to a running or blocked worker: SendMessage with `to` set to the agent ID. The subagent continues with its earlier context.
- Fixes (4-6) go to a fresh subagent, launched as in Launch, not to the agent that reported done. Its prompt is the original brief plus a "Fix" section holding the problem, the scope to fix and the earlier agent's final reply (its report).

## Long checks (central session)

Run them with Bash `run_in_background`, writing output to a log file.

## Clean up

Nothing to do.
