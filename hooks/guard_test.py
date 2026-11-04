"""guard.py decision tests (Korean commit messages are intentional multibyte test data). Usage: python3 -I hooks/guard_test.py"""
import json
import os
import subprocess
import sys
import tempfile

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'guard.py')
TMP = tempfile.mkdtemp()
with open(os.path.join(TMP, 'msg-ai.txt'), 'w') as f:
    f.write('fix(api): 수정\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>\n')
with open(os.path.join(TMP, 'msg-ok.txt'), 'w') as f:
    f.write('fix(api): 수정\n\nSigned-off-by: Dev <dev@example.com>\n')

HEREDOC_AI = '''git commit -m "$(cat <<'EOF'
feat(web): 화면 추가

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"'''
HEREDOC_OK = '''git commit -m "$(cat <<'EOF'
feat(web): npm run dev 화면 문구 수정; docker compose up 안내
EOF
)"'''

CASES = [
    # deny
    ('git add .', 'deny'), ('git add -A', 'deny'), ('git add --all', 'deny'), ('git add -u', 'deny'),
    ('cd app && git add .', 'deny'), ('git -C sub add .', 'deny'),
    ('git commit -am "x"', 'deny'), ('git commit -n -m x', 'deny'), ('git commit --no-verify -m x', 'deny'),
    ('git push --force origin feat', 'deny'), ('git push -f', 'deny'), ('git push origin +feat', 'deny'),
    ('git push --no-verify', 'deny'), ('git commit -m "x" && git push --force', 'deny'),
    (HEREDOC_AI, 'deny'), (f'git commit -F {TMP}/msg-ai.txt', 'deny'),
    # ask
    ('git push --force-with-lease origin feat', 'ask'), ('git push -u origin main', 'ask'),
    ('git push origin HEAD:release/1.2', 'ask'), ('git commit --amend --no-edit', 'ask'),
    ('./gradlew bootRun', 'ask'), ('./mvnw spring-boot:run', 'ask'), ('npm run dev', 'ask'),
    ('cd web && pnpm dev', 'ask'), ('docker compose up -d', 'ask'),
    # pass
    ('git add -- src/a.java .gitignore', None), ('git add ./src/x.java', None), ('git status --porcelain', None),
    ('git commit -m "fix(api): 수정"', None), (f'git commit -F {TMP}/msg-ok.txt', None), ('git commit -s -m x', None),
    (HEREDOC_OK, None), ('git commit -m "a; npm run dev 문구"', None), ('git push -u origin feat/ABC-1-x', None), ('git push -n origin main:feat', None),
    ('npm run build', None), ('./mvnw -q compile', None), ('./gradlew --no-daemon test', None),
    ('grep -rn "git add ." docs', None), ('echo "npm run dev"', None), ('ls', None),
]


HERE = os.path.dirname(GUARD)


def run(command, env=None, tool='Bash'):
    payload = json.dumps({'tool_name': tool, 'tool_input': {'command': command}, 'cwd': TMP})
    p = subprocess.run([sys.executable, '-I', GUARD], input=payload.encode('utf-8'), capture_output=True,
                       env={**os.environ, **(env or {})})
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode('ascii')  # output must always be ASCII (code-page independent)
    return json.loads(out)['hookSpecificOutput']['permissionDecision'] if out.strip() else None


fails, total = [], 0
for label, cases, kw in (('Bash tool', CASES, {}),
                         ('PowerShell tool', [('git add .', 'deny'), ('git.exe add -A', 'deny'), ('git add -- a.txt', None)],
                          {'tool': 'PowerShell'})):
    for c, want in cases:
        total += 1
        if (got := run(c, **kw)) != want:
            fails.append((label, c, want, got))
for label, c, env in (('DEVKIT_GUARD=off', 'git add .', {'DEVKIT_GUARD': 'off'}),
                      ('DEVKIT_AI_TRAILER=allow', HEREDOC_AI, {'DEVKIT_AI_TRAILER': 'allow'})):
    total += 1
    if got := run(c, env):
        fails.append((label, c, None, got))
total += 1
p = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'session_start.py')], capture_output=True)
ctx = json.loads(p.stdout.decode('ascii'))['hookSpecificOutput']['additionalContext']
if p.returncode or not ctx.startswith('# devkit'):
    fails.append(('session_start.py', '', '# devkit…', ctx[:20]))
for label, c, want, got in fails:
    print(f'FAIL [{label}] want={want} got={got}: {c!r}')
print(f'{total - len(fails)}/{total} passed')
sys.exit(1 if fails else 0)
