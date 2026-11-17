"""collect_commits.py shared-path proposal tests against a throwaway git repo.
Usage: python3 -I skills/peer-review/scripts/collect_commits_test.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'collect_commits.py')
PY = sys.executable
FAILS = []


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + out.replace('\n', '\n      ')[:1500])


def sh(*cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)


def commit(repo, author, path, msg):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'a') as f:
        f.write(msg + '\n')
    sh('git', 'add', path, cwd=repo)
    sh('git', '-c', f'user.name={author}', '-c', 'user.email=a@example.com', 'commit', '-q', '-m', msg, cwd=repo)


def repo_with(config):
    repo = tempfile.mkdtemp(prefix='pr-')
    sh('git', 'init', '-q', '-b', 'main', cwd=repo)
    commit(repo, 'Alice', 'shared/export.py', 'feat: add export')
    commit(repo, 'Bob', 'shared/export.py', 'fix: change export')
    commit(repo, 'Bob', 'web/page.js', 'feat: add page')
    sh('git', 'update-ref', 'refs/remotes/origin/main', 'HEAD', cwd=repo)
    if config is not None:
        os.makedirs(os.path.join(repo, '.devkit', 'peer-review'))
        with open(os.path.join(repo, '.devkit', 'peer-review', 'config.json'), 'w') as f:
            json.dump(config, f)
    return repo


def run(repo):
    r = sh(PY, '-I', SCRIPT, '--no-fetch', '--days', '30', '--self', 'Reviewer', cwd=repo)
    return r.returncode, r.stdout + r.stderr


def test_shared_path_by_non_steward_is_a_proposal():
    repo = repo_with({'branch': 'main', 'shared_paths': [{'prefix': 'shared/', 'steward': 'Alice', 'message': 'export is server-side'}]})
    code, out = run(repo)
    bob = out.split('## Bob', 1)[-1].split('## ', 1)[0]
    alice = out.split('## Alice', 1)[-1].split('## ', 1)[0]
    check("Bob's commit on shared/ is a proposal naming the steward",
          code == 0 and "🔶 proposal: touches shared `shared/`; needs Alice's approval (export is server-side)" in bob, out)
    check("Bob's commit outside shared/ and the steward's own commit are not proposals",
          bob.count('🔶') == 1 and '🔶' not in alice, out)


def test_steward_list():
    repo = repo_with({'branch': 'main', 'shared_paths': [{'prefix': 'shared/', 'steward': ['Alice', 'Bob']}]})
    code, out = run(repo)
    check('any listed steward may change the shared path', code == 0 and '🔶' not in out, out)


def test_no_shared_paths_no_change():
    repo = repo_with({'branch': 'main'})
    code, out = run(repo)
    check('without shared_paths nothing is tagged', code == 0 and '🔶' not in out and '## Bob' in out, out)


def test_missing_config_keys_stop_with_a_message():
    for cfg, field in (({'branch': 'main', 'shared_paths': [{'prefix': 'shared/'}]}, '`shared_paths[0]` needs steward'),
                       ({'branch': 'main', 'forbidden_paths': [{'prefix': 'tmp/'}]}, '`forbidden_paths[0]` needs message'),
                       ({'branch': 'main', 'subject': {'forbidden_endings': [{'message': 'x'}]}},
                        '`subject.forbidden_endings[0]` needs ending')):
        code, out = run(repo_with(cfg))
        check(f'missing key stops with a message: {field}', code != 0 and field in out and 'Traceback' not in out, out)


if __name__ == '__main__':
    for fn in [v for k, v in sorted(globals().items()) if k.startswith('test_')]:
        fn()
    print(f'\n{"FAILED: " + ", ".join(FAILS) if FAILS else "all passed"}')
    sys.exit(1 if FAILS else 0)
