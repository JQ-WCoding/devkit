"""devkit PreToolUse 가드: 매번 예외 없이 지켜야 하는 Git·실행 규칙을 문장 대신 코드로 강제한다.

입력: Claude Code 가 stdin 으로 주는 PreToolUse JSON(tool_name Bash|PowerShell, tool_input.command, cwd).
hooks.json 이 셸 없이(exec form) python3 로 직접 실행하므로 macOS·Linux·Windows 에서 같게 동작한다.
출력: 막을 때만 hookSpecificOutput(permissionDecision deny|ask). 그 밖에는 아무것도 출력하지 않는다(일반 권한 흐름).
끄기: 환경 변수 DEVKIT_GUARD=off. AI 작성 표기 허용: DEVKIT_AI_TRAILER=allow.
판단이 애매하면 통과시킨다(오탐으로 정상 작업을 막지 않는다). 판단 규칙은 using-devkit 문장에도 남아 있다.
"""
import json
import os
import re
import shlex
import sys

PROTECTED = re.compile(r'^(main|master|prod.*|production|release/.+)$')
AI_TRAILER = re.compile(r'Co-Authored-By:\s*Claude|Generated with \[?Claude Code', re.I)
SERVER = [
    (re.compile(r'\b(bootRun|spring-boot:run|quarkus:dev)\b'), '서버 기동'),
    (re.compile(r'\b(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|start|serve|preview)\b'), '개발 서버 기동'),
    (re.compile(r'\bdocker[- ]compose\b.*\b(up|down|stop|restart)\b'), '컨테이너 기동·중지'),
    (re.compile(r'\b(manage\.py\s+runserver|flask\s+run|uvicorn|rails\s+s(erver)?)\b'), '서버 기동'),
]
RUNNERS = {'gradle', 'gradlew', 'mvn', 'mvnw', 'npm', 'pnpm', 'yarn', 'bun', 'npx', 'docker', 'docker-compose',
           'python', 'python3', 'flask', 'uvicorn', 'rails', 'bundle'}
HEREDOC = re.compile(r'<<-?\s*([\'"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\b', re.S)


def segments(command):
    """따옴표·heredoc 밖의 ; & | 줄바꿈으로 명령을 나눈다(메시지 본문 속 문구를 명령으로 보지 않는다)."""
    text = HEREDOC.sub('<<HEREDOC', command)
    out, cur, quote, i = [], [], None, 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\' and quote == '"' and i + 1 < len(text):
                cur.append(text[i:i + 2])
                i += 2
                continue
            quote = None if c == quote else quote
        elif c in '\'"':
            quote = c
        elif c in ';&|\n':
            out.append(''.join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    out.append(''.join(cur))
    return [s.strip() for s in out if s.strip()]


def decide(kind, reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': kind,
                                   'permissionDecisionReason': f'[devkit] {reason}'}}


def git_args(segment):
    """`git [-C dir] [-c k=v] <sub> args` 에서 (sub, args) 를 돌려준다. git 명령이 아니면 None."""
    try:
        tok = shlex.split(segment)
    except ValueError:
        tok = segment.split()
    while tok and re.match(r'^\w+=', tok[0]):  # 앞의 VAR=value
        tok = tok[1:]
    if not tok or re.sub(r'\.exe$', '', os.path.basename(tok[0]).lower()) != 'git':
        return None
    i = 1
    while i < len(tok) and tok[i].startswith('-'):
        i += 2 if tok[i] in ('-C', '-c', '--git-dir', '--work-tree') else 1
    if i >= len(tok):
        return None
    return tok[i], tok[i + 1:]


def short_flags(args):
    return {c for a in args if re.match(r'^-[A-Za-z]+$', a) for c in a[1:]}


