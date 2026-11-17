"""runtime.py and record_run.py tests against throwaway git repos and python http.server services.
Usage: python3 -I skills/run-app/scripts/runtime_test.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(HERE, 'runtime.py')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'check', 'scripts'))
import record_run  # noqa: E402

PY = sys.executable
FAILS = []


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def sh(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)


def harness(repo, *args):
    r = sh(PY, '-I', RUNTIME, '--repo', repo, *args)
    return r.returncode, r.stdout + r.stderr


def new_repo(config):
    repo = tempfile.mkdtemp(prefix='rt-')
    sh('git', 'init', '-q', '-b', 'main', repo)
    sh('git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'init')
    if config is not None:
        os.makedirs(os.path.join(repo, '.devkit'))
        with open(os.path.join(repo, '.devkit', 'runtime.json'), 'w') as f:
            json.dump(config, f)
    return repo


def http_service(name, port, depends=None, timeout=20):
    s = {'name': name, 'port': port, 'cmd': [PY, '-m', 'http.server', '{port}', '--bind', '127.0.0.1'],
         'health': 'http://127.0.0.1:{port}/', 'timeout': timeout}
    if depends:
        s['depends'] = depends
    return s


def check(name, cond, out=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + out.replace('\n', '\n      ')[:1500])


def records(repo, task=None):
    folder = os.path.join(repo, '.devkit', 'work', task, 'runs') if task else os.path.join(repo, '.devkit', 'runs')
    return [json.load(open(os.path.join(folder, n))) for n in sorted(os.listdir(folder))] if os.path.isdir(folder) else []


def test_no_config():
    repo = new_repo(None)
    code, out = harness(repo, 'up')
    check('no config: refuses with exit 2', code == 2 and 'has not opted in' in out and 'RUNTIME: FAIL' in out, out)


def test_bad_config():
    repo = new_repo({'services': [{'name': 'a', 'port': 1, 'cmd': 'python -m http.server'}]})
    code, out = harness(repo, 'up')
    check('bad config: cmd must be a list', code == 2 and 'cmd must be a non-empty list' in out, out)
    repo = new_repo({'services': [{'name': 'a', 'port': 1, 'cmd': ['x'], 'depends': ['b']}]})
    code, out = harness(repo, 'up')
    check('bad config: depends must name an earlier service', code == 2 and 'depends' in out, out)


def test_preflight_fail():
    closed = free_port()
    repo = new_repo({'preflight': [{'name': 'db-tunnel', 'tcp': f'127.0.0.1:{closed}', 'hint': 'open the tunnel'}],
                     'services': [http_service('api', free_port())]})
    code, out = harness(repo, 'up', '--task', 'T-1')
    recs = records(repo, 'T-1')
    check('preflight closed port: FAIL, nothing started, hint shown',
          code == 1 and 'open the tunnel' in out and 'starting' not in out and 'RUNTIME: FAIL' in out, out)
    check('preflight failure is recorded', len(recs) == 1 and recs[0]['verdict'] == 'FAIL'
          and recs[0]['kind'] == 'runtime', json.dumps(recs))


def test_up_status_down():
    api, web = free_port(), free_port()
    repo = new_repo({'services': [http_service('api', api), http_service('web', web, depends=['api'])]})
    code, out = harness(repo, 'up', 'web', '--task', 'T-2')
    check('up web also starts its dependency api', code == 0 and 'starting api' in out and 'starting web' in out
          and out.strip().endswith('RUNTIME: PASS'), out)
    recs = records(repo, 'T-2')
    check('up writes a PASS runtime record with one item per service',
          len(recs) == 1 and recs[0]['verdict'] == 'PASS' and [i['name'] for i in recs[0]['items']] == ['api', 'web']
          and recs[0]['instance'] == 'main' and recs[0]['schema'] == 'devkit.run/1', json.dumps(recs))
    code, out = harness(repo, 'status', '--json')
    st = json.loads(out) if code == 0 else {}
    check('status reports both services healthy', [s['healthy'] for s in st.get('services', [])] == [True, True], out)
    code, out = harness(repo, 'up')
    check('second up reuses running services', code == 0 and out.count('already running') == 2, out)
    code, out = harness(repo, 'down')
    check('down stops both and frees the ports', code == 0 and 'stopped 2' in out
          and not record_run_port_open(api) and not record_run_port_open(web), out)
    check('down removes the state file', not os.path.exists(os.path.join(repo, '.devkit', 'runtime', 'main', 'state.json')))
    code, out = harness(repo, 'down')
    check('down with nothing running is a no-op', code == 0 and 'nothing to stop' in out, out)


def record_run_port_open(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def test_port_taken():
    port = free_port()
    blocker = socket.socket()
    blocker.bind(('127.0.0.1', port))
    blocker.listen()
    try:
        repo = new_repo({'services': [http_service('api', port)]})
        code, out = harness(repo, 'up')
        check('port already in use: FAIL without starting (IDE run stays untouched)',
              code == 1 and 'already in use' in out and 'starting' not in out, out)
    finally:
        blocker.close()


def test_env_file_and_java_home():
    port = free_port()
    probe = os.path.join(tempfile.mkdtemp(), 'env.txt')
    repo = new_repo(None)
    with open(os.path.join(repo, 'local.env'), 'w') as f:
        f.write('# comment\nexport SECRET_TOKEN="s3cr3t"\nPLAIN=1\n')
    svc = {'name': 'api', 'port': port, 'timeout': 20, 'env_file': 'local.env', 'java_home': '/opt/jdk-x',
           'cmd': [PY, '-c', 'import os,sys,http.server as h;open(sys.argv[1],"w").write(os.environ["SECRET_TOKEN"]+"|"'
                   '+os.environ["JAVA_HOME"]+"|"+os.environ["PATH"].split(os.pathsep)[0]);'
                   'h.test(h.SimpleHTTPRequestHandler, port=int(sys.argv[2]), bind="127.0.0.1")', probe, '{port}'],
           'health': 'http://127.0.0.1:{port}/'}
    os.makedirs(os.path.join(repo, '.devkit'))
    json.dump({'services': [svc]}, open(os.path.join(repo, '.devkit', 'runtime.json'), 'w'))
    code, out = harness(repo, 'up', '--task', 'T-4')
    seen = open(probe).read() if os.path.exists(probe) else ''
    rec = json.dumps(records(repo, 'T-4'))
    check('env_file and java_home reach the child', code == 0 and seen == 's3cr3t|/opt/jdk-x|/opt/jdk-x/bin', out + seen)
    check('env_file values stay out of output and records', 's3cr3t' not in out and 's3cr3t' not in rec, out + rec)
    harness(repo, 'down')


def test_launch_error_cleans_up():
    api = free_port()
    repo = new_repo({'services': [http_service('api', api),
                                  {'name': 'web', 'port': free_port(), 'depends': ['api'], 'cmd': ['no-such-binary-xyz']}]})
    code, out = harness(repo, 'up', '--task', 'T-5')
    recs = records(repo, 'T-5')
    check('launch error: FAIL, earlier service stopped, FAIL record written',
          code == 1 and 'cannot run' in out and not record_run_port_open(api)
          and len(recs) == 1 and recs[0]['verdict'] == 'FAIL', out + json.dumps(recs))
    repo = new_repo({'services': [{'name': 'api', 'port': free_port(), 'cmd': ['x'], 'env_file': 'missing.env'}]})
    code, out = harness(repo, 'up')
    check('missing env_file: FAIL before starting', code == 1 and 'env_file' in out and 'starting' not in out, out)


def test_timeout_and_cleanup():
    port, never = free_port(), free_port()
    svc = http_service('api', port, timeout=3)
    svc['health'] = f'http://127.0.0.1:{never}/'
    repo = new_repo({'services': [svc]})
    code, out = harness(repo, 'up')
    check('health timeout: FAIL and the started process is stopped',
          code == 1 and 'not healthy within 3s' in out and not record_run_port_open(port), out)
    recs = records(repo)
    check('failed record points at the failing log', len(recs) == 1 and (recs[0]['log'] or '').endswith('api.log'),
          json.dumps(recs))
    check('health timeout leaves no state behind',
          not os.path.exists(os.path.join(repo, '.devkit', 'runtime', 'main', 'state.json')))


def test_early_exit():
    repo = new_repo({'services': [{'name': 'api', 'port': free_port(), 'cmd': [PY, '-c', 'print("boom"); raise SystemExit(3)'],
                                   'timeout': 20}]})
    code, out = harness(repo, 'up')
    check('process exits early: FAIL with exit code and log tail', code == 1 and 'exited with code 3' in out
          and 'boom' in out, out)


def test_env_and_placeholders():
    api, web = free_port(), free_port()
    probe = os.path.join(tempfile.mkdtemp(), 'env.txt')
    web_svc = {'name': 'web', 'port': web, 'depends': ['api'], 'timeout': 20,
               'env': {'API_TARGET': 'http://localhost:{api.port}'},
               'cmd': [PY, '-c', 'import os,sys,http.server as h;open(sys.argv[1],"w").write(os.environ["API_TARGET"]);'
                       'h.test(h.SimpleHTTPRequestHandler, port=int(sys.argv[2]), bind="127.0.0.1")', probe, '{port}'],
               'health': 'http://127.0.0.1:{port}/'}
    repo = new_repo({'services': [http_service('api', api), web_svc]})
    code, out = harness(repo, 'up')
    seen = open(probe).read() if os.path.exists(probe) else ''
    check('service env gets {api.port} expanded', code == 0 and seen == f'http://localhost:{api}', out + seen)
    harness(repo, 'down')


def test_worktree_slot():
    api = free_port()
    while api + 10 > 65535 or record_run_port_open(api + 10):
        api = free_port()
    repo = new_repo({'services': [http_service('api', api)]})
    wt = os.path.join(repo, 'worktrees', 'task-a')
    sh('git', '-C', repo, 'worktree', 'add', '-q', '-b', 'feat/task-a', wt)
    code, out = harness(wt, 'up', '--task', 'T-3')
    check('worktree instance gets port +10 and its own state', code == 0 and f'port {api + 10}' in out
          and os.path.exists(os.path.join(repo, '.devkit', 'runtime', 'task-a', 'state.json')), out)
    recs = records(repo, 'T-3')
    check('worktree record lands in the main repo with the worktree instance name',
          len(recs) == 1 and recs[0]['instance'] == 'task-a' and recs[0]['branch'] == 'feat/task-a', json.dumps(recs))
    code, out = harness(repo, 'status')
    check('main instance status does not show the worktree instance', 'nothing started' in out, out)
    harness(wt, 'down')


def test_record_run():
    cases = [('CHECKS: PASS', ('checks', 'PASS', '')), ('CHECKS: PASS (2 not run)', ('checks', 'PARTIAL', '2 not run')),
             ('CHECKS: FAIL (3 commands)', ('checks', 'FAIL', '3 commands')), ('VERDICT: PASS (7 items)', ('verifier', 'PASS', '7 items')),
             ('VERDICT: FAIL (2 items)', ('verifier', 'FAIL', '2 items'))]
    for line, want in cases:
        check(f'parse {line!r}', record_run.parse_line(line) == want, str(record_run.parse_line(line)))
    try:
        record_run.parse_line('all good')
        check('non-contract line is refused', False)
    except ValueError:
        check('non-contract line is refused', True)
    try:
        record_run.parse_line('CHECKS: PASS (1 skipped)')
        check('CHECKS: PASS with a detail other than "<k> not run" is refused', False)
    except ValueError:
        check('CHECKS: PASS with a detail other than "<k> not run" is refused', True)
    repo = new_repo(None)
    r = sh(PY, '-I', os.path.join(HERE, '..', '..', 'check', 'scripts', 'record_run.py'), '--repo', repo,
           '--line', 'CHECKS: PASS (1 not run)')
    path = r.stdout.strip()
    check('record without task goes to .devkit/runs/', r.returncode == 0 and '/.devkit/runs/' in path
          and json.load(open(path))['verdict'] == 'PARTIAL', r.stdout + r.stderr)
    check('.devkit/ is added to info/exclude when not ignored',
          sh('git', '-C', repo, 'check-ignore', '-q', '.devkit/x').returncode == 0, r.stderr)
    items = os.path.join(tempfile.mkdtemp(), 'items.json')
    json.dump([{'name': 'login', 'result': 'PASS', 'env': {'DB_PASS': 'x'}}], open(items, 'w'))
    r = sh(PY, '-I', os.path.join(HERE, '..', '..', 'check', 'scripts', 'record_run.py'), '--repo', repo,
           '--kind', 'db', '--verdict', 'PASS', '--items', items)
    check('items with extra keys (env, secrets) are refused', r.returncode == 2 and 'allowed' in r.stderr, r.stderr)
    r = sh(PY, '-I', os.path.join(HERE, '..', '..', 'check', 'scripts', 'record_run.py'), '--repo', repo,
           '--task', '../x', '--kind', 'db', '--verdict', 'PASS')
    check('task id with a path separator is refused', r.returncode == 2, r.stderr)


def test_worktree_env_file_and_repo_after_command():
    port = free_port()
    while port + 10 > 65535 or record_run_port_open(port + 10):
        port = free_port()
    probe = os.path.join(tempfile.mkdtemp(), 'env.txt')
    svc = {'name': 'api', 'port': port, 'timeout': 20, 'env_file': 'local.env',
           'cmd': [PY, '-c', 'import os,sys,http.server as h;open(sys.argv[1],"w").write(os.environ["WHERE"]);'
                   'h.test(h.SimpleHTTPRequestHandler, port=int(sys.argv[2]), bind="127.0.0.1")', probe, '{port}'],
           'health': 'http://127.0.0.1:{port}/'}
    repo = new_repo({'services': [svc]})
    with open(os.path.join(repo, 'local.env'), 'w') as f:  # untracked, so the worktree does not have it
        f.write('WHERE=main\n')
    wt = os.path.join(repo, 'worktrees', 'task-b')
    sh('git', '-C', repo, 'worktree', 'add', '-q', '-b', 'feat/task-b', wt)
    r = sh(PY, '-I', RUNTIME, 'up', '--repo', wt)
    seen = open(probe).read() if os.path.exists(probe) else ''
    check('worktree without the env_file uses the main checkout file; --repo works after the command',
          r.returncode == 0 and seen == 'main' and f'port {port + 10}' in r.stdout, r.stdout + r.stderr + seen)
    harness(wt, 'down')
    with open(os.path.join(wt, 'local.env'), 'w') as f:
        f.write('WHERE=worktree\n')
    code, out = harness(wt, 'up')
    seen = open(probe).read() if os.path.exists(probe) else ''
    check('worktree env_file wins over the main checkout file', code == 0 and seen == 'worktree', out + seen)
    harness(wt, 'down')


if __name__ == '__main__':
    for fn in [v for k, v in sorted(globals().items()) if k.startswith('test_')]:
        fn()
    print(f'\n{"FAILED: " + ", ".join(FAILS) if FAILS else "all passed"}')
    sys.exit(1 if FAILS else 0)
