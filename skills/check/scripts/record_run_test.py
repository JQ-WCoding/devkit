"""record_run.py characterization tests against throwaway git repos: current line forms, record keys, refusals.
Usage: python3 -I skills/check/scripts/record_run_test.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'record_run.py')
PY = sys.executable
FAILS = []
KEYS = {'schema', 'task', 'kind', 'verdict', 'summary', 'repo', 'instance', 'branch', 'commit', 'dirty',
        'started_at', 'finished_at', 'items', 'log'}


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + str(out).replace('\n', '\n      ')[:1500])


def repo():
    r = tempfile.mkdtemp(prefix='rr-')
    subprocess.run(['git', '-C', r, 'init', '-q'], check=True)
    subprocess.run(['git', '-C', r, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'i'],
                   check=True)
    return r


def run(r, *args, stdin=None):
    p = subprocess.run([PY, '-I', SCRIPT, '--repo', r, *args], capture_output=True, text=True, input=stdin, timeout=60)
    rec = None
    if p.returncode == 0:
        with open(p.stdout.strip(), encoding='utf-8') as f:
            rec = json.load(f)
    return p.returncode, p.stdout, p.stderr, rec


def test_line_forms():
    r = repo()
    for line, kind, verdict, summary in [
            ('CHECKS: PASS', 'checks', 'PASS', ''), ('CHECKS: PASS (2 not run)', 'checks', 'PARTIAL', '2 not run'),
            ('CHECKS: FAIL (3 commands)', 'checks', 'FAIL', '3 commands'), ('CHECKS: FAIL (none run)', 'checks', 'FAIL', 'none run'),
            ('VERDICT: PASS', 'verifier', 'PASS', ''), ('VERDICT: PASS (1 not run)', 'verifier', 'PARTIAL', '1 not run'),
            ('VERDICT: FAIL (2 items)', 'verifier', 'FAIL', '2 items'), ('VERDICT: PASS (2 items)', 'verifier', 'PASS', '2 items')]:
        code, _, err, rec = run(r, '--task', 'T-1', '--line', line)
        check(f'{line!r} -> {kind} {verdict}', code == 0 and rec and rec['kind'] == kind and rec['verdict'] == verdict
              and rec['summary'] == summary and f'verdict: {verdict}' in err and set(rec) == KEYS, (code, err, rec))


def test_refused_lines():
    r = repo()
    for line in ('CHECKS: PASS (2 items)', 'CHECKS: PASS (oops)', 'garbage'):
        code, out, err, _ = run(r, '--line', line)
        check(f'{line!r} refused with exit 2 and nothing written', code == 2 and not out and 'record_run:' in err, err)


def test_record_location_and_keys():
    r = repo()
    code, out, err, rec = run(r, '--task', 'T-1', '--line', 'CHECKS: PASS')
    path = out.strip()
    check('task record under .devkit/work/<task>/runs/, schema devkit.run/1, .devkit/ excluded',
          code == 0 and os.path.dirname(path) == os.path.join(os.path.realpath(r), '.devkit', 'work', 'T-1', 'runs')
          and rec['schema'] == 'devkit.run/1' and rec['dirty'] is False
          and subprocess.run(['git', '-C', r, 'check-ignore', '-q', '.devkit/x']).returncode == 0, (out, err))
    code, out, _, _ = run(r, '--line', 'CHECKS: PASS')
    check('no task: record under .devkit/runs/', code == 0 and os.path.basename(os.path.dirname(out.strip())) == 'runs'
          and os.path.basename(os.path.dirname(os.path.dirname(out.strip()))) == '.devkit', out)


def test_kind_verdict_items():
    r = repo()
    code, _, err, rec = run(r, '--kind', 'db', '--verdict', 'PARTIAL', '--summary', 's', '--items', '-',
                            stdin='[{"name": "a", "result": "ok", "detail": "d"}]')
    check('--kind db with items', code == 0 and rec['kind'] == 'db' and rec['items'][0]['detail'] == 'd'
          and set(rec) == KEYS and 'verdict: PARTIAL' in err, (code, err, rec))
    code, _, err, _ = run(r, '--kind', 'db', '--verdict', 'PASS', '--items', '-', stdin='[{"name": "a", "result": "ok", "env": 1}]')
    check('an item key outside name/result/detail is refused', code == 2 and "['env']" in err, err)
    code, _, err, _ = run(r, '--kind', 'db')
    check('--kind without --verdict is refused', code == 2, err)
    code, _, err, _ = run(r, '--task', '../x', '--line', 'CHECKS: PASS')
    check('a task id with a path separator is refused', code == 2 and 'task id' in err, err)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
    print('\n' + ('all passed' if not FAILS else f'{len(FAILS)} failed'))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
