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


def run(command, env=None, tool='Bash', cwd=TMP, reason=False):
    payload = json.dumps({'tool_name': tool, 'tool_input': {'command': command}, 'cwd': cwd})
    p = subprocess.run([sys.executable, '-I', GUARD], input=payload.encode('utf-8'), capture_output=True,
                       env={**{k: v for k, v in os.environ.items() if not k.startswith(('DEVKIT_', 'CLAUDE_PLUGIN_OPTION_'))}, **(env or {})})
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode('ascii')  # output must always be ASCII (code-page independent)
    if not out.strip():
        return None
    hook = json.loads(out)['hookSpecificOutput']
    return hook['permissionDecisionReason'] if reason else hook['permissionDecision']


fails, total = [], 0
for label, cases, kw in (('Bash tool', CASES, {}),
                         ('PowerShell tool', [('git add .', 'deny'), ('git.exe add -A', 'deny'), ('git add -- a.txt', None)],
                          {'tool': 'PowerShell'})):
    for c, want in cases:
        total += 1
        if (got := run(c, **kw)) != want:
            fails.append((label, c, want, got))
ZSH = {'SHELL': '/bin/zsh'}
ZSH_CASES = [
    ('cat a.md; echo ====; cat b.md', 'deny'), ("printf '%s\\n' ===== x", 'deny'), ('[ "$a" == "$b" ] && echo same', 'deny'),
    ('grep -rn --include=*.java foo src', 'deny'), ('rg --glob=*.md x', 'deny'),
    ("echo '===='", None), ('echo "=== title ==="', None), ('[[ $a == b ]] && echo y', None), ('echo = x', None),
    ("grep -rn --include='*.java' foo src", None), ('git log --format=%h --since=2.weeks', None), ('VAR==x env', 'deny'), ("VAR='=x' env", None),
    ('git commit -m "a\n\n====\n"', None), ("cat <<'EOF'\n====\nEOF", None),
    ('echo x ==y', 'deny'), ('X=1 VAR==x env', 'deny'),
    # argument-position == and quotes that open mid-word run fine in zsh (checked with zsh -c)
    ('pip install requests==2.31.0', None), ('echo a==b', None), ('git log --grep="a == b"', None),
    ('git commit -m"a ==== b"', None), ("gh api x --jq='.x == 1'", None), ('FOO="x ==== y" env', None),
    ('echo \\==', None), ('ls --color=auto', None),
]
for c, want in ZSH_CASES:
    total += 1
    if (got := run(c, ZSH)) != want:
        fails.append(('zsh', c, want, got))
for label, c, kw in (('bash shell', 'cat a; echo ====', {'env': {'SHELL': '/bin/bash'}}),
                     ('PowerShell tool under zsh', 'echo ====', {'env': ZSH, 'tool': 'PowerShell'})):
    total += 1
    if got := run(c, **kw):
        fails.append((label, c, None, got))
total += 1
if 'Quote it' not in (run('echo ====', ZSH, reason=True) or ''):
    fails.append(('zsh reason names the fix', 'echo ====', 'Quote it', None))
for label, c, env in (('DEVKIT_GUARD=off', 'git add .', {'DEVKIT_GUARD': 'off'}),
                      ('option guard=false', 'git add .', {'CLAUDE_PLUGIN_OPTION_GUARD': 'false'}),
                      ('DEVKIT_AI_TRAILER=allow', HEREDOC_AI, {'DEVKIT_AI_TRAILER': 'allow'})):
    total += 1
    if got := run(c, env):
        fails.append((label, c, None, got))
# per-repo allow list (.devkit/guard.json) and the runtime harness hint, also from a worktree below the repo
REPO = os.path.join(TMP, 'repo')
WT = os.path.join(REPO, 'worktrees', 'task-a', 'web')
os.makedirs(WT)
os.makedirs(os.path.join(REPO, '.devkit'))
with open(os.path.join(REPO, '.devkit', 'guard.json'), 'w') as f:
    json.dump({'allow_server': [{'pattern': r'npm run dev( .*)?', 'reason': 'web dev server'}, '[bad(regex']}, f)
for c, cwd, want in (('npm run dev', REPO, None), ('cd web && npm run dev -- --port 3011', WT, None),
                     ('npm run preview', REPO, 'ask'), ('./gradlew bootRun', REPO, 'ask'),
                     ('npm run dev && rm -rf x', REPO, None), ('npm run dev', TMP, 'ask')):
    total += 1
    if (got := run(c, cwd=cwd)) != want:
        fails.append(('allow_server', f'{c} @ {cwd}', want, got))
with open(os.path.join(REPO, '.devkit', 'runtime.json'), 'w') as f:
    f.write('{}')
total += 1
if 'runtime harness' not in (got := run('./gradlew bootRun', cwd=REPO, reason=True) or ''):
    fails.append(('runtime hint', './gradlew bootRun', 'reason mentions runtime harness', got))
total += 1
if 'runtime harness' in (got := run('./gradlew bootRun', reason=True) or ''):
    fails.append(('no runtime hint without runtime.json', './gradlew bootRun', 'plain reason', got))
with open(os.path.join(REPO, '.devkit', 'guard.json'), 'w') as f:
    f.write('{not json')
total += 1
if (got := run('npm run dev', cwd=REPO)) != 'ask':
    fails.append(('unreadable guard.json keeps asking', 'npm run dev', 'ask', got))
total += 1
p = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'session_start.py')], capture_output=True)
ctx = json.loads(p.stdout.decode('ascii'))['hookSpecificOutput']['additionalContext']
if p.returncode or not ctx.startswith('# devkit'):
    fails.append(('session_start.py', '', '# devkit…', ctx[:20]))
for raw, want in ((json.dumps({'prompt': '한국어 요청'}, ensure_ascii=False).encode('utf-8'), True),
                  (json.dumps({'prompt': 'これを直して'}, ensure_ascii=False).encode('utf-8'), True),
                  (b'{"prompt": "fix this"}', True),
                  (b'{"prompt": "   "}', False), (b'{"prompt": 123}', False), (b'{}', False),
                  (b'[]', False), (b'null', False), (b'not json', False)):
    total += 1
    p = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'user_prompt.py')], input=raw, capture_output=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith(('DEVKIT_', 'CLAUDE_PLUGIN_OPTION_'))})
    got = bool(p.stdout.strip()) and 'additionalContext' in json.loads(p.stdout)['hookSpecificOutput']
    if p.returncode or got != want:
        fails.append(('user_prompt.py', raw.decode('utf-8'), want, f'{got} rc={p.returncode}'))
for off in ({'DEVKIT_LANG_HOOK': 'off'}, {'CLAUDE_PLUGIN_OPTION_LANG_HOOK': 'false'}):
    total += 1
    p = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'user_prompt.py')], input=b'{"prompt": "fix this"}',
                       capture_output=True, env={**os.environ, **off})
    if p.returncode or p.stdout.strip():
        fails.append((f'user_prompt.py {off}', 'fix this', 'no output', p.stdout[:40]))
for label, c, want, got in fails:
    print(f'FAIL [{label}] want={want} got={got}: {c!r}')
print(f'{total - len(fails)}/{total} passed')
sys.exit(1 if fails else 0)
