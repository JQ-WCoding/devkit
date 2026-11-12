"""Check that skill folders follow the authoring principles. Never modifies files.

Usage: python3 -I check_skill.py <skill folder> [<skill folder> ...]
Exits 1 if there is any ERROR.
"""
import json
import re
import sys
from pathlib import Path

# Official frontmatter limits
NAME_MAX = 64
DESC_MAX = 1024
RESERVED = ('claude', 'anthropic')
# Official guidance: SKILL.md body under 500 lines
BODY_MAX_LINES = 500
# Official guidance: reference files over 100 lines start with a table of contents
TOC_REQUIRED_LINES = 100
# The contents must be visible from a partial read, so it has to sit within this many lines of the top
TOC_SEARCH_LINES = 15
# Official guidance: at least 3 evaluation scenarios
EVALS_MIN = 3
# Shorter than this usually means the "when to use" part is missing (rule of thumb, warning only)
DESC_SHORT = 100
# Threshold to catch run outputs or backups piling up in a skill folder
LARGE_FILE_BYTES = 1024 * 1024
SKIP_DIRS = {'node_modules', '.git', '__pycache__'}
ARCHIVE_SUFFIXES = ('.tgz', '.tar.gz', '.zip', '.dmp', '.tar')
# Korean and English phrases that go stale over time
STALE_WORDS = re.compile(r'아직|곧 |최근에|이번 주|이번 달|올해|처음 실행할 때|\b(soon|recently|this week|this month|this year|for now)\b', re.I)
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|「[^」]*」')
FIRST_PERSON = re.compile(r'\b(I can|I will|You can)\b|저는 |제가 ')
LINK = re.compile(r'\]\(([^)\s]+)\)')
XML_TAG = re.compile(r'<[A-Za-z/][^>]*>')
# Official naming guidance lists these as vague or overly generic. Flag only when EVERY hyphen
# segment is one of them (`utils`, `data-files`), never a single segment (`data-migration` is fine).
VAGUE_NAME_WORDS = {
    'helper', 'helpers', 'util', 'utils', 'utility', 'utilities', 'tool', 'tools',
    'document', 'documents', 'doc', 'docs', 'data', 'file', 'files',
    'misc', 'common', 'general', 'stuff', 'my',
}
# Official guidance: name files by content (`form_validation_rules.md`, not `doc2.md` or `file1.md`).
# First group: vague even alone. Second group: vague only with a number (`doc2`, `reference2`); alone
# they can name a domain (`docs.md` beside `sheets.md` for Google Docs) or a kind of content
# (`reference.md`, `examples.md`). Pure numbers (`01.md`) are vague too.
VAGUE_FILE_STEM = re.compile(
    r'(file|notes?|misc|untitled|temp|tmp|stuff|new|draft|other)\d*'
    r'|(docs?|document|part|page|section|reference|example|template|guide)\d+|\d+', re.I)
# Claude Code calls MCP tools `mcp__<server>__<tool>`; a bare name can resolve to nothing. Only the
# unambiguous shapes are flagged, because a server name in the same spot is not a mistake:
# - "MCP tool `x`" (singular, name after): `x` is the tool.
# - "`x_y` MCP tool" (singular, snake_case before): server names are rarely snake_case.
# Skipped: "`x` MCP", "`x` MCP server", "`x` MCP tools" and kebab/one-word names before "MCP tool",
# where `x` is usually the server (e.g. a `github` MCP tool).
MCP_BARE_TOOL = re.compile(r'\bMCP\s+tool\s+`([a-z][a-z0-9_-]*)`|`([a-z][a-z0-9-]*_[a-z0-9_-]*)`\s+MCP\s+tool\b(?!s)')


class Report:
    def __init__(self, root):
        self.root = root
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))

    @property
    def errors(self):
        return sum(1 for level, _, _ in self.items if level == 'ERROR')


