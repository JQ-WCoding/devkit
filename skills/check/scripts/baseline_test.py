"""baseline.py tests against throwaway git repos. One test per invariant.
Usage: python3 -I skills/check/scripts/baseline_test.py
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'baseline.py')
PY = sys.executable
FAILS = []
# exits 0 when add() is right, 1 when it is wrong; prints the sum (-B: no stale .pyc when calc.py is rewritten within a second)
ADD = [PY, '-B', '-c', 'import sys; sys.path.insert(0, "."); import calc; print(calc.add(2, 2)); sys.exit(0 if calc.add(2, 2) == 4 else 1)']


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + str(out).replace('\n', '\n      ')[:1500])


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def git(r, *args):
    return subprocess.run(['git', '-C', r, '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                          capture_output=True, text=True, check=True).stdout


def repo(body='a + b'):
    """A repo with calc.py committed; body is add()'s return expression."""
    r = os.path.realpath(tempfile.mkdtemp(prefix='bl-'))
    git(r, 'init', '-q')
    write(os.path.join(r, 'calc.py'), f'def add(a, b):\n    return {body}\n')
    git(r, 'add', '.')
    git(r, 'commit', '-q', '-m', 'i')
    return r


def run(r, *args):
    p = subprocess.run([PY, '-I', SCRIPT, args[0], '--repo', r, *args[1:]], capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def state(r, task, rid):
    with open(os.path.join(r, '.devkit', 'work', task, 'baseline', f'{rid}.json'), encoding='utf-8') as f:
        return json.load(f)


def records(r, task):
    out = []
    for p in sorted(glob.glob(os.path.join(r, '.devkit', 'work', task, 'runs', '*-baseline*.json'))):
        with open(p, encoding='utf-8') as f:
            out.append(json.load(f))
    return out


def test_keep_same_after_unrelated_change():
    r = repo()
    code, out = run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    check('keep before: captured (ran twice, same output)', code == 0 and state(r, 'T', 'K1')['before']['result'] == 'captured', out)
    write(os.path.join(r, 'other.py'), 'x = 1\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1')
    check('keep after with the stored command: same', code == 0 and 'same' in out and state(r, 'T', 'K1')['after']['result'] == 'same', out)
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: keep met', code == 0 and '| K1 | keep | captured | same | met |' in out, out)


def test_keep_differs():
    r = repo()
    run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    write(os.path.join(r, 'calc.py'), 'def add(a, b):\n    return a * b + 1\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1')
    check('keep after a behavior change: differs, exit 1', code == 1 and 'differs' in out, out)
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: keep not met, exit 1', code == 1 and '| not met |' in out, out)


def test_unstable_and_ignore():
    r = repo()
    noisy = [PY, '-c', 'import uuid; print("id", uuid.uuid4()); print("rows 3")']
    code, out = run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *noisy)
    check('keep whose two runs differ: unstable', code == 0 and state(r, 'T', 'K1')['before']['result'] == 'unstable', out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1')
    check('unstable keep is not compared after', code == 0 and 'unstable' in out
          and state(r, 'T', 'K1')['after']['result'] == 'unstable', out)
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: unstable keep is not run', '| not run |' in out, out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'K2', '--kind', 'keep', '--ignore', r'[0-9a-f-]{36}', '--', *noisy)
    check('ignore rule makes it stable', code == 0 and state(r, 'T', 'K2')['before']['result'] == 'captured', out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K2')
    check('after reuses the stored ignore rule: same', code == 0 and 'same' in out, out)


def test_repro_red_then_green():
    r = repo('a - b')
    code, out = run(r, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--', *ADD)
    check('repro on pre-change code: red', code == 0 and state(r, 'T', 'R1')['before']['result'] == 'red', out)
    write(os.path.join(r, 'calc.py'), 'def add(a, b):\n    return a + b\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'R1')
    check('repro after the fix: green', code == 0 and state(r, 'T', 'R1')['after']['result'] == 'green', out)
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: repro met', code == 0 and '| R1 | repro | red | green | met |' in out, out)


def test_repro_green_before_stops():
    r = repo()
    code, out = run(r, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--', *ADD)
    check('repro green on pre-change code: exit 1, back to analyze', code == 1 and 'green' in out and 'analyze' in out, out)


def test_frozen_and_refusals():
    r = repo()
    run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    code, out = run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    check('a second before for the same id is refused (frozen)', code == 2 and 'K1' in out, out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1', '--', PY, '-c', 'print(4)')
    check('after with a different command is refused', code == 2 and 'command' in out, out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1', '--ignore', 'x')
    check('after does not take ignore rules', code == 2, out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K9')
    check('after without a before is refused', code == 2 and 'K9' in out, out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'K2', '--kind', 'accept', '--', *ADD)
    check('kinds are keep and repro only', code == 2, out)
    code, out = run(r, 'before', '--task', 'T', '--id', '../x', '--kind', 'keep', '--', *ADD)
    check('an id with a path separator is refused', code == 2, out)


def test_capture_after_edit_is_caught():
    r = repo()
    write(os.path.join(r, 'calc.py'), 'def add(a, b):\n    return b + a\n')
    write(os.path.join(r, 'new.py'), 'y = 2\n')
    run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    st = state(r, 'T', 'K1')
    check('before stamps HEAD and the modified and untracked paths',
          st['base'] == git(r, 'rev-parse', 'HEAD').strip() and st['pre_change'] == ['calc.py', 'new.py'], st)
    run(r, 'after', '--task', 'T', '--id', 'K1')
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: keep captured after editing is not met and names the paths',
          code == 1 and '| not met |' in out and 'calc.py' in out and 'new.py' in out, out)


def test_repro_path():
    r = repo('a - b')
    write(os.path.join(r, 'test_add.py'), 'import calc\nassert calc.add(2, 2) == 4\n')
    write(os.path.join(r, 'stray.py'), 'z = 3\n')
    t = [PY, '-B', '-c', 'import sys; sys.path.insert(0, "."); import test_add']
    code, out = run(r, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--repro-path', './test_add.py', '--', *t)
    check('before names an undeclared path changed at capture', code == 0 and 'stray.py' in out, out)
    run(r, 'before', '--task', 'T', '--id', 'R2', '--kind', 'repro', '--repro-path', 'test_add.py',
        '--repro-path', os.path.join(r, 'stray.py'), '--', *t)
    write(os.path.join(r, 'calc.py'), 'def add(a, b):\n    return a + b\n')
    run(r, 'after', '--task', 'T', '--id', 'R1')
    run(r, 'after', '--task', 'T', '--id', 'R2')
    code, out = run(r, 'verify', '--task', 'T')
    check('verify: repro with an undeclared path changed at capture is not met',
          code == 1 and '| R1 | repro | red | green | not met |' in out and 'stray.py' in out, out)
    check('verify: repro whose changed paths are all declared (relative or absolute) is met',
          '| R2 | repro | red | green | met |' in out, out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--repro-path', 'test_add.py', '--', *ADD)
    check('--repro-path is refused on a keep row', code == 2 and 'repro' in out and 'usage' not in out, out)


def test_from_file():
    r = repo()
    out_file = os.path.join(tempfile.mkdtemp(), 'resp.txt')
    write(out_file, '{"total": 4, "at": "2026-01-01T00:00:00"}\n')
    code, out = run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--ignore', r'"at": "[^"]*"', '--from-file', out_file)
    check('keep from a saved output: captured', code == 0 and state(r, 'T', 'K1')['before']['result'] == 'captured', out)
    write(out_file, '{"total": 4, "at": "2026-02-02T09:09:09"}\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1', '--from-file', out_file)
    check('keep from file after, ignored field changed: same', code == 0 and 'same' in out, out)
    code, out = run(r, 'after', '--task', 'T', '--id', 'K1')
    check('a file row needs --from-file after', code == 2, out)
    write(out_file, 'error: total 0\n')
    code, out = run(r, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--from-file', out_file)
    check('repro from a file without --match is refused', code == 2 and '--match' in out and 'usage' not in out, out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'K2', '--kind', 'keep', '--match', 'x', '--from-file', out_file)
    check('--match is refused outside a file-based repro', code == 2 and '--match' in out and 'usage' not in out, out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--match', 'total 0', '--from-file', out_file)
    check('repro from file: red when the pattern is present', code == 0 and state(r, 'T', 'R1')['before']['result'] == 'red', out)
    code, out = run(r, 'before', '--task', 'T', '--id', 'R2', '--kind', 'repro', '--match', 'total 9', '--from-file', out_file)
    check('repro from file: pattern absent before is green, exit 1, back to analyze', code == 1 and 'analyze' in out, out)
    write(out_file, 'error: total 0 (retried)\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'R1', '--from-file', out_file)
    check('repro from file: red when the pattern is still present, though the output changed',
          code == 1 and state(r, 'T', 'R1')['after']['result'] == 'red', out)
    write(out_file, 'total 4\n')
    code, out = run(r, 'after', '--task', 'T', '--id', 'R1', '--from-file', out_file)
    check('repro from file: green when the pattern is absent', code == 0 and state(r, 'T', 'R1')['after']['result'] == 'green', out)


def test_repro_path_from_subfolder():
    r = repo('a - b')
    sub = os.path.join(r, 'pkg')
    write(os.path.join(sub, 'test_add.py'), 'x = 1\n')
    write(os.path.join(r, 'top.py'), 'y = 2\n')
    t = [PY, '-B', '-c', 'import sys; sys.path.insert(0, ".."); import calc; sys.exit(0 if calc.add(2, 2) == 4 else 1)']
    run(sub, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--repro-path', 'test_add.py', '--', *t)
    check('subfolder --repo: paths from the repo top, untracked files outside the folder included',
          state(r, 'T', 'R1')['pre_change'] == ['pkg/test_add.py', 'top.py'] and state(r, 'T', 'R1')['repro_paths'] == ['pkg/test_add.py'],
          state(r, 'T', 'R1'))


def test_records_keep_hashes_not_output():
    r = repo()
    secret = [PY, '-c', 'print("token=abc123secret")']
    run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *secret)
    run(r, 'after', '--task', 'T', '--id', 'K1')
    recs = records(r, 'T')
    text = json.dumps(recs)
    check('records: kind baseline, phases before/after, base, pre_change and fingerprint, no output text',
          sorted(x['phase'] for x in recs) == ['after', 'before'] and all(x['kind'] == 'baseline' and x['schema'] == 'devkit.run/1'
                                                                   and {'base', 'pre_change', 'fingerprint'} <= set(x) for x in recs)
          and 'abc123secret' not in text, text)
    check('.devkit/ stays out of Git', subprocess.run(['git', '-C', r, 'check-ignore', '-q', '.devkit/x']).returncode == 0)


def test_verify_is_read_only():
    r = repo()
    run(r, 'before', '--task', 'T', '--id', 'K1', '--kind', 'keep', '--', *ADD)

    def snap():
        files = sorted(glob.glob(os.path.join(r, '.devkit', '**'), recursive=True))
        return [(f, os.path.getmtime(f)) for f in files], git(r, 'status', '--porcelain', '--untracked-files=all')
    s1 = snap()
    code, out = run(r, 'verify', '--task', 'T')
    check('verify writes nothing; a row without after is not run', snap() == s1 and '| not run |' in out, out)
    code, out = run(r, 'verify', '--task', 'NONE')
    check('verify with no rows says so, exit 0', code == 0 and 'no baseline rows' in out, out)


def test_worktree_and_no_task():
    r = repo('a - b')
    wt = os.path.join(tempfile.mkdtemp(), 'wt')
    git(r, 'worktree', 'add', '-q', '-b', 'fix', wt)
    write(os.path.join(wt, 'scratch.py'), 'z = 3\n')
    code, out = run(wt, 'before', '--task', 'T', '--id', 'R1', '--kind', 'repro', '--', *ADD)
    st = state(r, 'T', 'R1')
    check('worktree: state in the main repo, command and paths from the worktree',
          code == 0 and st['before']['result'] == 'red' and st['pre_change'] == ['scratch.py'], (out, st))
    code, out = run(r, 'before', '--id', 'K1', '--kind', 'keep', '--', *ADD)
    check('no task: state under .devkit/baseline/', code == 0 and os.path.exists(os.path.join(r, '.devkit', 'baseline', 'K1.json')), out)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
    print('\n' + ('all passed' if not FAILS else f'{len(FAILS)} failed'))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