def check_git(sub, args, command, cwd):
    flags = short_flags(args)
    if sub == 'add':
        paths = args[args.index('--') + 1:] if '--' in args else [a for a in args if not a.startswith('-')]
        if {'-A', '--all', '-u', '--update'} & set(args) or 'A' in flags or any(p in ('.', './', '*', ':/') for p in paths):
            return decide('deny', '파일을 지정해 스테이징한다: `git add -- <파일...>` (`git add .`·`-A`·`-u` 금지)')
    if sub in ('commit', 'push', 'merge', 'rebase') and '--no-verify' in args:
        return decide('deny', '`--no-verify`로 훅을 우회하지 않는다. 훅 실패 원인을 보고한다')
    if sub == 'commit':
        if 'n' in flags:
            return decide('deny', '`git commit -n`(--no-verify)으로 훅을 우회하지 않는다')
        if 'a' in flags or '--all' in args:
            return decide('deny', '`git commit -a` 대신 파일을 지정해 스테이징한 뒤 커밋한다')
        if os.environ.get('DEVKIT_AI_TRAILER') != 'allow' and AI_TRAILER.search(commit_message(args, command, cwd)):
            return decide('deny', 'AI 작성 표기(Co-Authored-By: Claude 등)를 빼고 다시 커밋한다. '
                          '저장소 규칙이 요구하면 DEVKIT_AI_TRAILER=allow 로 허용한다')
        if '--amend' in args:
            return decide('ask', '`--amend`는 이전 커밋을 다시 쓴다. 사용자가 요청한 것인지 확인한다')
    if sub == 'push':
        if '--force' in args or 'f' in flags or any(a.startswith('+') for a in args):
            return decide('deny', 'force push 금지. 꼭 필요하면 덮어쓸 원격 커밋을 보여 주고 확인받은 뒤 `--force-with-lease`로 한다')
        if any(a.startswith('--force-with-lease') or a == '--force-if-includes' for a in args):
            return decide('ask', '`--force-with-lease`는 원격 커밋을 덮어쓴다. 덮어쓸 커밋을 확인했는지 묻는다')
        refs = [a.split(':')[-1] for a in args if not a.startswith('-')][1:]
        if any(PROTECTED.match(r.replace('refs/heads/', '')) for r in refs):
            return decide('ask', '보호·배포 브랜치로 직접 push한다. 저장소 흐름상 PR/MR이 아닌지 확인한다')
    return None


def commit_message(args, command, cwd):
    msg = [command]  # -m 문자열·heredoc 본문은 명령 문자열에 들어 있다
    for i, a in enumerate(args):
        path = None
        if a in ('-F', '--file') and i + 1 < len(args):
            path = args[i + 1]
        elif a.startswith('--file='):
            path = a.split('=', 1)[1]
        if path and path != '-':
            try:
                with open(os.path.join(cwd, os.path.expanduser(path)), encoding='utf-8', errors='replace') as f:
                    msg.append(f.read())
            except OSError:
                pass
    return '\n'.join(msg)


def check(command, cwd):
    for seg in segments(command):
        parsed = git_args(seg)
        if parsed:
            out = check_git(*parsed, command, cwd)
            if out:
                return out
            continue
        first = re.sub(r'^(\w+=\S*\s+)*', '', seg).split(' ', 1)[0]
        if os.path.basename(first) not in RUNNERS:  # 커밋 메시지 본문 같은 줄은 명령이 아니다
            continue
        for pat, what in SERVER:
            if pat.search(seg):
                return decide('ask', f'{what} 명령이다. 서버·컨테이너는 사용자가 요청했을 때만 켜고 끈다')
    return None


def main():
    if os.environ.get('DEVKIT_GUARD') == 'off':
        return 0
    try:
        # 콘솔 인코딩(cp949 등)과 무관하게 UTF-8 로 읽는다
        data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))
    except ValueError:
        return 0
    if data.get('tool_name') not in ('Bash', 'PowerShell'):
        return 0
    command = (data.get('tool_input') or {}).get('command') or ''
    out = check(command, data.get('cwd') or os.getcwd())
    if out:
        print(json.dumps(out))  # ASCII 이스케이프: 어느 셸·코드 페이지를 거쳐도 깨지지 않는다
    return 0


if __name__ == '__main__':
    sys.exit(main())
