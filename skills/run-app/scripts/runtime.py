"""devkit runtime harness: start, check and stop a repo's app servers from <main repo>/.devkit/runtime.json.

Usage (run with python3 -I; --repo defaults to the current folder, a main checkout or a git worktree):
  runtime.py preflight              check the TCP prerequisites (DB tunnel and so on); starts nothing
  runtime.py up [svc...] [--task ID] preflight, start services (and what they depend on), wait for health, record
  runtime.py status [--json]        services of this instance: pid, port, health
  runtime.py down [svc...]          stop what this harness started for this instance and wait for the ports to free
  runtime.py logs <svc> [-n N]      tail a service log
Each checkout is one instance: the main checkout uses the configured ports, each worktree gets its own port slot.
State and logs: <main repo>/.devkit/runtime/<instance>/. The harness only stops processes it started itself, and never
starts anything that a port already in use would collide with (an IDE run, another session).
The last line of up/preflight is `RUNTIME: PASS` or `RUNTIME: FAIL (<reason>)`.
"""
import argparse
import datetime
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'check', 'scripts'))
import record_run  # noqa: E402  (shared with devkit:check; -I drops the script folder from sys.path)

CONFIG = os.path.join('.devkit', 'runtime.json')
STATE_DIR = os.path.join('.devkit', 'runtime')
PORT_STEP = 10        # worktree slot k shifts every port by k*10, so 8001/3001 become 8011/3011 and stay recognisable
MAX_SLOTS = 9         # at most 9 worktree instances at once; parallel-work runs 3 workers, this leaves headroom
DEFAULT_TIMEOUT = 120  # seconds a service gets to become healthy unless the config sets "timeout"
POLL = 2              # seconds between health probes: frequent enough to not add noticeable wait
PROBE_TIMEOUT = 3     # seconds per HTTP or TCP probe; a local server that is up answers far faster
STOP_GRACE = 20       # seconds after SIGTERM before SIGKILL; Spring Boot shutdown hooks finish well inside this
PORT_FREE_WAIT = 10   # seconds to wait for a port to close after the process is gone
TAIL = 40             # log lines shown when a start fails
PLACEHOLDER = re.compile(r'\{([\w.-]+)\}')


class HarnessError(Exception):
    pass


# ---------- repo, config, state ----------

def instance_root(repo):
    top = record_run.git(repo, 'rev-parse', '--show-toplevel')
    if not top:
        raise HarnessError(f'{repo} is not inside a git repository')
    return top


def load_config(main):
    path = os.path.join(main, CONFIG)
    if not os.path.exists(path):
        raise HarnessError(f'no {path}. This repo has not opted in to the runtime harness; '
                           'the user starts servers. See the run-app skill for the config format.')
    try:
        with open(path, encoding='utf-8') as f:
            cfg = json.load(f)
    except ValueError as e:
        raise HarnessError(f'{path}: invalid JSON ({e})')
    names = []
    for i, s in enumerate(cfg.get('services') or []):
        where = f'{path}: services[{i}]'
        if not isinstance(s.get('name'), str) or not re.match(r'^[\w-]+$', s['name']):
            raise HarnessError(f'{where}.name must be letters, digits, "_" or "-"')
        if s['name'] in names:
            raise HarnessError(f'{where}.name {s["name"]!r} is duplicated')
        if not isinstance(s.get('port'), int):
            raise HarnessError(f'{where}.port must be an integer')
        if not (isinstance(s.get('cmd'), list) and s['cmd'] and all(isinstance(c, str) for c in s['cmd'])):
            raise HarnessError(f'{where}.cmd must be a non-empty list of strings (no shell)')
        for d in s.get('depends') or []:
            if d not in names:
                raise HarnessError(f'{where}.depends {d!r} must name a service listed earlier')
        names.append(s['name'])
    if not names:
        raise HarnessError(f'{path}: "services" is empty')
    return cfg


def state_path(main, instance):
    return os.path.join(main, STATE_DIR, instance, 'state.json')


