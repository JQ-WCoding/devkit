#!/usr/bin/env bash
# using-devkit 본문(frontmatter 제외)을 SessionStart additionalContext 로 주입한다.
# 한글·따옴표가 섞인 본문을 손으로 이스케이프하지 않도록 JSON 은 python 으로 만든다.
set -euo pipefail
root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
python3 -I - "$root/skills/using-devkit/SKILL.md" <<'PY'
import json, re, sys
text = open(sys.argv[1], encoding='utf-8').read()
body = re.sub(r'\A---\n.*?\n---\n', '', text, flags=re.S).strip()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": body}}, ensure_ascii=False))
PY
