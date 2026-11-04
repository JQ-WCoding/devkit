---
name: using-devkit
description: Source text of the devkit judgment principles, injected by the SessionStart hook. Invoke directly only to reread them.
disable-model-invocation: true
---

# devkit principles

Repo `CLAUDE.md` and `docs/rules/` override these.

- Make the simplest change within the request. Preserve user changes, surrounding style and line endings; reuse existing shared modules first.
- If unclear, ask or state assumptions. Never call unrun or unchecked work a success. Verify only what is needed or requested.
- DB writes, deploys and deletes need a confirmed target; by default a human runs them. Keep credentials out of output, files and commits. Put temp files in the scratchpad.
- add, commit, push, PR and tracker writes only on request. The devkit hook blocks or confirms forbidden Git commands, AI attribution and server starts.
- Delegate multi-file exploration to `devkit:code-reader`. Start multi-file change requests with `devkit:analyze`.
- On the third repeat of a multi-step task or the second identical correction, suggest `devkit:suggest-skills` once after finishing.
