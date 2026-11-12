"""List temp files left in a git working tree, and move chosen ones to the OS trash. Python 3.8+, any OS.

Usage:
  python3 -I clean_temp.py scan  <repo root> [--scratchpad <this session's scratchpad path>]
  python3 -I clean_temp.py trash <repo root> [--scratchpad <path>] <paths...>

scan only lists; it deletes nothing. trash refuses tracked files, protected paths and anything outside
the repo or the scratch root, checks every path before moving any, and never deletes permanently.
Repo-specific protections: <repo>/.devkit/clean-temp/config.json  {"protect": ["<glob>", ...]}
  Globs match repo-relative paths; `*` also matches `/`; a trailing `/` means everything under it.
"""
import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import time

CONFIG = os.path.join('.devkit', 'clean-temp', 'config.json')

# Never listed or touched: in-progress sources, tests, dependencies, build output, logs, tool and agent
# folders (.worktrees = parallel-work worktrees, .devkit = devkit work docs and state).
PROTECTED_DIR_PARTS = {'src', 'test', 'tests', '__tests__', 'node_modules', '.gradle', 'build', 'out',
                       'dist', 'target', 'logs', '.venv', 'venv', '__pycache__', '.git', '.worktrees',
                       '.devkit', '.claude', '.codex', '.agents', '.idea', '.vscode'}
PROTECTED_NAME_GLOBS = ('CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', 'AGENTS.local.md', '.env*',
                        '.mcp.json', '.DS_Store')

# Removal candidates: shapes that only temp work produces.
TEMP_FILE_GLOBS = ('*.bak', '*.orig', '*.tmp', '*.temp', '*~', '*.swp', '*.swo', '*.rej')
# Temp folders count only at the repo root or under docs/, where dry runs and scratch copies land.
# Bare tmp/temp/scratch need a separator or digit after them, so templates/, tmpl/, temperature/ don't match.
TEMP_DIR_GLOBS = ('_dryrun*', '_tmp*', '_temp*', '_test*', '_scratch*',
                  'tmp', 'tmp[-_.0-9]*', 'temp', 'temp[-_.0-9]*', 'scratch', 'scratch[-_.0-9]*',
                  '.playwright-mcp', 'playwright-report', 'test-results')
# Images count only at the root or directly in docs/ (captures); deeper they may be design work or assets.
IMAGE_GLOBS = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp')
# Logs are out of scope (left to the user), so *.log is not here.
ROOT_NOTE_GLOBS = ('*.py', '*.sh', '*.mjs', '*.cjs', '*.js', '*.md', '*.txt', '*.json', '*.sql')