def walk(root):
    for path in sorted(root.rglob('*')):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def parse_frontmatter(text):
    """Minimal YAML parser: top-level keys and `>-` / `|` multi-line values only."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return None, text
    try:
        end = lines.index('---', 1)
    except ValueError:
        return None, text
    meta, key = {}, None
    for line in lines[1:end]:
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            meta[key] = '' if value in ('>-', '>', '|', '|-') else value.strip('"\'')
        elif key and line.startswith((' ', '\t')):
            meta[key] = (meta[key] + ' ' + line.strip()).strip()
    return meta, '\n'.join(lines[end + 1:])


def prose_lines(text, keep_code=False):
    """Yield (line number, text) for lines outside code fences, with inline code removed unless keep_code."""
    inside = False
    for no, line in enumerate(text.split('\n'), 1):
        if line.lstrip().startswith('```'):
            inside = not inside
            continue
        if not inside:
            yield no, line if keep_code else re.sub(r'`[^`]*`', '', line)


def check_frontmatter(rep, skill_md, meta):
    if meta is None:
        rep.add('ERROR', skill_md, 'no frontmatter (--- ... ---)')
        return {}
    name = meta.get('name', '')
    if not name:
        rep.add('ERROR', skill_md, 'missing name')
    else:
        if len(name) > NAME_MAX or not re.fullmatch(r'[a-z0-9-]+', name):
            rep.add('ERROR', skill_md, f'name "{name}": use only lowercase letters, digits and hyphens, at most {NAME_MAX} chars')
        if any(word in name.lower() for word in RESERVED):
            rep.add('ERROR', skill_md, f'name "{name}" contains a reserved word (claude, anthropic)')
        if name != rep.root.name:
            rep.add('WARN', skill_md, f'name "{name}" differs from folder name "{rep.root.name}"')
        if all(part in VAGUE_NAME_WORDS for part in name.lower().split('-') if part):
            rep.add('WARN', skill_md, f'name "{name}" is vague; name the action and its object (e.g. process-pdfs)')
    desc = meta.get('description', '')
    if not desc:
        rep.add('ERROR', skill_md, 'description is empty')
    else:
        if len(desc) > DESC_MAX:
            rep.add('ERROR', skill_md, f'description is {len(desc)} chars; shorten to at most {DESC_MAX}')
        if XML_TAG.search(desc):
            rep.add('ERROR', skill_md, 'description contains an XML tag')
        if FIRST_PERSON.search(desc):
            rep.add('WARN', skill_md, 'description is in first or second person; write it in third person')
        if len(desc) < DESC_SHORT and meta.get('disable-model-invocation') != 'true':
            rep.add('WARN', skill_md, f'description is {len(desc)} chars; check that it says when to use it (request phrases)')
    return meta


def check_links(rep, path, text):
    """Check that relative links point to existing files; return the targets."""
    targets = set()
    for no, line in prose_lines(text):
        for link in LINK.findall(line):
            if re.match(r'^[a-z]+:', link) or link.startswith('#'):
                continue
            target = (path.parent / link.split('#')[0]).resolve()
            if not target.exists():
                rep.add('ERROR', f'{path}:{no}', f'link target missing: {link}')
            else:
                targets.add(target)
    return targets


def check_skill(root):
    rep = Report(root)
    skill_md = root / 'SKILL.md'
    if not skill_md.is_file():
        rep.add('ERROR', root, 'no SKILL.md')
        return rep
    text = skill_md.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(text)
    meta = check_frontmatter(rep, skill_md, meta)
    body_lines = body.count('\n')
    if body_lines >= BODY_MAX_LINES:
        rep.add('ERROR', skill_md, f'body is {body_lines} lines; split it to under {BODY_MAX_LINES}')

    direct = check_links(rep, skill_md, text)
    for path in walk(root):
        rel = path.relative_to(root)
        size = path.stat().st_size
        if size > LARGE_FILE_BYTES or path.name.endswith(ARCHIVE_SUFFIXES):
            rep.add('WARN', rel, f'large or archive file ({size // 1024}KB); move run outputs or backups out of the skill folder')
        if path.suffix != '.md' or path == skill_md:
            continue
        if VAGUE_FILE_STEM.fullmatch(path.stem):
            rep.add('WARN', rel, 'file name does not say what it holds; name it by content (e.g. form_validation_rules.md)')
        md = path.read_text(encoding='utf-8')
        check_links(rep, path, md)
        covered = path.resolve() in direct or any(t.is_dir() and t in path.resolve().parents for t in direct)
        if not covered and rel.parts[0] != 'evals':
            rep.add('WARN', rel, 'not linked directly from SKILL.md (keep references one level deep)')
        lines = md.split('\n')
        if len(lines) > TOC_REQUIRED_LINES:
            head = '\n'.join(lines[:TOC_SEARCH_LINES])
            if not re.search(r'^(목차|## 목차|Contents|## Contents|Table of contents)', head, re.M):
                rep.add('WARN', rel, f'{len(lines)} lines but no table of contents in the first {TOC_SEARCH_LINES} lines')

    for path in [skill_md] + [p for p in walk(root) if p.suffix == '.md' and p != skill_md]:
        content = path.read_text(encoding='utf-8')
        # Docs with a date near the top are dated, so time-relative phrases are fine there
        dated_doc = DATE.search('\n'.join(content.split('\n')[:5]))
        for no, line in prose_lines(content):
            if re.search(r'[A-Za-z0-9_]\\+[A-Za-z0-9_]+\.[a-z]{1,4}\b', line):
                rep.add('WARN', f'{path.relative_to(root)}:{no}', 'backslash path; use `/`')
            unquoted = QUOTED.sub('', line)
            if not dated_doc and not DATE.search(line) and STALE_WORDS.search(unquoted):
                rep.add('WARN', f'{path.relative_to(root)}:{no}', f'phrase that may go stale: {line.strip()[:60]}')
        for no, line in prose_lines(content, keep_code=True):
            for m in MCP_BARE_TOOL.finditer(line):
                tool = m.group(1) or m.group(2)
                if tool.startswith('mcp__'):
                    continue
                rep.add('WARN', f'{path.relative_to(root)}:{no}', f'MCP tool `{tool}` without server; write the full name mcp__<server>__{tool}')

    evals = root / 'evals' / 'evals.json'
    auto = meta.get('disable-model-invocation') != 'true'
    if evals.is_file():
        try:
            cases = json.loads(evals.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            rep.add('ERROR', 'evals/evals.json', f'JSON error: {e}')
        else:
            if not isinstance(cases, list) or not all(isinstance(c, dict) and c.get('query') and c.get('expected_behavior') for c in cases):
                rep.add('ERROR', 'evals/evals.json', 'every item needs query and expected_behavior')
            elif len(cases) < EVALS_MIN:
                rep.add('WARN', 'evals/evals.json', f'{len(cases)} scenarios; at least {EVALS_MIN} recommended')
    elif auto:
        rep.add('WARN', root, f'no evals/evals.json (at least {EVALS_MIN} scenarios recommended)')
    return rep


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    total_errors = 0
    for arg in argv:
        root = Path(arg).expanduser().resolve()
        if not root.is_dir():
            print(f'== {arg}\n  ERROR  ' + ('path does not exist' if not Path(arg).exists() else 'not a folder'))
            total_errors += 1
            continue
        rep = check_skill(root)
        print(f'== {root}')
        if not rep.items:
            print('  OK')
        for level, where, msg in rep.items:
            print(f'  {level:5}  {where}: {msg}')
        total_errors += rep.errors
    return 1 if total_errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
