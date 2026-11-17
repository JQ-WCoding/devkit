"""devkit PreToolUse guard: enforces Git and run rules that must hold every time, in code instead of prose.

Input: the PreToolUse JSON Claude Code sends on stdin (tool_name Bash|PowerShell, tool_input.command, cwd).
hooks.json runs it with python3 directly (exec form, no shell), so it behaves the same on macOS, Linux and Windows.
Output: hookSpecificOutput (permissionDecision deny|ask) only when it intervenes; otherwise nothing (normal permission flow).
Disable: the plugin option guard (/plugin > devkit > Configure options) or DEVKIT_GUARD=off. Allow AI attribution: DEVKIT_AI_TRAILER=allow.
Under zsh (Bash tool, $SHELL ends in zsh) it also denies unquoted words zsh fails on: `====` and `--opt=*.glob`.
Per repo: server commands that fully match an allow_server pattern in .devkit/guard.json pass without asking.
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
GUARD_CONFIG = os.path.join('.devkit', 'guard.json')  # per-repo {"allow_server": [pattern | {"pattern", "reason"}]}
RUNTIME_CONFIG = os.path.join('.devkit', 'runtime.json')
HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'skills', 'run-app', 'scripts', 'runtime.py')
ASSIGNMENT = re.compile(r'^[A-Za-z_]\w*=')
ZSH_OPT_GLOB = re.compile(r'^--?[\w-]+=')  # an option word whose value zsh globs as a whole (NOMATCH)
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


def shell_words(segment):
    """Split like a shell: [(text, quoted)] where quoted[i] says whether character i was quoted or escaped."""
    words, text, quoted, quote, i = [], [], [], None, 0
    while i < len(segment):
        c = segment[i]
        if quote:
            if c == quote:
                quote = None
            elif c == '\\' and quote == '"' and i + 1 < len(segment):
                i += 1
                text.append(segment[i]), quoted.append(True)
            else:
                text.append(c), quoted.append(True)
        elif c in '\'"':
            quote = c
        elif c == '\\' and i + 1 < len(segment):
            i += 1
            text.append(segment[i]), quoted.append(True)
        elif c.isspace():
            if text or quoted:
                words.append((''.join(text), quoted))
            text, quoted = [], []
        else:
            text.append(c), quoted.append(False)
        i += 1
    if text:
        words.append((''.join(text), quoted))
    return words


def zsh_trap(segment):
    """A reason when zsh would fail on an unquoted word that bash passes through literally."""
    if '[[' in segment:  # [[ a == b ]] is parsed as a condition, not expanded
        return None
    leading = True  # VAR=value words before the command name
    for text, quoted in shell_words(segment):
        bare = lambda i: i < len(text) and not quoted[i]
        if bare(0) and bare(1) and text[:2] == '==':  # zsh EQUALS: `====` looks up a command named `===`
            return (f'zsh reads the unquoted word `{text}` as a command path and fails ("{text[1:]} not found"). '
                    f"Quote it: '{text}'")
        m = ASSIGNMENT.match(text)
        if leading and m and bare(m.end()) and text[m.end()] == '=':  # VAR==x: the value =x is expanded the same way
            name, value = text[:m.end()], text[m.end():]
            return (f'zsh reads the unquoted value `{value}` as a command path and fails ("{value[1:]} not found"). '
                    f"Quote it: {name}'{value}'")
        leading = leading and bool(m)
        m = ZSH_OPT_GLOB.match(text)
        if m and any(text[i] in '*?' and not quoted[i] for i in range(m.end(), len(text))):  # zsh NOMATCH
            return (f'zsh globs the unquoted `{text}` and fails ("no matches found"). '
                    f"Quote the pattern: {text[:m.end()]}'{text[m.end():]}'")
    return None


def check(command, cwd, zsh=False):
    for seg in segments(command):
        if zsh and (reason := zsh_trap(seg)):
            return decide('deny', reason)
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
                if allowed_server(seg, cwd):
                    break
                reason = f'This is a {what} command. Start or stop servers and containers only when the user asks'
                if find_up(cwd, RUNTIME_CONFIG):
                    reason += (f'. This repo uses the runtime harness: python3 -I "{HARNESS}" up|status|down '
                               '(see the devkit:run-app skill)')
                return decide('ask', reason)
    return None


def find_up(cwd, rel):
    """Nearest <dir>/<rel> from cwd upward; worktrees under <repo>/worktrees/ find the main repo's .devkit/."""
    d = os.path.abspath(cwd)
    while True:
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def allowed_server(segment, cwd):
    """True if the segment fully matches an allow_server pattern in the repo's .devkit/guard.json."""
    path = find_up(cwd, GUARD_CONFIG)
    if not path:
        return False
    try:
        with open(path, encoding='utf-8') as f:
            entries = json.load(f).get('allow_server') or []
    except (OSError, ValueError, AttributeError):
        return False  # unreadable config: keep asking
    for entry in entries:
        pattern = entry.get('pattern') if isinstance(entry, dict) else entry
        try:
            if isinstance(pattern, str) and re.fullmatch(pattern, segment.strip()):
                return True
        except re.error:
            continue
    return False


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
    zsh = data.get('tool_name') == 'Bash' and os.environ.get('SHELL', '').endswith('zsh')
    out = check(command, data.get('cwd') or os.getcwd(), zsh)
    if out:
        print(json.dumps(out))  # ASCII-escaped: survives any shell or code page
    return 0


if __name__ == '__main__':
    sys.exit(main())
