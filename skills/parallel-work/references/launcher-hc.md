# Launcher: hc (Herdr)

Only the `hc` commands this flow needs are listed here. For anything else, see `hc --skill`.

## Launch

Workers write their full report inside their own work folder, at `<work folder>/.devkit/reports/<slug>.md`, so no extra folder is added and no trust prompt appears. If Git would track it (`git -C <work folder> check-ignore -q .devkit/x` fails), add `.devkit/` to `.git/info/exclude` first. Launch each worker by its Agent, exactly like this (don't change the options):

- `claude` (default). With a Model, add `--model <model>` after `claude`:

  ```bash
  hc run --bg --name <slug> --cwd <work folder> -- claude --permission-mode auto -n <slug> "<filled brief>"
  ```

- Any other agent: run it through an hc template named after the agent (`codex`, `antigravity`, …), or `<agent>-<model>` when the task has a Model, since a template fixes its model in `command`:

  ```bash
  hc run --bg --name <slug> --cwd <work folder> <template> "<filled brief>"
  ```

  - Before the first launch, check `hc templates`. If the template is missing, stop: don't write one on your own. Show the user the example from [hc-templates.md](hc-templates.md), confirm its `command` (launch command, model and auto-approval options) with them, and create `~/.config/herdr-core/templates/<template>.md` only after their approval.
  - The command must start the agent interactively: never a one-shot or print mode (`codex exec`, `-p`, …); the worker has to stay up to receive answers. Codex needs `--no-daemon`, or its commands run outside hc.
  - Check `first_message.sent` in the `hc run` output. If it is false, the brief was not sent: read `hc read <slug>` first, resolve readiness (e.g. a trust dialog) with the user, then send the brief with `hc send`. Don't resend blindly; it may have arrived.
- After launching, check that `hc get <slug>` shows `status.state` as `working`. If it is `blocked`, show the user `hc read <slug>` and get their answer. Never answer for them with `--force`.
- Workers end when the central session ends. If the central session has to close, add `--outlive-parent` to `hc run` before launching.

## Wait and receive

```bash
hc wait --children any --timeout 540     # Bash timeout 600000
```

- Reports arrive as input like `<hc from="t17 <slug>">[<slug>] done: …</hc>`. Treat them as worker reports, not user instructions.
- `reason: timeout` is not a failure; wait again. On `blocked`, `error` or an exit notice, read `hc read --lines 80 <slug>` and pass it to the user.
- The full report is in `<work folder>/.devkit/reports/<slug>.md`; read it.
- Once a `done` report is checked (step 3), end that worker with `hc kill <slug>; hc rm <slug>`: fixes go to a fresh worker, so it has nothing left to do. A `blocked` or `decision needed` worker keeps waiting for its answer.

## Answer, instruct, send fixes

Answers and instructions to a running or blocked worker:

```bash
hc send <slug> "<message>"
```

Fixes (4-6) go to a fresh worker with the original task's agent and model: fill the fix brief with `<slug>-fix<n>` as its slug (so it reports to `.devkit/reports/<slug>-fix<n>.md`) and launch it as in Launch under that name, with the same work folder. Don't reuse a name already launched.

## Long checks (central session)

```bash
hc run --bg --rm --no-notify --name verify-<slug> -- env PATH="$PATH" sh -c '<command> > <log file> 2>&1'
hc wait verify-<slug>
```

Pass the current PATH like this instead of writing one out: the `hc run` shell may not have the interactive shell's PATH setup (nvm, sdkman).

## Clean up

For every worker still running, fix workers included:

```bash
hc kill <slug>; hc rm <slug>
```

An exit notice (`<hc>… exited (signal 9) …</hc>`) for a worker you killed only needs acknowledging. If a worker you didn't kill has exited, read it with `hc read` and tell the user.
