"""devkit UserPromptSubmit hook: reminds Claude, on every prompt, to write every user-visible message in the user's language.

The SessionStart principle alone fades in long sessions full of English skills and tool output,
so this short line is attached to each prompt. It names no language: Claude follows whatever
language the user writes in. Disable: DEVKIT_LANG_HOOK=off. Keep the wording in step with the first line of skills/using-devkit/SKILL.md.
"""
import json
import os
import sys

REMINDER = (
    "devkit: Write every message the user sees this turn (progress updates, questions, final answer) in the "
    "language the user writes in, judged from their latest message; if it is only code, logs, a link or a bare "
    "command, keep the language of their earlier messages. Keep code, paths and identifiers as they are."
)

if os.environ.get('DEVKIT_LANG_HOOK') == 'off':
    sys.exit(0)
try:
    # Read bytes as UTF-8: -I ignores PYTHONUTF8, and Windows would otherwise decode stdin with the locale code page.
    prompt = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace')).get('prompt')
except (ValueError, AttributeError):
    prompt = None
if isinstance(prompt, str) and prompt.strip():
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': REMINDER}}))
