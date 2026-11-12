"""Create a worker worktree: <repo>/.worktrees/<slug> on branch <type>/<slug>, cut from <base branch>.

Usage: python3 -I make_worktree.py <slug> [feat|fix] [base branch | -] [extra paths to link ...]
  Empty or '-' base branch = the main repo's current branch.
  Extra paths are relative to the repo root (local-only files or folders that git doesn't track).
Run from the main repo root (the original checkout). Python 3.8+, any git with `worktree`.
On failure prints `ERROR: <reason and next action>` and exits 1.
"""
import os
import re
import shutil
import subprocess
import sys

# The same slug names the branch, the folder and the worker; 32 chars matches Herdr terminal names.
SLUG = re.compile(r'[a-z0-9][a-z0-9-]{0,31}')
# Local files workers need, linked when present and untracked. CLAUDE.md and CLAUDE.local.md are not here:
# Claude Code loads them from every parent folder, and the worktree sits inside the repo, so a link would
# load them twice.
DEFAULT_LINKS = ('.env',)
# .claude: in a worktree Claude Code reads settings.local.json from the main checkout, and falls back to the
# main checkout's skills when the worktree has no .claude/skills (checked below).
# .git and .worktrees must never be linked into a worktree.
NEVER_LINK = ('.claude', '.git', '.worktrees')
EXCLUDE_LINE = '/.worktrees/'


def die(msg):
    print('ERROR: ' + msg, file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print('WARN: ' + msg, file=sys.stderr)


def git(args, cwd, ok_codes=(0,)):
    try:
        r = subprocess.run(['git'] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           encoding='utf-8', errors='replace')
    except FileNotFoundError:
        die('git not found. Install Git and make sure `git` is on PATH')
    if r.returncode not in ok_codes:
        die('git %s failed: %s' % (' '.join(args), r.stderr.strip() or r.stdout.strip()))
    return r


def same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def link_or_copy(src, dst):
    """Symlink src to dst. Where symlinks are not allowed (Windows without Developer Mode), copy instead."""
    try:
        os.symlink(src, dst, target_is_directory=os.path.isdir(src))
        return 'linked'
    except (OSError, NotImplementedError):
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)
        return 'copied'


def main(argv):
    if not argv or not argv[0]:
        die('missing slug. Usage: make_worktree.py <slug> [feat|fix] [base branch] [paths to link ...]')
    slug = argv[0]
    kind = argv[1] if len(argv) > 1 else 'feat'
    base = argv[2] if len(argv) > 2 else '-'
    extra = argv[3:]

    if not SLUG.fullmatch(slug):
        die("slug must be 1-32 lowercase letters, digits or hyphens, starting with a letter or digit: '%s'" % slug)
    if kind not in ('feat', 'fix'):
        die("type must be feat or fix: '%s'" % kind)

    top = git(['rev-parse', '--show-toplevel'], os.getcwd(), ok_codes=(0, 128))
    if top.returncode != 0:
        die('not inside a git repository. Run from the repo root')
    root = os.path.realpath(top.stdout.strip())
    common = git(['rev-parse', '--git-common-dir'], root).stdout.strip()
    common = os.path.realpath(os.path.join(root, common))
    if not same_path(common, os.path.join(root, '.git')):
        die('this is a linked worktree. Run from the main repo (the parent of %s)' % common)

    current = git(['symbolic-ref', '--quiet', '--short', 'HEAD'], root, ok_codes=(0, 1)).stdout.strip()
    if base in ('', '-'):
        if not current:
            die('main repo is on a detached HEAD. Pass the base branch as the third argument')
        base = current

    branch = '%s/%s' % (kind, slug)
    wt = os.path.join(root, '.worktrees', slug)

    if git(['rev-parse', '--verify', '--quiet', 'refs/heads/' + base], root, ok_codes=(0, 1)).returncode != 0:
        die("no local base branch '%s'. If it exists only on the remote, ask the user, then: git branch %s origin/%s"
            % (base, base, base))
    if os.path.lexists(wt):
        die('%s already exists. To continue that work, launch the worker in that folder' % wt)
    if git(['rev-parse', '--verify', '--quiet', 'refs/heads/' + branch], root, ok_codes=(0, 1)).returncode == 0:
        die('branch %s already exists. To reuse it (after user approval): git worktree add .worktrees/%s %s'
            % (branch, slug, branch))

    # Exclude .worktrees/ on this machine only (.git/info/exclude is never committed and is shared by
    # all worktrees). Leave .gitignore alone.
    exclude = os.path.join(common, 'info', 'exclude')
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    text = ''
    if os.path.exists(exclude):
        with open(exclude, encoding='utf-8', errors='replace') as f:
            text = f.read()
    if EXCLUDE_LINE not in text.splitlines():
        with open(exclude, 'a', encoding='utf-8') as f:
            f.write(('' if not text or text.endswith('\n') else '\n') + EXCLUDE_LINE + '\n')

    if current == base and git(['status', '--porcelain', '--untracked-files=no'], root).stdout.strip():
        warn('main repo has uncommitted changes. The worktree only gets the committed state of %s.' % base)

    git(['worktree', 'add', '-q', '-b', branch, wt, base], root)

    # Link local-only files git doesn't track. By default only the rules and env files workers read.
    # Other paths (local docs, test data, ...) are chosen by the central session and passed as extra args.
    linked, copied, skipped = [], [], []
    for rel in list(DEFAULT_LINKS) + extra:
        rel = rel.replace('\\', '/').rstrip('/')
        parts = rel.split('/')
        if not rel or os.path.isabs(rel) or '..' in parts:
            skipped.append('%s (must be a path inside the repo)' % rel)
            continue
        if parts[0] in NEVER_LINK:
            skipped.append('%s (never linked)' % rel)
            continue
        src, dst = os.path.join(root, *parts), os.path.join(wt, *parts)
        if not os.path.exists(src):
            if rel not in DEFAULT_LINKS:
                skipped.append('%s (not found)' % rel)
            continue
        if os.path.lexists(dst):
            continue  # tracked by git, so already in the worktree
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        (linked if link_or_copy(src, dst) == 'linked' else copied).append(rel)

    # Links not covered by ignore rules show up as ??. They must be left out of commits
    # (adding them to exclude would also hide them in the main repo, so the script doesn't).
    untracked = git(['status', '--porcelain'], wt).stdout.rstrip()
    if untracked:
        warn('worktree shows changes that must not be committed:\n' + untracked)
    # When .claude/skills or .claude/agents is tracked, the worktree has its own copy and the main checkout's
    # untracked skills and agents are not found there.
    for kind in ('skills', 'agents'):
        main_dir, wt_dir = os.path.join(root, '.claude', kind), os.path.join(wt, '.claude', kind)
        if os.path.isdir(main_dir) and os.path.isdir(wt_dir):
            missing = sorted(set(os.listdir(main_dir)) - set(os.listdir(wt_dir)) - {'.DS_Store'})
            if missing:
                warn('local .claude/%s not in the worktree, so workers started there may not see them: %s'
                     % (kind, ' '.join(missing)))
    if copied:
        warn('symlinks not allowed here, so these were copied: %s. Edits to the copies do not reach the main repo'
             % ' '.join(copied))
    if skipped:
        warn('could not link: ' + ', '.join(skipped))

    sha = git(['rev-parse', '--short', base], root).stdout.strip()
    print('worktree: ' + wt)
    print('branch:   %s (base %s @ %s)' % (branch, base, sha))
    print('linked:   ' + (' '.join(linked) or '(none)'))


if __name__ == '__main__':
    main(sys.argv[1:])