def read_state(main, instance):
    try:
        with open(state_path(main, instance), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_state(main, instance, state):
    path = state_path(main, instance)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not state.get('services'):
        if os.path.exists(path):
            os.remove(path)
        return
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Lock:
    """One harness command per instance at a time (two sessions running `up` together)."""

    def __init__(self, main, instance):
        self.path = os.path.join(main, STATE_DIR, instance, '.lock')

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.f = open(self.path, 'w')
        try:
            import fcntl
        except ImportError:  # Windows: no advisory lock; rely on the port checks
            return self
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            raise HarnessError('another harness command is running for this instance; wait for it and retry')
        return self

    def __exit__(self, *exc):
        self.f.close()


# ---------- ports and processes ----------

def port_in_use(port, host='localhost'):
    """True if anything accepts connections on the port (IPv4 or IPv6: Vite may bind only ::1)."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('127.0.0.1', port))]
    for family, kind, proto, _, addr in infos:
        with socket.socket(family, kind, proto) as s:
            s.settimeout(PROBE_TIMEOUT)
            if s.connect_ex(addr) == 0:
                return True
    return False


def listener(port):
    """'pid 123 (cwd /path)' for the process listening on the port, when lsof can tell."""
    try:
        pid = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'],
                             capture_output=True, text=True, timeout=5).stdout.split()
        if not pid:
            return 'unknown process'
        cwd = subprocess.run(['lsof', '-a', '-p', pid[0], '-d', 'cwd', '-Fn'],
                             capture_output=True, text=True, timeout=5).stdout
        folder = next((ln[1:] for ln in cwd.splitlines() if ln.startswith('n')), '?')
        return f'pid {pid[0]} (cwd {folder})'
    except (OSError, subprocess.SubprocessError):
        return 'unknown process (lsof unavailable)'


def alive(pid):
    if not pid:
        return False
    if os.name == 'nt':
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:  # the harness starts each service as a session leader; a reused pid is not one
        return os.getpgid(pid) == pid
    except OSError:
        return False


def stop_group(pid):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)
        return
    for sig, wait in ((signal.SIGTERM, STOP_GRACE), (signal.SIGKILL, 5)):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return
        end = time.time() + wait
        while time.time() < end:
            try:  # a child started by this same call stays a zombie (and looks alive) until it is reaped
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
            try:  # the whole group, not just the leader: gradle bootRun runs the app in a child JVM
                os.killpg(pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                pass
            time.sleep(0.5)


def probe(url):
    """(ready, detail). Ready means HTTP 2xx/3xx; 4xx/5xx (for example a DB-backed health check reporting DOWN) is not."""
    if url.startswith('tcp://'):
        host, _, port = url[6:].rpartition(':')
        return (port_in_use(int(port), host or 'localhost'), 'tcp')
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=PROBE_TIMEOUT) as r:
            return (200 <= r.status < 400, f'HTTP {r.status}')
    except urllib.error.HTTPError as e:
        return (False, f'HTTP {e.code}')
    except (urllib.error.URLError, OSError) as e:
        return (False, type(getattr(e, 'reason', e)).__name__)


# ---------- placeholders and ports ----------

def ports_for(cfg, slot):
    return {s['name']: s['port'] + slot * PORT_STEP for s in cfg['services']}


def expand(text, values):
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise HarnessError(f'unknown placeholder {{{key}}} in {text!r}; known: {sorted(values)}')
        return str(values[key])
    return PLACEHOLDER.sub(sub, text)


def values_for(svc, ports, root, instance):
    v = {'root': root, 'instance': instance, 'port': ports[svc['name']]}
    v.update({f'{n}.port': p for n, p in ports.items()})
    return v


def claimed_ports(main, instance):
    """Ports recorded by the other instances' state files."""
    taken = set()
    folder = os.path.join(main, STATE_DIR)
    for name in (os.listdir(folder) if os.path.isdir(folder) else []):
        if name != instance:
            taken.update(s.get('port') for s in read_state(main, name).get('services', {}).values())
    return taken


def pick_slot(cfg, main, instance, state):
    if 'slot' in state:
        return state['slot']
    if instance == 'main':
        return 0
    taken = claimed_ports(main, instance)
    for slot in range(1, MAX_SLOTS + 1):
        ports = ports_for(cfg, slot).values()
        if not any(p in taken or port_in_use(p) for p in ports):
            return slot
    raise HarnessError(f'no free port slot for worktree instance {instance!r} (tried {MAX_SLOTS}); stop another instance')


def order_with_deps(cfg, wanted):
    by_name = {s['name']: s for s in cfg['services']}
    unknown = [w for w in wanted if w not in by_name]
    if unknown:
        raise HarnessError(f'unknown service {unknown}; configured: {list(by_name)}')
    need = set(wanted or by_name)
    for s in reversed(cfg['services']):  # depends only point to earlier services, so one backward pass closes it
        if s['name'] in need:
            need.update(s.get('depends') or [])
    return [s for s in cfg['services'] if s['name'] in need]


# ---------- commands ----------

def run_preflight(cfg):
    items = []
    for c in cfg.get('preflight') or []:
        host, _, port = str(c.get('tcp', '')).rpartition(':')
        ok = port.isdigit() and port_in_use(int(port), host or 'localhost')
        detail = '' if ok else (c.get('hint') or f'nothing listening on {c.get("tcp")}')
        items.append({'name': f'preflight:{c.get("name", c.get("tcp"))}', 'result': 'PASS' if ok else 'FAIL',
                      'detail': detail})
    return items


def read_env_file(path):
    """KEY=VALUE lines (# comments, optional quotes). Values go only to the child, never to output or records."""
    out = {}
    try:
        with open(path, encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, sep, value = (line[len('export '):] if line.startswith('export ') else line).partition('=')
                if not sep or not re.match(r'^[A-Za-z_]\w*$', key.strip()):
                    raise HarnessError(f'{path}:{n}: expected KEY=VALUE')
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                    value = value[1:-1]
                out[key.strip()] = value
    except OSError as e:
        raise HarnessError(f'env_file {path}: {e.strerror}')
    return out


def child_env(cfg, svc, values):
    env = dict(os.environ)
    java_home = svc.get('java_home') or cfg.get('java_home')
    if java_home:
        env['JAVA_HOME'] = expand(java_home, values)
    for scope in (cfg, svc):  # service-level keys override top-level ones
        if scope.get('env_file'):
            env.update(read_env_file(os.path.join(values['root'], expand(scope['env_file'], values))))
        for k, v in (scope.get('env') or {}).items():
            env[k] = expand(str(v), values)
    prepend = [expand(p, values) for p in (cfg.get('path_prepend') or []) + (svc.get('path_prepend') or [])]
    if java_home:
        prepend.insert(0, os.path.join(env['JAVA_HOME'], 'bin'))
    if prepend:
        env['PATH'] = os.pathsep.join(prepend + [env.get('PATH', '')])
    return env


def tail(path, n=TAIL):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return ''.join(f.readlines()[-n:])
    except OSError:
        return ''


def start(cfg, svc, values, root, logdir):
    cwd = os.path.join(root, expand(svc.get('cwd', '.'), values))
    cmd = [expand(c, values) for c in svc['cmd']]
    log = os.path.join(logdir, f'{svc["name"]}.log')
    logf = open(log, 'w', encoding='utf-8')
    logf.write(f'# {datetime.datetime.now().isoformat(timespec="seconds")} cwd={cwd} cmd={cmd}\n')
    logf.flush()
    kw = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=child_env(cfg, svc, values), stdin=subprocess.DEVNULL,
                                stdout=logf, stderr=subprocess.STDOUT, **kw)
    except OSError as e:
        logf.close()
        raise HarnessError(f'{svc["name"]}: cannot run {cmd[0]!r} in {cwd} ({e})')
    logf.close()
    return proc, log


def wait_healthy(svc, proc, url, timeout):
    end = time.time() + timeout
    last = 'no answer'
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            return False, f'process exited with code {proc.returncode} before it was healthy'
        ok, last = probe(url)
        if ok:
            return True, last
        time.sleep(POLL)
    return False, f'not healthy within {timeout}s (last: {last})'


def cmd_up(args, cfg, main, root, instance):
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    items = run_preflight(cfg)
    services = order_with_deps(cfg, args.services)
    started, failed = [], None
    with Lock(main, instance):
        state = read_state(main, instance)
        slot = pick_slot(cfg, main, instance, state)
        ports = ports_for(cfg, slot)
        state.update({'instance': instance, 'root': root, 'slot': slot})
        state.setdefault('services', {})
        logdir = os.path.dirname(state_path(main, instance))
        os.makedirs(logdir, exist_ok=True)
        if any(i['result'] == 'FAIL' for i in items):
            failed = 'preflight'
        failed_log = None
        for svc in ([] if failed else services):
            name, port = svc['name'], ports[svc['name']]
            try:
                values = values_for(svc, ports, root, instance)
                url = expand(svc.get('health') or 'tcp://localhost:{port}', values)
                child_env(cfg, svc, values)  # surface env_file / placeholder errors before anything starts
            except HarnessError as e:
                items.append({'name': name, 'result': 'FAIL', 'detail': str(e)})
                failed = name
                break
            mine = state['services'].get(name)
            if mine and alive(mine.get('pid')):
                ok, detail = probe(url)
                items.append({'name': name, 'result': 'PASS' if ok else 'FAIL',
                              'detail': f'already running (pid {mine["pid"]}, port {port}, {detail})'})
                if not ok:
                    failed = name
                    break
                continue
            state['services'].pop(name, None)
            if port_in_use(port):
                items.append({'name': name, 'result': 'FAIL',
                              'detail': f'port {port} is already in use by {listener(port)}; stop it first '
                                        '(an IDE run or another session) and run up again'})
                failed = name
                break
            print(f'starting {name} on port {port} ...', flush=True)
            try:
                proc, log = start(cfg, svc, values, root, logdir)
            except HarnessError as e:
                items.append({'name': name, 'result': 'FAIL', 'detail': str(e)})
                failed, failed_log = name, os.path.join(logdir, f'{name}.log')
                break
            state['services'][name] = {'pid': proc.pid, 'port': port, 'health': url, 'log': log,
                                       'commit': record_run.git(root, 'rev-parse', '--short', 'HEAD'),
                                       'started_at': datetime.datetime.now().isoformat(timespec='seconds')}
            write_state(main, instance, state)
            started.append(name)
            ok, detail = wait_healthy(svc, proc, url, int(svc.get('timeout', DEFAULT_TIMEOUT)))
            items.append({'name': name, 'result': 'PASS' if ok else 'FAIL', 'detail': f'port {port}, {detail}'})
            if not ok:
                failed, failed_log = name, log
                print(f'--- last lines of {log} ---\n{tail(log)}', flush=True)
                break
        if failed:  # leave nothing half-started by this call; services that were already up stay up
            for name in reversed(started):
                stop_group(state['services'][name]['pid'])
                state['services'].pop(name, None)
        write_state(main, instance, state)
    for i in items:
        print(f'{i["result"]:4}  {i["name"]}  {i.get("detail", "")}')
    if not failed:
        for name, s in state['services'].items():
            print(f'url   {name}: http://localhost:{s["port"]}/  (log {s["log"]})')
    verdict = 'FAIL' if failed else 'PASS'
    summary = f'{failed} failed' if failed else f'{len(services)} service(s) healthy on instance {instance}'
    try:
        path, _ = record_run.write_record(root, 'runtime', verdict, summary, args.task, items, log=failed_log,
                                          started_at=started_at)
        print(f'record {path}')
    except (ValueError, OSError) as e:
        print(f'record not written: {e}')
    print(f'RUNTIME: {verdict}' + (f' ({summary})' if failed else ''))
    return 1 if failed else 0


def cmd_preflight(args, cfg, main, root, instance):
    items = run_preflight(cfg)
    for i in items:
        print(f'{i["result"]:4}  {i["name"]}  {i["detail"]}')
    bad = [i['name'] for i in items if i['result'] == 'FAIL']
    print('RUNTIME: ' + (f'FAIL ({", ".join(bad)})' if bad else 'PASS'))
    return 1 if bad else 0


def cmd_status(args, cfg, main, root, instance):
    state = read_state(main, instance)
    rows = []
    for name, s in state.get('services', {}).items():
        ok, detail = probe(s['health']) if alive(s.get('pid')) else (False, 'process gone')
        rows.append({'name': name, 'pid': s.get('pid'), 'port': s.get('port'), 'healthy': ok, 'detail': detail,
                     'commit': s.get('commit'), 'log': s.get('log')})
    if args.json:
        print(json.dumps({'instance': instance, 'root': root, 'services': rows}, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print(f'instance {instance}: nothing started by the harness')
        return 0
    for r in rows:
        print(f'{"UP" if r["healthy"] else "DOWN":4}  {r["name"]}  pid {r["pid"]}  port {r["port"]}  '
              f'{r["detail"]}  commit {r["commit"]}')
    return 0


def cmd_down(args, cfg, main, root, instance):
    with Lock(main, instance):
        state = read_state(main, instance)
        names = [s['name'] for s in reversed(cfg['services']) if s['name'] in state.get('services', {})]
        names += [n for n in state.get('services', {}) if n not in names]  # services removed from the config
        if args.services:
            names = [n for n in names if n in args.services]
        busy = []
        for name in names:
            s = state['services'][name]
            if alive(s.get('pid')):
                print(f'stopping {name} (pid {s["pid"]}) ...', flush=True)
                stop_group(s['pid'])
            end = time.time() + PORT_FREE_WAIT
            while port_in_use(s['port']) and time.time() < end:
                time.sleep(0.5)
            if port_in_use(s['port']):
                busy.append(f'{name}: port {s["port"]} still in use by {listener(s["port"])}')
            state['services'].pop(name)
        write_state(main, instance, state)
    for b in busy:
        print(f'WARN  {b}')
    print(f'stopped {len(names)} service(s) on instance {instance}' if names else f'instance {instance}: nothing to stop')
    return 1 if busy else 0


def cmd_logs(args, cfg, main, root, instance):
    s = read_state(main, instance).get('services', {}).get(args.service)
    log = s['log'] if s else os.path.join(main, STATE_DIR, instance, f'{args.service}.log')
    if not os.path.exists(log):
        print(f'no log for {args.service} on instance {instance}')
        return 1
    print(tail(log, args.n), end='')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description='devkit runtime harness')
    p.add_argument('--repo', default=os.getcwd())
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight')
    up = sub.add_parser('up')
    up.add_argument('services', nargs='*')
    up.add_argument('--task')
    st = sub.add_parser('status')
    st.add_argument('--json', action='store_true')
    dn = sub.add_parser('down')
    dn.add_argument('services', nargs='*')
    lg = sub.add_parser('logs')
    lg.add_argument('service')
    lg.add_argument('-n', type=int, default=TAIL * 2)
    args = p.parse_args(argv)
    try:
        root = instance_root(args.repo)
        main_repo = record_run.main_root(root)
        instance = record_run.instance_name(root)
        cfg = load_config(main_repo)
        handler = {'preflight': cmd_preflight, 'up': cmd_up, 'status': cmd_status,
                   'down': cmd_down, 'logs': cmd_logs}[args.command]
        return handler(args, cfg, main_repo, root, instance)
    except HarnessError as e:
        print(f'runtime: {e}', file=sys.stderr)
        if args.command in ('up', 'preflight'):
            print(f'RUNTIME: FAIL ({e})')
        return 2


if __name__ == '__main__':
    sys.exit(main())
