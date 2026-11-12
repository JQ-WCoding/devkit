"""devkit UserPromptSubmit hook: reminds Claude, on every prompt, to write every user-visible message in the user's language.

The SessionStart principle alone fades in long sessions full of English skills and tool output,
so this short line is attached to each prompt. It names no language: Claude follows whatever
language the user writes in. Disable: the plugin option lang_hook (/plugin > devkit > Configure options) or DEVKIT_LANG_HOOK=off. Keep the wording in step with the first line of skills/using-devkit/SKILL.md.
"""
import json
import os
import sys

# Kept short: it is added to every prompt, so each word repeats once per turn in the context.
REMINDER = (
    "devkit: Reply, including progress and questions, in the user's language (latest message; "
    "if it is only code or logs, earlier ones). Keep code and paths as is."
)

if os.environ.get('DEVKIT_LANG_HOOK') == 'off' or os.environ.get('CLAUDE_PLUGIN_OPTION_LANG_HOOK', '').lower() in ('false', '0'):
    sys.exit(0)
try:
    # Read bytes as UTF-8: -I ignores PYTHONUTF8, and Windows would otherwise decode stdin with the locale code page.
    prompt = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace')).get('prompt')
except (ValueError, AttributeError):
    prompt = None
if isinstance(prompt, str) and prompt.strip():
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': REMINDER}}))
