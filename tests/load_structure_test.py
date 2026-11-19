"""Skill load-structure test: structure checks (fail) + always-loaded / per-skill word measurement (report only).

Usage: python3 -I tests/load_structure_test.py [root]
  no root: self-tests on temp fixtures, then the checks and the measurement on this repo.
  root:    only the structure checks on <root>/skills (exit 1 on a violation).

Checks for every skills/<name>/ (no word limits anywhere):
  a. No orphan: every .md under references/ (recursively) is reachable by markdown links from SKILL.md,
     directly or through linked .md files of the same skill.
  b. Load condition, in one sentence: every reference file is linked at least once (from SKILL.md or a linked
     reference) by a table row with another non-empty cell, or by a sentence or list item that says when — a
     condition word (if, when, unless, only, before, after, without, step) or `→`, an enclosing list item that
     does, or a numbered step (an ordered item or a numbered heading); other mentions may be plain prose.
  c. Broken links: every relative link in SKILL.md and references/**/*.md resolves to an existing file, and a
     `#anchor` on a .md target must match one of its headings (GitHub slug). Links inside fenced code blocks
     and inline code spans are templates, not links, and are skipped; so are URLs with a scheme.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PY = sys.executable

LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
FENCE = re.compile(r'^\s*(```|~~~)')
CODE_SPAN = re.compile(r'`[^`]*`')
LIST_ITEM = re.compile(r'^\s*([-*+]|\d+[.)])\s')
CONDITION = re.compile(r'\b(if|when|unless|only|before|after|without|step)\b|→', re.I)
ORDERED = re.compile(r'^\s*\d+[.)]\s')
STEP_HEADING = re.compile(r'^#{1,6}\s+\d')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def prose_lines(text):
    """(line number, line) outside fenced code blocks, with inline code spans blanked."""
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield n, CODE_SPAN.sub('``', line)


def links(path):
    """(line number, line, target) for each relative link in a markdown file."""
    for n, line in prose_lines(read(path)):
        for m in LINK.finditer(line):
            target = m.group(1)
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                yield n, line, target


def slug(heading):
    s = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return s.replace(' ', '-')


def anchors(path):
    return {slug(line.lstrip('#')) for _, line in prose_lines(read(path)) if re.match(r'^#{1,6}\s', line)}


def resolve(src, target):
    file_part, _, anchor = target.partition('#')
    dest = os.path.normpath(os.path.join(os.path.dirname(src), file_part)) if file_part else src
    return dest, anchor


def says_when(text):
    return bool(CONDITION.search(LINK.sub('', text)))


def context_conditioned(lines, n):
    """For a list item at line n: an ordered item, an enclosing list item that says when or is ordered,
    or a numbered heading above it."""
    line = lines[n]
    if ORDERED.match(line):
        return True
    indent = len(line) - len(line.lstrip())
    for k in range(n - 1, 0, -1):
        prev = lines.get(k, '')
        if STEP_HEADING.match(prev):
            return True
        if prev.startswith('#'):
            return False
        if LIST_ITEM.match(prev):
            pi = len(prev) - len(prev.lstrip())
            if pi < indent:
                if ORDERED.match(prev) or says_when(prev):
                    return True
                indent = pi
    return False


def conditioned(line, target, lines=None, n=None):
    """True for a table row with another non-empty cell, or a sentence or list item that says when (see b)."""
    if line.strip().startswith('|'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        return any(c and '](' + target + ')' not in c and not re.fullmatch(r':?-+:?', c) for c in cells)
    sentence = next((s for s in re.split(r'(?<=[.!?])\s+', line) if '](' + target + ')' in s), line)
    if says_when(sentence):
        return True
    return bool(lines and LIST_ITEM.match(line) and context_conditioned(lines, n))


def check_skill(skill_dir):
    """Violation messages for one skill folder."""
    errors = []
    rel = lambda p: os.path.relpath(p, os.path.dirname(os.path.dirname(skill_dir)))
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    ref_dir = os.path.join(skill_dir, 'references')
    refs = sorted(os.path.join(d, f) for d, _, fs in os.walk(ref_dir) for f in fs if f.endswith('.md'))

    # c. broken links in SKILL.md and every reference file
    for src in [skill_md] + refs:
        for n, _, target in links(src):
            dest, anchor = resolve(src, target)
            if not os.path.exists(dest):
                errors.append(f'broken link: {rel(src)}:{n} -> {target}')
            elif anchor and dest.endswith('.md') and anchor not in anchors(dest):
                errors.append(f'broken anchor: {rel(src)}:{n} -> {target}')

    # a. reachability from SKILL.md through .md files of this skill
    seen, todo = set(), [skill_md]
    while todo:
        src = todo.pop()
        if src in seen or not os.path.isfile(src):
            continue
        seen.add(src)
        for _, _, target in links(src):
            dest, _ = resolve(src, target)
            if dest.endswith('.md') and dest.startswith(skill_dir + os.sep):
                todo.append(dest)
    errors += [f'orphan reference: {rel(r)} is not reachable from SKILL.md' for r in refs if r not in seen]

    # b. load condition for each reference file, from SKILL.md or another reference of this skill
    introduced = {}
    for src in [skill_md] + refs:
        lines = dict(prose_lines(read(src)))
        for n, line, target in links(src):
            dest, _ = resolve(src, target)
            if dest in refs and dest != src:
                introduced.setdefault(dest, []).append((f'{rel(src)}:{n}', conditioned(line, target, lines, n)))
    for dest, uses in introduced.items():
        if not any(ok for _, ok in uses):
            where = ', '.join(w for w, _ in uses)
            errors.append(f'no load condition: {where} -> {os.path.relpath(dest, skill_dir)} '
                          '(link it from a table row with a When cell, or a sentence or list item that says when)')
    return errors


def check_root(root):
    skills = os.path.join(root, 'skills')
    errors = []
    for name in sorted(os.listdir(skills)):
        d = os.path.join(skills, name)
        if os.path.isfile(os.path.join(d, 'SKILL.md')):
            errors += check_skill(d)
    return errors


# ---------- measurement (report only) ----------

def words(text):
    return len(text.split())


def description(path):
    m = re.match(r'---\n(.*?)\n---', read(path), re.S)
    d = re.search(r'^description:\s*(.*)$', m.group(1), re.M) if m else None
    return d.group(1).strip().strip('"\'') if d else ''


def measure(root):
    out = subprocess.run([PY, '-I', os.path.join(root, 'hooks', 'session_start.py')], input='{}',
                         capture_output=True, text=True, timeout=30).stdout
    try:
        hook = json.loads(out)['hookSpecificOutput']['additionalContext']
    except (ValueError, KeyError, TypeError):
        hook = out
    skills = os.path.join(root, 'skills')
    names = sorted(n for n in os.listdir(skills) if os.path.isfile(os.path.join(skills, n, 'SKILL.md')))
    agents_dir = os.path.join(root, 'agents')
    agents = sorted(f for f in os.listdir(agents_dir) if f.endswith('.md')) if os.path.isdir(agents_dir) else []
    skill_desc = sum(words(description(os.path.join(skills, n, 'SKILL.md'))) for n in names)
    agent_desc = sum(words(description(os.path.join(agents_dir, a))) for a in agents)

    print('\nAlways loaded (words)')
    print(f'  session_start hook context   {words(hook):6}')
    print(f'  skill descriptions ({len(names):2})      {skill_desc:6}')
    print(f'  agent descriptions ({len(agents):2})      {agent_desc:6}')
    print(f'  total                        {words(hook) + skill_desc + agent_desc:6}')
    print('\nPer skill (words): SKILL.md loads on use; every reference loads on demand (rule b), so ref words is the most it can add')
    print(f'  {"skill":18} {"SKILL.md":>8} {"refs":>5} {"ref words":>9}')
    for n in names:
        d = os.path.join(skills, n)
        refs = [os.path.join(p, f) for p, _, fs in os.walk(os.path.join(d, 'references')) for f in fs if f.endswith('.md')]
        print(f'  {n:18} {words(read(os.path.join(d, "SKILL.md"))):8} {len(refs):5} {sum(words(read(r)) for r in refs):9}')


# ---------- self-tests ----------

FAILS = []


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + out.replace('\n', '\n      ')[:1500])


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data)


GOOD_SKILL = """---
name: demo
description: Demo skill.
---
# Demo