def die(msg):
    print('ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


def git(args, cwd):
    try:
        r = subprocess.run(['git'] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        die('git not found on PATH')
    if r.returncode != 0:
        die('git %s failed: %s' % (' '.join(args), r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout.decode('utf-8', 'replace')


def repo_root(path):
    if not os.path.isdir(path):
        die('not a folder: ' + path)
    return os.path.realpath(git(['rev-parse', '--show-toplevel'], path).strip())


def load_protect(root):
    path = os.path.join(root, CONFIG)
    if not os.path.exists(path):
        return []
    fix = '. Fix it to the form {"protect": ["<glob>", ...]}'
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        die('cannot read %s (%s)%s' % (path, e, fix))
    globs = data.get('protect', []) if isinstance(data, dict) else None
    if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
        die('%s: "protect" must be a list of non-empty strings%s' % (path, fix))
    return [g + '*' if g.endswith('/') else g for g in globs]


def matches(name, globs):
    return any(fnmatch.fnmatchcase(name, g) for g in globs)


def is_protected(path, protect):
    parts = path.rstrip('/').split('/')
    if PROTECTED_DIR_PARTS.intersection(parts) or matches(parts[-1], PROTECTED_NAME_GLOBS):
        return True
    return matches(path, protect) or matches(path.rstrip('/'), protect)


def temp_dir_of(path):
    parts = path.rstrip('/').split('/')
    dirs = parts if path.endswith('/') else parts[:-1]
    for i, part in enumerate(dirs):
        if matches(part, TEMP_DIR_GLOBS) and (i == 0 or parts[0] == 'docs'):
            return '/'.join(parts[:i + 1]) + '/'
    return None


def classify(path, ignored=False):
    """Return (key, reason) for a removal candidate, or None.

    Ignored files are often local keepsakes (secrets, seed data, settings), so for them only the
    unmistakable temp shapes count: temp folders and backup or swap files.
    """
    parts = path.rstrip('/').split('/')
    name = parts[-1]
    tdir = temp_dir_of(path)
    if tdir:
        return tdir, 'temp folder'
    if matches(name, TEMP_FILE_GLOBS):
        return path, 'backup or swap file'
    if ignored:
        return None
    if matches(name, IMAGE_GLOBS) and (len(parts) == 1 or (len(parts) == 2 and parts[0] == 'docs')):
        return path, 'capture image at the root or directly in docs/'
    if len(parts) == 1 and matches(name, ROOT_NOTE_GLOBS):
        return path, 'temp script or note at the repo root'
    return None


def entries(root):
    out = git(['status', '--porcelain', '--ignored', '-z', '--untracked-files=all'], root)
    for rec in out.split('\0'):
        if len(rec) > 3 and rec[:2] in ('??', '!!'):
            yield rec[:2], rec[3:]


def size_of(path):
    if os.path.isfile(path) or os.path.islink(path):
        return os.lstat(path).st_size
    total = 0
    for cur, _, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(cur, f)).st_size
            except OSError:
                pass
    return total


def latest_mtime(path):
    latest = os.lstat(path).st_mtime
    for cur, dirs, files in os.walk(path):
        for n in dirs + files:
            try:
                latest = max(latest, os.lstat(os.path.join(cur, n)).st_mtime)
            except OSError:
                pass
    return latest


def human(n):
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024:
            return '%.0f%s' % (n, unit)
        n /= 1024.0
    return '%.1fT' % n


def scratch_dirs(scratchpad):
    """(scratch root, this session's folder). Layout: <root>/<session ID>/scratchpad."""
    s = os.path.realpath(scratchpad.rstrip('/\\'))
    session = os.path.dirname(s) if os.path.basename(s) == 'scratchpad' else s
    root = os.path.dirname(session)
    if not os.path.basename(os.path.dirname(root)).startswith('claude'):
        die('%s does not look like a Claude scratch root (<tmp>/claude-*/<project>/<session>/scratchpad). '
            'Pass this session\'s scratchpad path' % root)
    return root, session


def scan(args):
    root = repo_root(args.repo)
    protect = load_protect(root)
    scratch = scratch_dirs(args.scratchpad) if args.scratchpad else None
    candidates, review, protected = {}, set(), []
    members = {}  # temp folder -> its own entries, in case the folder has to be split
    for status, path in entries(root):
        if is_protected(path, protect):
            protected.append(path)
            continue
        hit = classify(path, ignored=(status == '!!'))
        if hit:
            candidates.setdefault(hit[0], hit[1])
            if hit[0] != path:
                members.setdefault(hit[0], []).append(path)
        elif status == '??':
            review.add(path)  # ignored files of unclear shape are local keepsakes: left out entirely
    # A temp folder that also holds protected files is never proposed whole; only its other files are.
    for folder in [k for k in candidates if k.endswith('/')]:
        if any(p.startswith(folder) for p in protected):
            del candidates[folder]
            for p in members.get(folder, []):
                candidates[p] = 'file in a temp folder that also holds protected files'

    print('repo: %s\nconfig: %s' % (root, CONFIG if protect else '(none)'))
    print('\n## Removal candidates')
    for p, reason in sorted(candidates.items()):
        print('- %s\t%s\t%s' % (p, human(size_of(os.path.join(root, p))), reason))
    if not candidates:
        print('(none)')
    print('\n## Needs review (never removed unless the user names it)')
    for p in sorted(review):
        print('- %s\t%s' % (p, human(size_of(os.path.join(root, p)))))
    if not review:
        print('(none)')
    print('\n## Protected: %d entries skipped (sources, tests, dependencies, build output, logs, '
          'agent folders, config protect globs)' % len(protected))

    if scratch:
        sroot, session = scratch
        print('\n## Other sessions\' scratchpads (%s; a recent time may mean a live session, e.g. a parallel worker)'
              % sroot)
        rows = [d for d in sorted(os.listdir(sroot))
                if os.path.join(sroot, d) != session and os.path.isdir(os.path.join(sroot, d))]
        for d in rows:
            p = os.path.join(sroot, d)
            print('- %s\t%s\tlast change %s' % (p, human(size_of(p)),
                                               time.strftime('%Y-%m-%d %H:%M', time.localtime(latest_mtime(p)))))
        if not rows:
            print('(none)')


def inside(path, base):
    return path != base and path.startswith(base.rstrip(os.sep) + os.sep)


def resolve(raw, root):
    """Absolute path with the parent folders resolved but not the last part, so a symlink stays the link."""
    path = os.path.abspath(raw if os.path.isabs(raw) else os.path.join(root, raw))
    return os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))


def protected_inside(folder, rel, protect):
    """First protected path under a folder (the walk does not follow symlinks), or None."""
    for cur, dirs, files in os.walk(folder):
        for name in dirs + files:
            sub = rel + '/' + os.path.relpath(os.path.join(cur, name), folder).replace(os.sep, '/')
            if is_protected(sub, protect):
                return sub
    return None


def check_target(raw, root, protect, sroot, session):
    path = resolve(raw.rstrip('/\\') or raw, root)
    if not os.path.lexists(path):
        return path, 'does not exist'
    if sroot and inside(path, sroot):
        if path == session or inside(path, session):
            return path, "is this session's scratchpad"
        return path, None
    if not inside(path, root):
        return path, 'is outside the repo and the scratch root'
    rel = os.path.relpath(path, root).replace(os.sep, '/')
    if git(['ls-files', '--', rel], root).strip():
        return path, 'is tracked by git (or contains tracked files)'
    is_dir = os.path.isdir(path) and not os.path.islink(path)
    if is_protected(rel + ('/' if is_dir else ''), protect):
        return path, 'is protected'
    if is_dir:
        inner = protected_inside(path, rel, protect)
        if inner:
            return path, 'holds a protected path (%s); pick its other files instead' % inner
    return path, None


def os_trash(paths):
    """Move paths to the OS trash. Returns an error string, or None."""
    if sys.platform == 'darwin':
        tool = shutil.which('trash')
        if tool:
            cmd = [tool] + paths
        else:
            cmd = ['osascript', '-e', 'on run argv', '-e', 'repeat with p in argv',
                   '-e', 'tell application "Finder" to delete (POSIX file (p as text) as alias)',
                   '-e', 'end repeat', '-e', 'end run'] + paths
    elif sys.platform == 'win32':
        script = ('Add-Type -AssemblyName Microsoft.VisualBasic; '
                  '$env:DEVKIT_TRASH -split "`n" | ForEach-Object { '
                  'if (Test-Path -LiteralPath $_ -PathType Container) { '
                  "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($_, 'OnlyErrorDialogs', 'SendToRecycleBin') "
                  '} else { '
                  "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($_, 'OnlyErrorDialogs', 'SendToRecycleBin') } }")
        os.environ['DEVKIT_TRASH'] = '\n'.join(paths)
        cmd = ['powershell', '-NoProfile', '-NonInteractive', '-Command', script]
    else:
        if shutil.which('gio'):
            cmd = ['gio', 'trash', '--'] + paths
        elif shutil.which('trash-put'):
            cmd = ['trash-put', '--'] + paths
        else:
            return 'no trash tool found. Install gio (glib) or trash-cli, then retry'
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        return 'trash tool could not run: %s' % e
    if r.returncode != 0:
        return 'trash tool failed: ' + r.stderr.decode('utf-8', 'replace').strip()
    return None


def trash(args):
    root = repo_root(args.repo)
    protect = load_protect(root)
    sroot, session = scratch_dirs(args.scratchpad) if args.scratchpad else (None, None)
    targets, refused = [], []
    for raw in args.paths:
        path, problem = check_target(raw, root, protect, sroot, session)
        (refused if problem else targets).append((raw, path, problem))
    if refused:
        for raw, _, problem in refused:
            print('REFUSED: %s %s' % (raw, problem), file=sys.stderr)
        die('nothing was moved. Drop the refused paths and run again')
    sizes = {path: size_of(path) for _, path, _ in targets}
    err = os_trash([path for _, path, _ in targets])
    left = [path for _, path, _ in targets if os.path.lexists(path)]
    for _, path, _ in targets:
        print('%s %s\t%s' % ('kept ' if path in left else 'trashed', path, human(sizes[path])))
    if err or left:
        die((err or 'some paths are still there') + '. Nothing was deleted permanently')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command')
    s = sub.add_parser('scan')
    s.add_argument('repo')
    s.add_argument('--scratchpad')
    t = sub.add_parser('trash')
    t.add_argument('repo')
    t.add_argument('--scratchpad')
    t.add_argument('paths', nargs='+')
    args = p.parse_args()
    if args.command == 'scan':
        scan(args)
    elif args.command == 'trash':
        trash(args)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
