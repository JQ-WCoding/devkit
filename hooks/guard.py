"""devkit PreToolUse guard: enforces Git and run rules that must hold every time, in code instead of prose.

Input: the PreToolUse JSON Claude Code sends on stdin (tool_name Bash|PowerShell, tool_input.command, cwd).
hooks.json runs it with python3 directly (exec form, no shell), so it behaves the same on macOS, Linux and Windows.
Output: hookSpecificOutput (permissionDecision deny|ask) only when it intervenes; otherwise nothing (normal permission flow).
Disable: the plugin option guard (/plugin > devkit > Configure options) or DEVKIT_GUARD=off. Allow AI attribution: DEVKIT_AI_TRAILER=allow.
When unsure it lets the command through (a false positive must not block real work).
"""
import json
import os
import re
import shlex
import sys

PROTECTED = re.compile(r'^(main|master|prod.*|production|release/.+)$')
AI_TRAILER = re.compile(r'Co-Authored-By:\s*Claude|Generated with \[?Claude Code', re.I)
SERVER = [
    (re.compile(r'\b(bootRun|spring-boot:run|quarkus:dev)\b'), 'server start'),
    (re.compile(r'\b(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|start|serve|preview)\b'), 'dev server start'),
    (re.compile(r'\bdocker[- ]compose\b.*\b(up|down|stop|restart)\b'), 'container start/stop'),
    (re.compile(r'\b(manage\.py\s+runserver|flask\s+run|uvicorn|rails\s+s(erver)?)\b'), 'server start'),
]
RUNNERS = {'gradle', 'gradlew', 'mvn', 'mvnw', 'npm', 'pnpm', 'yarn', 'bun', 'npx', 'docker', 'docker-compose',
           'python', 'python3', 'flask', 'uvicorn', 'rails', 'bundle'}
HEREDOC = re.compile(r'<<-?\s*([\'"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\b', re.S)


def segments(command):
    """Split on ; & | and newlines outside quotes and heredocs (text inside a commit message is not a command)."""
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
    """Return (sub, args) for `git [-C dir] [-c k=v] <sub> args`, or None if it is not a git command."""
    try:
        tok = shlex.split(segment)
    except ValueError:
        tok = segment.split()
    while tok and re.match(r'^\w+=', tok[0]):  # leading VAR=value
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
            return decide('deny', 'Stage named files: `git add -- <files...>` (no `git add .`, `-A` or `-u`)')
    if sub in ('commit', 'push', 'merge', 'rebase') and '--no-verify' in args:
        return decide('deny', 'Do not bypass hooks with `--no-verify`. Report why the hook failed')
    if sub == 'commit':
        if 'n' in flags:
            return decide('deny', 'Do not bypass hooks with `git commit -n` (--no-verify)')
        if 'a' in flags or '--all' in args:
            return decide('deny', 'Instead of `git commit -a`, stage named files and then commit')
        if os.environ.get('DEVKIT_AI_TRAILER') != 'allow' and AI_TRAILER.search(commit_message(args, command, cwd)):
            return decide('deny', 'Remove the AI attribution (Co-Authored-By: Claude etc.) and commit again. '
                          'If the repo rules require it, allow it with DEVKIT_AI_TRAILER=allow')
        if '--amend' in args:
            return decide('ask', '`--amend` rewrites the previous commit. Confirm the user asked for it')
    if sub == 'push':
        if '--force' in args or 'f' in flags or any(a.startswith('+') for a in args):
            return decide('deny', 'No force push. If truly needed, show the remote commits it would overwrite, get confirmation, then use `--force-with-lease`')
        if any(a.startswith('--force-with-lease') or a == '--force-if-includes' for a in args):
            return decide('ask', '`--force-with-lease` overwrites remote commits. Confirm the commits to overwrite were reviewed')
        refs = [a.split(':')[-1] for a in args if not a.startswith('-')][1:]
        if any(PROTECTED.match(r.replace('refs/heads/', '')) for r in refs):
            return decide('ask', 'Direct push to a protected or release branch. Confirm the repo flow does not require a PR/MR')
    return None


def commit_message(args, command, cwd):
    msg = [command]  # -m strings and heredoc bodies are part of the command string
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
        if os.path.basename(first) not in RUNNERS:  # lines such as commit message bodies are not commands
            continue
        for pat, what in SERVER:
            if pat.search(seg):
                return decide('ask', f'This is a {what} command. Start or stop servers and containers only when the user asks')
    return None


def main():
    if os.environ.get('DEVKIT_GUARD') == 'off' or os.environ.get('CLAUDE_PLUGIN_OPTION_GUARD', '').lower() in ('false', '0'):
        return 0
    try:
        # read as UTF-8 regardless of the console code page (cp949 etc.)
        data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))
    except ValueError:
        return 0
    if data.get('tool_name') not in ('Bash', 'PowerShell'):
        return 0
    command = (data.get('tool_input') or {}).get('command') or ''
    out = check(command, data.get('cwd') or os.getcwd())
    if out:
        print(json.dumps(out))  # ASCII-escaped: survives any shell or code page
    return 0


if __name__ == '__main__':
    sys.exit(main())
