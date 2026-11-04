"""Check generated rule, router, guide, agent and skill docs. Never modifies files.

Usage: python3 -I check_docs.py <repo root> [--allow <identifier> ...]
  --allow: exclude identifiers that are intentionally absent from the repo (external tools, products, standards) from the evidence check.

Scope: CLAUDE.md · docs/rules/*.md · docs/guide/*.md · .claude/agents/*.md · .claude/skills/*/*.md
Checks:
  ERROR  broken relative links · secret-like values · unfilled template slots `{{…}}` · missing agent frontmatter
  WARN   inline-code identifiers (`…`) in rule docs with no evidence in the repo · over length · agents with write tools
         · broken links from the root README into docs/rules or docs/guide
  INFO   count of open markers: `needs confirmation`/`확인 필요`, `unverified`/`미확인`, TODO
Exits 1 if there is any ERROR. Check skill folders themselves with suggest-skills' check_skill.py.
"""
import re
import subprocess
import sys
from pathlib import Path

# The router is read every session, so keep it short (origin project CLAUDE.md was 21 lines; warning line with headroom)
CLAUDE_MD_WARN = 40
# A rule doc longer than this reads better split by area (origin project max was 111 lines)
RULE_DOC_WARN = 150
GENERATED_GLOBS = ['CLAUDE.md', 'docs/rules/*.md', 'docs/guide/*.md', '.claude/agents/*.md',
                   '.claude/skills/*/SKILL.md', '.claude/skills/*/*.md']
# Evidence check runs on the canonical rules only (skills and agents have many command examples, too noisy)
EVIDENCE_GLOBS = ['CLAUDE.md', 'docs/rules/*.md']
LINK = re.compile(r'\]\(([^)\s]+)\)')
FENCE = re.compile(r'```.*?```', re.S)
INLINE_CODE = re.compile(r'`([^`\n]+)`')
# Catch every slot within a line, no length cap
SLOT = re.compile(r'\{\{[^\n]*?\}\}')
OPEN_MARKS = re.compile(r'(?i:needs confirmation|unverified)|확인 필요|미확인|TODO|TBD')
SECRETS = [
    ('AWS access key', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('private key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('GitLab/GitHub token', re.compile(r'\b(glpat-[\w-]{20,}|gh[pousr]_[A-Za-z0-9]{30,})')),
    ('Slack token', re.compile(r'\bxox[abpr]-[\w-]{10,}')),
    ('credentials in URL', re.compile(r'://[^/\s:@]+:[^/\s@<>{}$]+@')),
    ('password value', re.compile(r'(?i)(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*["\']?(?![<${*]|\s|$|개별|별도|환경변수|미확인|provided|shared|separately|environment|unverified)[^\s"\'`|]{4,}')),
]
# Inline code treated as an identifier: paths, dotted names, underscores, camelCase, prefixes. Anything with spaces is a command and skipped
IDENT_LIKE = re.compile(r'^[@\w./:{}*-]+$')
IDENT_SIGNAL = re.compile(r'[./_]|[a-z][A-Z]|^[A-Z]{2,}[A-Z_]*_$')
# Generic names valid in any repo (excluded from the evidence check)
GENERIC = {
    'docs/rules', 'docs/rules/', 'docs/guide', 'docs/guide/', 'CLAUDE.md', 'CLAUDE.local.md', '.claude/',
    '.gitignore', 'README.md', 'git.md', 'common.md', 'environments.md', 'git add .', '--force', '--no-verify',
    '.claude/settings.json', '.claude/settings.local.json', '.devkit/', '.env', '.env.example', 'scratchpad',
}


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))


def collect(root, globs):
    seen = []
    for g in globs:
        for p in sorted(root.glob(g)):
            if p.is_file() and p not in seen:
                seen.append(p)
    return seen


def check_links(root, path, text, rep, level='ERROR', only_prefix=None):
    for target in LINK.findall(FENCE.sub('', text)):
        if re.match(r'^[a-z]+:', target) or target.startswith('#'):
            continue
        rel = target.split('#')[0]
        if only_prefix and not any(rel.startswith(p) for p in only_prefix):
            continue
        if rel and not (path.parent / rel).exists():
            rep.add(level, path.relative_to(root), f'broken link: {target}')


def check_secrets(root, path, text, rep):
    for name, pat in SECRETS:
        for m in pat.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            rep.add('ERROR', f'{path.relative_to(root)}:{line}', f'looks like a {name}; remove the value and write "provided separately"')


