# Blueprint: tool skill

Collects the explanations and pitfalls repeated every time an external tool that is hard to install or configure (report designer, physical-device verification, in-house CLI or SDK) is used.

## Files to create

- `SKILL.md` — mode table (e.g. `setup` · `design` · `integrate`, or a command table), how to pick a mode, common prohibitions
- With two or more modes, one doc per mode (`setup.md` etc.). End each with a "When something goes wrong" table (symptom → reference doc)
- `references/` — summaries of only what this project needs from the tool's docs. Over 100 lines gets a `Contents:` line
- `scripts/` — repeated deterministic work (file conversion, connection checks, captures). Error messages should say what to do next
- `SETUP.md` — human installation guide (not in SKILL.md)
- `evals/evals.json`

## Criteria for the body

- For physical devices or external services, state "what not to touch" (personal tabs, device settings, install commands, etc.).
- Actions that write to a dev DB or external system need user approval before pressing or running. Invoking the skill is not write approval.
- Link the repo rule that servers are not started or stopped.
- Keep credentials (license keys, passwords) out of command output, conversation and docs.
- If the reference docs and actual tool behavior differ, take actual behavior as the reference, tell the user, then fix the reference doc.
- Attach `checked scope (YYYY-MM-DD)` to facts such as devices and versions.
