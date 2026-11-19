"""Freeze behavior on pre-change code and compare it after the change (keep rows), or show a bug fails before
the fix and passes after (repro rows).

Usage:
  python3 -I baseline.py before --repo R [--task T] --id K1 --kind keep|repro [--ignore REGEX ...] [--repro-path FILE ...]
                                (-- <command> | --from-file OUT [--match REGEX])
  python3 -I baseline.py after  --repo R [--task T] --id K1 [-- <command> | --from-file OUT]
  python3 -I baseline.py verify --repo R [--task T]      # read-only

before: run before the first edit. Stamps HEAD and the paths already modified or untracked; keep runs twice
(different output -> unstable, not compared); repro must fail (red) or it exits 1: the cause is wrong.
after: reuses the stored command and ignore rules (a different command is refused); keep -> same | differs,
repro -> green | red. A --from-file row compares the saved output instead; a file-based repro needs --match:
red while the pattern is present, green once it is absent.
verify: one table row per id; a row captured after its own paths were already edited is not met, except the
repro test files declared with --repro-path.
Outputs stay in the work folder (<main repo>/.devkit/work/<task>/baseline/, else .devkit/baseline/); run
records (kind baseline) keep only hashes. Catches drift and self-fitting, not a deliberate workaround such as
stashing edits before capture.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script folder from sys.path
import record_run  # noqa: E402

ID = re.compile(r'^[\w.#-]{1,40}$')
VERDICT = {'captured': 'PASS', 'unstable': 'PARTIAL', 'same': 'PASS', 'differs': 'FAIL'}


class Refused(Exception):
    pass


def folder(repo, task, work_dir):
    root = record_run.main_root(repo)
    if task:
        return os.path.join(work_dir or os.path.join(root, '.devkit', 'work'), task, 'baseline')
    return os.path.join(root, '.devkit', 'baseline')


def changed_paths(repo, base=None):
    """Tracked paths changed against base (else HEAD) plus untracked paths, relative to the repo top."""
    diff = record_run.git(repo, 'diff', '--name-only', base or 'HEAD')
    untracked = record_run.git(repo, 'ls-files', '--others', '--exclude-standard', '--full-name', ':/')
    return sorted({p for p in (diff + '\n' + untracked).splitlines() if p})


def capture(repo, command, from_file, timeout):
    """(text, exit code or None)."""
    if from_file:
        with open(from_file, encoding='utf-8', errors='replace') as f:
            return f.read(), None
    try:
        p = subprocess.run(command, cwd=repo, capture_output=True, text=True, errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Refused(f'command timed out after {timeout}s')
    except OSError as e:
        raise Refused(f'command not runnable: {e}')
    return p.stdout + p.stderr, p.returncode


def top_relative(repo, path):
    top = os.path.realpath(record_run.git(repo, 'rev-parse', '--show-toplevel'))
    return os.path.relpath(os.path.realpath(os.path.join(repo, path)), top).replace(os.sep, '/')


def fingerprint(text, code, ignore):
    for rx in ignore:
        text = re.sub(rx, '<ignored>', text)
    return hashlib.sha256(f'exit {code}\n{text}'.encode('utf-8')).hexdigest()


def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')


def record(a, st, phase, result, fp):
    verdict = VERDICT.get(result) or ('PASS' if (result == 'red') == (phase == 'before') else 'FAIL')
    path, _ = record_run.write_record(
        a.repo, 'baseline', verdict, f'{st["id"]} {st["kind"]} {phase}: {result}', a.task,
        [{'name': st['id'], 'result': result, 'detail': st['kind']}], work_dir=a.work_dir,
        extra={'phase': phase, 'base': st['base'], 'pre_change': st['pre_change'], 'fingerprint': fp})
    return path, verdict


def before(a, command):
    d = folder(a.repo, a.task, a.work_dir)
    state_path = os.path.join(d, f'{a.id}.json')
    if os.path.exists(state_path):
        raise Refused(f'{a.id} already has a before capture (frozen): {state_path}')
    for rx in a.ignore + ([a.match] if a.match else []):
        re.compile(rx)
    if a.repro_path and a.kind != 'repro':
        raise Refused('--repro-path is for repro rows only')
    if (a.kind == 'repro' and bool(a.from_file)) != bool(a.match):
        raise Refused('--match is required for a --from-file repro and allowed only there')
    record_run.ensure_excluded(record_run.main_root(a.repo))
    base = record_run.git(a.repo, 'rev-parse', 'HEAD')
    if not base:
        raise Refused('not runnable: no commit to stamp (git rev-parse HEAD failed)')
    pre = changed_paths(a.repo)
    declared = sorted({top_relative(a.repo, p) for p in a.repro_path})
    text, code = capture(a.repo, command, a.from_file, a.timeout)
    fp = fingerprint(text, code, a.ignore)
    if a.kind == 'keep':
        result = 'captured'
        if not a.from_file:
            text2, code2 = capture(a.repo, command, None, a.timeout)
            if fingerprint(text2, code2, a.ignore) != fp:
                result = 'unstable'
    else:
        result = 'red' if (re.search(a.match, text) if a.match else code != 0) else 'green'
    os.makedirs(d, exist_ok=True)
    save(os.path.join(d, f'{a.id}.before.out'), text)
    st = {'id': a.id, 'kind': a.kind, 'command': None if a.from_file else command, 'ignore': a.ignore,
          'match': a.match, 'repro_paths': declared, 'base': base, 'pre_change': pre,
          'before': {'result': result, 'exit': code, 'fingerprint': fp}}
    save(state_path, st)
    path, verdict = record(a, st, 'before', result, fp)
    msg = f'{a.id} {a.kind} before: {result}'
    if a.kind == 'repro' and result == 'green':
        msg += ' — passes on pre-change code, so the cause is wrong: go back to devkit:analyze'
    elif result == 'unstable':
        msg += ' — the two runs differ: add --ignore rules under a new id, or this row is not compared'
    print(msg)
    undeclared = sorted(set(pre) - set(declared))
    if undeclared:
        print('already changed at capture (verify will mark this row not met): ' + ', '.join(undeclared))
    print(path)
    return 1 if verdict == 'FAIL' else 0


def after(a, command):
    state_path = os.path.join(folder(a.repo, a.task, a.work_dir), f'{a.id}.json')
    if not os.path.exists(state_path):
        raise Refused(f'{a.id} has no before capture: {state_path}')
    with open(state_path, encoding='utf-8') as f:
        st = json.load(f)
    stored = st['command']
    if stored is None and not a.from_file:
        raise Refused(f'{a.id} was captured from a file; pass --from-file')
    if stored is not None and (a.from_file or (command and command != stored)):
        raise Refused(f'{a.id}: after must reuse the stored command {stored}')
    text, code = capture(a.repo, stored, a.from_file, a.timeout)
    fp = fingerprint(text, code, st['ignore'])
    b = st['before']
    if st['kind'] == 'keep':
        result = 'unstable' if b['result'] == 'unstable' else ('same' if fp == b['fingerprint'] else 'differs')
    elif st.get('match'):
        result = 'red' if re.search(st['match'], text) else 'green'
    else:
        result = 'green' if code == 0 else 'red'
    d = os.path.dirname(state_path)
    save(os.path.join(d, f'{a.id}.after.out'), text)
    st['after'] = {'result': result, 'exit': code, 'fingerprint': fp}
    save(state_path, st)
    path, verdict = record(a, st, 'after', result, fp)
    print(f'{a.id} {st["kind"]} after: {result}')
    print(path)
    return 1 if verdict == 'FAIL' else 0


def verify(a):
    d = folder(a.repo, a.task, a.work_dir)
    rows = sorted(p for p in (os.listdir(d) if os.path.isdir(d) else []) if p.endswith('.json'))
    if not rows:
        print(f'no baseline rows in {d}')
        return 0
    print('| ID | Kind | Before | After | Status | Note |\n|---|---|---|---|---|---|')
    counts = {'met': 0, 'not met': 0, 'not run': 0}
    for name in rows:
        with open(os.path.join(d, name), encoding='utf-8') as f:
            st = json.load(f)
        b, af = st['before']['result'], (st.get('after') or {}).get('result', '-')
        notes = []
        base_ok = subprocess.run(['git', '-C', a.repo, 'merge-base', '--is-ancestor', st['base'], 'HEAD'],
                                 capture_output=True).returncode == 0
        if st['kind'] == 'keep':
            edited = sorted(set(st['pre_change']) & set(changed_paths(a.repo, st['base']))) if base_ok else []
        else:
            edited = sorted(set(st['pre_change']) - set(st.get('repro_paths') or []))
        if not base_ok:
            status = 'not met'
            notes.append(f'base {st["base"][:10]} is not in the current history')
        elif b == 'unstable' or af == '-':
            status = 'not run'
        elif st['kind'] == 'keep':
            status = 'met' if af == 'same' and not edited else 'not met'
        else:
            status = 'met' if b == 'red' and af == 'green' and not edited else 'not met'
        if edited:
            notes.append(('captured after editing: ' if st['kind'] == 'keep' else
                          'changed at capture, not declared with --repro-path: ') + ', '.join(edited))
        notes.append(f'base {st["base"][:10]}')
        counts[status] += 1
        print(f'| {st["id"]} | {st["kind"]} | {b} | {af} | {status} | {"; ".join(notes)} |')
    print(f'baseline: {counts["met"]} met, {counts["not met"]} not met, {counts["not run"]} not run')
    return 1 if counts['not met'] else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if '--' in argv:
        i = argv.index('--')
        argv, command = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(description='Freeze behavior before a change and compare it after')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('before', 'after', 'verify'):
        s = sub.add_parser(name)
        s.add_argument('--repo', required=True)
        s.add_argument('--task')
        s.add_argument('--work-dir')
        if name == 'verify':
            continue
        s.add_argument('--id', required=True)
        s.add_argument('--from-file')
        s.add_argument('--timeout', type=int, default=600)
        if name == 'before':
            s.add_argument('--kind', required=True, choices=('keep', 'repro'))
            s.add_argument('--ignore', action='append', default=[], help='regex replaced before comparing')
            s.add_argument('--repro-path', action='append', default=[], help='repro test file written before capture')
            s.add_argument('--match', help='file-based repro: regex present while the bug is')
    a = p.parse_args(argv)
    try:
        if a.task and not record_run.TASK_ID.match(a.task):
            raise Refused(f'task id {a.task!r} must be letters, digits, ".", "_", "-" or "#"')
        if a.cmd == 'verify':
            if command:
                raise Refused('verify takes no command')
            return verify(a)
        if not ID.match(a.id):
            raise Refused(f'id {a.id!r} must be letters, digits, ".", "_", "-" or "#"')
        if a.cmd == 'before':
            if bool(command) == bool(a.from_file):
                raise Refused('pass either -- <command> or --from-file')
            return before(a, command)
        return after(a, command)
    except (Refused, ValueError, OSError, re.error) as e:
        print(f'baseline: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