| File | When |
|---|---|
| [guide.md](references/guide.md) | Step 1 |

1. Read [notes.md](references/notes.md) when the input is a draft.

Later prose may mention [guide.md](references/guide.md#usage) again.

```markdown
Template: [Rules](docs/rules/{{file}}.md) and `[file](link)` are not links.
```
"""


def fixture(skill_md=GOOD_SKILL, refs=None):
    root = tempfile.mkdtemp(prefix='load-')
    d = os.path.join(root, 'skills', 'demo')
    write(os.path.join(d, 'SKILL.md'), skill_md)
    for name, text in (refs if refs is not None else {
        'guide.md': '# Guide\n\n## Usage\n\nSee [notes](notes.md).\n',
        'notes.md': '# Notes\n',
    }).items():
        write(os.path.join(d, 'references', name), text)
    return root


def run(root):
    r = subprocess.run([PY, '-I', os.path.abspath(__file__), root], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def test_good_skill_passes():
    code, out = run(fixture())
    check('good skill: exit 0', code == 0, out)


def test_orphan_reference_fails():
    code, out = run(fixture(refs={'guide.md': '# Guide\n\n## Usage\n', 'notes.md': '# Notes\n',
                                  'lost.md': '# Nobody links here\n'}))
    check('orphan reference: exit 1 naming lost.md', code == 1 and 'orphan reference' in out and 'lost.md' in out, out)


def test_unconditional_link_fails():
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            'Read [notes.md](references/notes.md).')
    code, out = run(fixture(md))
    check('prose-only link: exit 1 naming notes.md', code == 1 and 'no load condition' in out and 'notes.md' in out, out)
    md = GOOD_SKILL.replace('| [guide.md](references/guide.md) | Step 1 |', '| [guide.md](references/guide.md) | |')
    code, out = run(fixture(md))
    check('table row with an empty When cell: exit 1', code == 1 and 'no load condition' in out and 'guide.md' in out, out)


def test_list_item_needs_context():
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            '## References\n\n- [notes.md](references/notes.md)')
    code, out = run(fixture(md))
    check('bare list item under a plain heading: exit 1', code == 1 and 'no load condition' in out and 'notes.md' in out, out)
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            '- Input is a draft → plan it:\n  - Read [notes.md](references/notes.md).')
    code, out = run(fixture(md))
    check('list item under a parent that says when: exit 0', code == 0, out)
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            '## 2. Plan\n\n- Read [notes.md](references/notes.md).')
    code, out = run(fixture(md))
    check('list item inside a numbered step heading: exit 0', code == 0, out)


def test_nested_reference_needs_condition():
    refs = {'guide.md': '# Guide\n\n## Usage\n\nBackground: [notes](notes.md).\n', 'notes.md': '# Notes\n'}
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.\n', '')
    code, out = run(fixture(md, refs))
    check('reference linked only from another reference in plain prose: exit 1',
          code == 1 and 'no load condition' in out and 'notes.md' in out, out)


def test_conditional_sentence_passes():
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            'Intro text. If the input is a draft, read [notes.md](references/notes.md).')
    code, out = run(fixture(md))
    check('prose sentence with a condition word: exit 0', code == 0, out)
    md = GOOD_SKILL.replace('1. Read [notes.md](references/notes.md) when the input is a draft.',
                            'Read this only once. Background is in [notes.md](references/notes.md).')
    code, out = run(fixture(md))
    check('condition word in a different sentence: exit 1', code == 1 and 'no load condition' in out, out)


def test_broken_link_fails():
    code, out = run(fixture(refs={'guide.md': '# Guide\n\n## Usage\n\n[gone](missing.md)\n', 'notes.md': '# Notes\n'}))
    check('missing link target: exit 1', code == 1 and 'broken link' in out and 'missing.md' in out, out)
    code, out = run(fixture(refs={'guide.md': '# Guide\n', 'notes.md': '# Notes\n'}))
    check('missing #anchor heading: exit 1', code == 1 and 'broken anchor' in out and '#usage' in out, out)


def test_analyze_split_layout_passes():
    """Core files with index tables linking per-language / per-area files, as the analyze split will do."""
    md = """---
name: demo
description: Demo.
---
| File | When |
|---|---|
| [design-principles.md](references/design-principles.md) | Step 4 design principles |
| [risk-checklist.md](references/risk-checklist.md) | Step 4 risk check |
"""
    refs = {
        'design-principles.md': '# Design principles\n\n| Language | File |\n|---|---|\n'
                                '| Java | [java.md](design-principles/java.md) |\n'
                                '| Python | [python.md](design-principles/python.md) |\n',
        'design-principles/java.md': '# Java\n\nBack to [core](../design-principles.md).\n',
        'design-principles/python.md': '# Python\n',
        'risk-checklist.md': '# Risk checklist\n\n| Area | Signals | File |\n|---|---|---|\n'
                             '| DB | SQL, mapper | [db.md](risk-checklist/db.md) |\n'
                             '| Screen | grid, popup | [screen.md](risk-checklist/screen.md) |\n',
        'risk-checklist/db.md': '# DB\n',
        'risk-checklist/screen.md': '# Screen\n',
    }
    code, out = run(fixture(md, refs))
    check('analyze split layout (core + per-language/per-area index tables): exit 0', code == 0, out)
    refs['risk-checklist/batch.md'] = '# Batch, not in the index table\n'
    code, out = run(fixture(md, refs))
    check('analyze split layout with an unindexed area file: exit 1', code == 1 and 'risk-checklist/batch.md' in out, out)


def self_tests():
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()


def main():
    if len(sys.argv) > 1:
        errors = check_root(sys.argv[1])
        print('\n'.join(errors) if errors else 'load structure ok')
        sys.exit(1 if errors else 0)
    self_tests()
    errors = check_root(REPO)
    for e in errors:
        print('FAIL  ' + e)
    check(f'repo skills: no orphan, unconditioned or broken reference links ({len(errors)} violations)', not errors)
    measure(REPO)
    if FAILS:
        print(f'\n{len(FAILS)} failed')
        sys.exit(1)
    print('\nall load structure tests passed')


if __name__ == '__main__':
    main()