def check_agent(root, path, text, rep):
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m:
        rep.add('ERROR', path.relative_to(root), 'no frontmatter')
        return
    fm = m.group(1)
    for key in ('name', 'description', 'tools'):
        if not re.search(rf'^{key}:', fm, re.M):
            rep.add('ERROR', path.relative_to(root), f'frontmatter has no `{key}`')
    tools = re.search(r'^tools:\s*(.+)$', fm, re.M)
    if tools and re.search(r'\b(Edit|Write|NotebookEdit)\b', tools.group(1)):
        rep.add('WARN', path.relative_to(root), 'has write tools; remove them for a read-only agent')
    if not re.search(r'^model:', fm, re.M):
        rep.add('WARN', path.relative_to(root), 'no `model`; use sonnet for an exploration agent')


def evidence_checker(root):
    """Check whether an identifier appears in repo paths or content (rule docs excluded). None without git."""
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                            cwd=root, capture_output=True, text=True)
    if listed.returncode != 0:
        return None
    paths = listed.stdout
    cache = {}
    excludes = [':(exclude)CLAUDE.md', ':(exclude)docs/rules', ':(exclude)docs/guide', ':(exclude).claude']

    def has(token):
        if token in cache:
            return cache[token]
        probe = token.strip('/').split('{')[0].split('*')[0].rstrip('/.:') or token
        found = probe in paths or (root / probe).exists()
        if not found and len(probe) >= 3:
            found = subprocess.run(['git', 'grep', '-q', '-F', '--untracked', probe, '--', '.'] + excludes,
                                   cwd=root, capture_output=True).returncode == 0
        if not found:
            # Names like `User.name`, `value/onChange`, `_ID/_NO` count as evidenced when every part is found
            parts = [x.strip('*') for x in re.split(r'[/.]', probe) if len(x.strip('*')) >= 2]
            found = len(parts) >= 2 and all(has(x) for x in parts)
        cache[token] = found
        return found
    return has


def check_evidence(root, files, rep, allow):
    has = evidence_checker(root)
    if has is None:
        rep.add('WARN', '.', 'not a git repository; skipping the identifier evidence check')
        return
    for path in files:
        text = FENCE.sub('', path.read_text(encoding='utf-8', errors='replace'))
        missing = []
        for token in dict.fromkeys(INLINE_CODE.findall(text)):
            t = token.strip()
            if t in GENERIC or t in allow or not IDENT_LIKE.match(t) or not IDENT_SIGNAL.search(t):
                continue
            if t.startswith(('http', '--', '-', '/devkit:', 'devkit:', '@/')) or SLOT.search(t) or '...' in t or '…' in t:
                continue
            if not has(t):
                missing.append(t)
        if missing:
            rep.add('WARN', path.relative_to(root),
                    f'{len(missing)} identifiers with no evidence in the repo: {missing[:8]}; check for copies from another project or typos')


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    root = Path(argv[1]).expanduser().resolve()
    allow = set(argv[argv.index('--allow') + 1:]) if '--allow' in argv else set()
    rep = Report()
    files = collect(root, GENERATED_GLOBS)
    if not files:
        print(f'no docs to check: {root}; run after creating CLAUDE.md and docs/rules.')
        return 2
    open_count = 0
    for path in files:
        text = path.read_text(encoding='utf-8', errors='replace')
        rel = path.relative_to(root)
        lines = text.count('\n') + 1
        if path.name == 'CLAUDE.md' and path.parent == root and lines > CLAUDE_MD_WARN:
            rep.add('WARN', rel, f'{lines} lines; keep only tables and invocation cues in the router and move rules to docs/rules')
        if 'docs/rules' in str(rel) and lines > RULE_DOC_WARN:
            rep.add('WARN', rel, f'{lines} lines; split by area or move examples to a separate guide')
        check_links(root, path, text, rep)
        check_secrets(root, path, text, rep)
        if '.claude/agents' in str(rel):
            check_agent(root, path, text, rep)
        for m in SLOT.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            rep.add('ERROR', f'{rel}:{line}', f'unfilled slot {m.group(0)[:80]}')
        marks = OPEN_MARKS.findall(FENCE.sub('', text))
        if marks:
            open_count += len(marks)
            rep.add('INFO', rel, f'{len(marks)} open markers: {sorted(set(marks))}')
    readme = root / 'README.md'
    if readme.is_file():
        check_links(root, readme, readme.read_text(encoding='utf-8', errors='replace'), rep,
                    level='WARN', only_prefix=('docs/rules', 'docs/guide', './docs/rules', './docs/guide'))
    check_evidence(root, collect(root, EVIDENCE_GLOBS), rep, allow)
    for level in ('ERROR', 'WARN', 'INFO'):
        for lv, where, msg in rep.items:
            if lv == level:
                print(f'{lv:5} {where}: {msg}')
    errors = sum(1 for lv, _, _ in rep.items if lv == 'ERROR')
    warns = sum(1 for lv, _, _ in rep.items if lv == 'WARN')
    print(f'\n{len(files)} docs · ERROR {errors} · WARN {warns} · open markers {open_count}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
