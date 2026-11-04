"""devkit SessionStart hook: injects the using-devkit body (without frontmatter) into the session context.

Output is ASCII-escaped JSON, so it survives any OS or console code page.
"""
import json
import os
import re
import sys

ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    with open(os.path.join(ROOT, 'skills', 'using-devkit', 'SKILL.md'), encoding='utf-8') as f:
        body = re.sub(r'\A---\n.*?\n---\n', '', f.read().replace('\r\n', '\n'), flags=re.S).strip()
except OSError:
    sys.exit(0)
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': body}}))
