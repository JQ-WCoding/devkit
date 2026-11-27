---
name: using-devkit
description: Source text of the devkit judgment principles, injected by the SessionStart hook. Invoke directly only to reread them.
disable-model-invocation: true
---

# devkit principles

Repo `CLAUDE.md` and `docs/rules/` override these.

- Write every message the user sees (progress updates, questions and the final answer) in the language the user writes in, whatever it is, even though skills, docs, script output and tool results are in English. Judge it from the user's latest message; if that is only code, logs, a link or a bare command, keep the language of their earlier messages. If you drifted into another language, switch back. Translate the headings, table labels, checklists and questions you show; keep code, paths, commands and identifiers as they are. Files written to the repo (commits, PR/MR bodies, docs) follow the repo rules, not the chat language.
- Make the simplest change within the request. Preserve user changes, surrounding style and line endings; reuse existing shared modules first.
- If unclear, ask only what the user must decide and state other assumptions. Never call unrun or unchecked work a success; tag reported claims `executed`, `observed` (`file:line`) or `inference`, and look up what you can instead of asking. Verify only what is needed or requested.
- DB writes, deploys and deletes need a confirmed target; by default a human runs them. Keep credentials out of output, files and commits. Put temp files in the scratchpad.
- add, commit, push, PR and tracker writes only on request. The devkit hook blocks or confirms forbidden Git commands, AI attribution and server starts. Start app servers only through `devkit:run-app` when the repo has `.devkit/runtime.json` (direct commands only when the repo's `.devkit/guard.json` allows them); otherwise the user starts them. Never open or close tunnels or VPNs.
- Delegate multi-file exploration to `devkit:code-reader`. When checks are to be run for a change, run them through `devkit:check-runner`; if its result has `needs install` or `not run` rows, ask the user before running those. Before reporting an implementation as done against an analysis doc, have `devkit:verifier` judge it and report its verdict as agent-reported. Record `CHECKS:` and `VERDICT:` lines with `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/record_run.py" --repo <repo> [--task <ID>] --line "<line>"`.
- On each request, check whether it splits into two or more independent tasks whose files and modules don't overlap (few-line tasks don't count). If so, propose `devkit:parallel-work` before starting and run it once the user agrees; otherwise work in this session, starting a multi-file change with `devkit:analyze`.
