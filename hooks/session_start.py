"""devkit SessionStart 훅: using-devkit 본문(frontmatter 제외)을 세션 컨텍스트로 넣는다.

출력은 ASCII 이스케이프 JSON 이라 OS·콘솔 코드 페이지와 관계없이 깨지지 않는다.
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
