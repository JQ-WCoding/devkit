"""Write one machine-readable run record (a check, verifier, runtime or DB verdict) as JSON.

Usage:
  python3 -I record_run.py --repo <repo> [--task <id>] --line "CHECKS: PASS (2 not run)" [--summary <text>]
  python3 -I record_run.py --repo <repo> [--task <id>] --kind db --verdict FAIL --summary <text> [--items <json file|->]
Prints the path of the written file. Records go to <main repo>/.devkit/work/<task>/runs/ (or .devkit/runs/ without a
task); --work-dir overrides the work folder when the repo rules name another one.
Items are a JSON list of {"name", "result", "detail"?}; other keys are refused so environment values and secrets
cannot slip into a record.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

SCHEMA = 'devkit.run/1'
KINDS = ('checks', 'verifier', 'runtime', 'db')
VERDICTS = ('PASS', 'FAIL', 'PARTIAL')
ITEM_KEYS = {'name', 'result', 'detail'}
# last-line contracts of the check-runner and verifier agents
LINE = re.compile(r'^\s*(CHECKS|VERDICT):\s*(PASS|FAIL)\b\s*(\((.*)\))?\s*$')
TASK_ID = re.compile(r'^[\w.#-]{1,80}$')  # issue keys (ABC-123, #45) and dated slugs; no path separators


def git(repo, *args):
    try:
        out = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    return out.stdout.strip() if out.returncode == 0 else ''


def main_root(repo):
    """The main checkout of a repo or one of its worktrees (records of every instance live in one place)."""
    common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if common and os.path.basename(common) == '.git':
        return os.path.dirname(common)
    return git(repo, 'rev-parse', '--show-toplevel') or os.path.abspath(repo)


def instance_name(repo):
    top = git(repo, 'rev-parse', '--show-toplevel') or os.path.abspath(repo)
    return 'main' if os.path.realpath(top) == os.path.realpath(main_root(repo)) else os.path.basename(top)


def ensure_excluded(root):
    """Keep .devkit/ out of Git; returns a note when it had to add the exclude line."""
    if subprocess.run(['git', '-C', root, 'check-ignore', '-q', '.devkit/x'], capture_output=True).returncode == 0:
        return ''
    exclude = git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude')
    if not exclude:
        return ''
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with open(exclude, 'a', encoding='utf-8') as f:
        f.write('\n.devkit/\n')
    return f'added .devkit/ to {exclude}'


def parse_line(line):
    """'CHECKS: PASS (2 not run)' -> ('checks', 'PARTIAL', '2 not run')."""
    m = LINE.match(line or '')
    if not m:
        raise ValueError(f'not a CHECKS:/VERDICT: line: {line!r}. Accepted: "CHECKS: PASS", "CHECKS: PASS (<k> not run)", '
                         '"CHECKS: FAIL (<n> commands)", "CHECKS: FAIL (none run)", "VERDICT: PASS", "VERDICT: FAIL (<n> items)"')
    kind = 'checks' if m.group(1) == 'CHECKS' else 'verifier'
    detail = m.group(4) or ''
    verdict = m.group(2)
    if verdict == 'PASS' and 'not run' in detail:
        verdict = 'PARTIAL'
    elif kind == 'checks' and verdict == 'PASS' and detail:
        raise ValueError(f'{line!r}: a CHECKS: PASS detail must be "<k> not run"')
    return kind, verdict, detail


def check_items(items):
    if not isinstance(items, list):
        raise ValueError('items must be a JSON list')
    for i, it in enumerate(items):
        if not isinstance(it, dict) or not {'name', 'result'} <= set(it):
            raise ValueError(f'item {i} needs "name" and "result"')
        extra = set(it) - ITEM_KEYS
        if extra:
            raise ValueError(f'item {i} has keys {sorted(extra)}; allowed: {sorted(ITEM_KEYS)}')
    return items


def write_record(repo, kind, verdict, summary, task=None, items=None, log=None, started_at=None, work_dir=None):
    if kind not in KINDS:
        raise ValueError(f'kind must be one of {KINDS}')
    if verdict not in VERDICTS:
        raise ValueError(f'verdict must be one of {VERDICTS}')
    if task and not TASK_ID.match(task):
        raise ValueError(f'task id {task!r} must be letters, digits, ".", "_", "-" or "#"')
    root = main_root(repo)
    note = ensure_excluded(root)
    base = work_dir or os.path.join(root, '.devkit', 'work')
    folder = os.path.join(base, task, 'runs') if task else os.path.join(root, '.devkit', 'runs')
    os.makedirs(folder, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    record = {
        'schema': SCHEMA, 'task': task, 'kind': kind, 'verdict': verdict, 'summary': summary or '',
        'repo': root, 'instance': instance_name(repo),
        'branch': git(repo, 'branch', '--show-current'), 'commit': git(repo, 'rev-parse', '--short', 'HEAD'),
        'dirty': bool(git(repo, 'status', '--porcelain', '--untracked-files=no')),
        'started_at': started_at, 'finished_at': now.isoformat(timespec='seconds'),
        'items': check_items(items or []), 'log': log,
    }
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    path = os.path.join(folder, f'{stamp}-{kind}.json')
    n = 1
    while os.path.exists(path):  # two records in the same second
        n += 1
        path = os.path.join(folder, f'{stamp}-{kind}-{n}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return path, note


def main(argv=None):
    p = argparse.ArgumentParser(description='Write a devkit run record')
    p.add_argument('--repo', required=True)
    p.add_argument('--task')
    p.add_argument('--line', help='the last line of check-runner or verifier')
    p.add_argument('--kind', choices=KINDS)
    p.add_argument('--verdict', choices=VERDICTS)
    p.add_argument('--summary', default='')
    p.add_argument('--items', help='JSON file with the item list, or - for stdin')
    p.add_argument('--log')
    p.add_argument('--work-dir')
    a = p.parse_args(argv)
    try:
        if a.line:
            kind, verdict, detail = parse_line(a.line)
            summary = a.summary or detail
        elif a.kind and a.verdict:
            kind, verdict, summary = a.kind, a.verdict, a.summary
        else:
            raise ValueError('pass --line, or both --kind and --verdict')
        items = []
        if a.items:
            text = sys.stdin.read() if a.items == '-' else open(a.items, encoding='utf-8').read()
            items = json.loads(text)
        path, note = write_record(a.repo, kind, verdict, summary, a.task, items, a.log, work_dir=a.work_dir)
    except (ValueError, OSError) as e:
        print(f'record_run: {e}', file=sys.stderr)
        return 2
    if note:
        print(f'note: {note}', file=sys.stderr)
    print(path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
