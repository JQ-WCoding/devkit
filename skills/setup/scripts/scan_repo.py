"""Collect a repository fingerprint (layout, conventions, history) as the starting point for pinpoint analysis. Never modifies files.

Usage: python3 -I scan_repo.py <repo root> [--since <YYYY-MM-DD | commit>] [--out <result.json>]
- stdout: human-readable summary (Markdown). --out writes the full result as JSON.
- --since limits history items (fix commits, hotspots, doc commits) to after that point (update mode).
Requires: Python 3.8+. Without git or outside a repository, only the history items are skipped.
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Generated, dependency and tool folders are not project conventions, so skip them
SKIP_DIRS = {
    '.git', 'node_modules', 'build', 'dist', 'out', 'target', '.gradle', '.idea', '.vscode',
    'vendor', 'venv', '.venv', '__pycache__', 'coverage', '.next', '.nuxt', 'bin', 'obj',
    'logs', '.claude', '.codex', '.agents', '.cache', 'tmp',
}
# Cap the number of files read so even very large repos finish in 1-2 minutes
MAX_WALK_FILES = 40000
MAX_READ_FILES = 15000
MAX_READ_BYTES = 1024 * 1024
STYLE_SAMPLE_PER_EXT = 300
# Fix-commit hotspots matter for recent history, so look at this many commits only
HISTORY_LIMIT = 600

SOURCE_EXTS = {'.properties', '.yml', '.yaml', '.gradle', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.java', '.kt', '.py', '.go',
               '.rb', '.php', '.cs', '.rs', '.xml', '.sql', '.css', '.scss'}
MANIFESTS = {
    'package.json': 'node', 'build.gradle': 'gradle', 'build.gradle.kts': 'gradle',
    'pom.xml': 'maven', 'go.mod': 'go', 'Cargo.toml': 'rust', 'pyproject.toml': 'python',
    'requirements.txt': 'python', 'setup.py': 'python', 'Gemfile': 'ruby',
    'composer.json': 'php', 'Dockerfile': 'docker', 'docker-compose.yml': 'compose',
    'docker-compose.yaml': 'compose', 'compose.yml': 'compose', 'compose.yaml': 'compose',
}
# package.json dependencies used to judge structure (shown with versions)
NODE_HINTS = re.compile(
    r'^(react|react-dom|react-router-dom|vue|nuxt|next|@angular/core|svelte|vite|webpack|typescript|'
    r'eslint|prettier|jest|vitest|axios|redux|@reduxjs/toolkit|zustand|@tanstack/react-query|'
    r'tailwindcss|express|@nestjs/core|@syncfusion/.+|ag-grid.*|antd|@mui/material|electron)$')
# Format and static-analysis tools in the build config: evidence for "what the linter already blocks"
QUALITY_TOOLS = re.compile(r'(spring-javaformat|checkstyle|spotless|pmd|spotbugs|errorprone|ktlint|detekt|nohttp|'
                           r'eslint|prettier|stylelint|biome|ruff|black|flake8|mypy|pylint|golangci|rubocop|license-maven-plugin)', re.I)
JVM_HINTS = {
    'spring-boot': r'org\.springframework\.boot', 'mybatis': r'mybatis', 'jpa': r'jpa|hibernate',
    'querydsl': r'querydsl', 'jasperreports': r'jasperreports', 'lombok': r'lombok',
    'oracle-driver': r'ojdbc', 'postgres-driver': r'postgresql', 'mysql-driver': r'mysql|mariadb',
    'flyway': r'flyway', 'liquibase': r'liquibase', 'h2-driver': r'com\.h2database|\bh2\b',
}
CI_FILES = ['.gitlab-ci.yml', 'Jenkinsfile', 'azure-pipelines.yml', 'bitbucket-pipelines.yml',
            '.circleci/config.yml']
AI_CONFIG = ['CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', 'AGENTS.local.md', '.cursorrules',
             '.windsurfrules', '.github/copilot-instructions.md', 'CONTRIBUTING.md', 'README.md',
             '.editorconfig']
STYLE_CONFIG = re.compile(r'^(\.editorconfig|\.prettierrc.*|prettier\.config\..*|\.eslintrc.*|'
                          r'eslint\.config\..*|checkstyle.*\.xml|\.clang-format|ruff\.toml|'
                          r'\.stylelintrc.*|tsconfig\.json|jsconfig\.json)$')
DB_KINDS = [('h2', r'jdbc:h2|\bh2\b'), ('oracle', r'jdbc:oracle|oracle\.jdbc'), ('postgres', r'jdbc:postgresql|postgres://'),
            ('mysql', r'jdbc:mysql|jdbc:mariadb|mysql://'), ('sqlserver', r'jdbc:sqlserver'),
            ('sqlite', r'sqlite'), ('mongodb', r'mongodb(\+srv)?://')]
# Warning marks left by authors are traces of incidents and pitfalls (S3 candidates). Korean markers stay so Korean repos still match
WARN_MARK = re.compile(r'(주의|반드시|금지|하지 말 것|하지 않는다|절대|IMPORTANT|WARNING|CAUTION|HACK|FIXME|XXX|'
                       r"[Dd]on't|[Dd]o not|[Mm]ust not|[Nn]ever |[Nn]eeds to stay|[Kk]eep in sync|[Cc]areful)")
# Defect-fix commits use verbs other than 'fix' too (Prevent HTTP 500…, Validate…, Mitigate…); Korean verbs match Korean repos
FIX_SUBJECT = re.compile(r'^(fix|hotfix|revert|prevent|validate|mitigate|handle|correct|resolve|avoid|guard)\b|\bfix(es|ed)?\b|^Revert |버그|오류 수정|장애|방지', re.I)
CONVENTIONAL = re.compile(r'^(\w+)(?:\(([^)]+)\))?!?: ?(.+)$')
HANGUL = re.compile(r'[가-힣]')
JS_IMPORT = re.compile(r'''(?:import\s[^'"]*?from\s*|import\s*\(\s*|require\(\s*|^\s*import\s+)['"]([^'"]+)['"]''', re.M)
JAVA_IMPORT = re.compile(r'^import\s+(?:static\s+)?([\w.]+?)(?:\.\*)?;', re.M)
JAVA_PACKAGE = re.compile(r'^package\s+([\w.]+);', re.M)
PY_IMPORT = re.compile(r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.M)
JS_PATH_LITERAL = re.compile(r'''['"`](/[A-Za-z][\w-]*(?:/[\w{}:.-]+){1,4})['"`]''')
JAVA_MAPPING = re.compile(r'@(?:Request|Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?\{?\s*"([^"]+)"')
SECRET_IN_URL = re.compile(r'//[^/@\s]+@')
# Assets and generated files excluded from the extension ranking (useless for conventions)
ASSET_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.woff', '.woff2', '.ttf', '.eot',
              '.otf', '.rels', '.map', '.lock', '.DS_Store', '.pdf', '.zip', '.jar', '.class', '.mp4', '.mp3'}
# Archive or old-code folders; flagged in fix hotspots so they are not used as evidence
ARCHIVE_DIR = re.compile(r'(^|/)(archive|archived|old|deprecated|legacy|backup)(/|$)', re.I)
# Injected fields and shared objects don't show up as imports, so count `receiver.method(` calls by file (S1/S2 candidates)
MEMBER_CALL = re.compile(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(')
# Receivers that are language built-ins or common local names are not project conventions, so skip them
GENERIC_RECEIVERS = {
    'console', 'Math', 'Object', 'Array', 'JSON', 'Promise', 'window', 'document', 'this', 'super',
    'props', 'String', 'Number', 'Date', 'e', 'event', 'res', 'response', 'data', 'list', 'item',
    'row', 'args', 'arr', 'obj', 'el', 'ref', 'React', 'System', 'log', 'logger', 'LOGGER', 'LOG',
    'map', 'param', 'params', 'result', 'str', 'sb', 'value', 'values', 'entry', 'key', 'Arrays',
    'Collections', 'Objects', 'Optional', 'Stream', 'Collectors', 'Integer', 'Long', 'Boolean',
    'Double', 'BigDecimal', 'it', 'self', 'os', 'sys', 're', 'json', 'path', 'Path', 'Files',
    'navigator', 'localStorage', 'sessionStorage', 'history', 'location', 'prev', 'current',
    'target', 'node', 'child', 'parent', 'options', 'config', 'error', 'err', 'ex', 'Character',
    'StringBuilder', 'Thread', 'file', 'f', 'i', 'x', 'r', 'c', 'm', 'p', 's', 'k', 'v', 'd', 'a', 'b',
}


def run(cmd, cwd):
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120,
                             encoding='utf-8', errors='replace')
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def walk(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')
                             or d in ('.github', '.circleci'))
        for name in sorted(filenames):
            files.append(Path(dirpath, name).relative_to(root))
            if len(files) >= MAX_WALK_FILES:
                return files, True
    return files, False


def read(root, rel):
    path = root / rel
    try:
        if path.stat().st_size > MAX_READ_BYTES:
            return None
        return path.read_bytes().decode('utf-8', errors='replace')
    except OSError:
        return None


def scan_manifests(root, files):
    found = []
    for rel in files:
        kind = MANIFESTS.get(rel.name) or ('dotnet' if rel.suffix in ('.csproj', '.sln') else None)
        if not kind or len(rel.parts) > 4:
            continue
        item = {'path': str(rel), 'kind': kind}
        text = read(root, rel) or ''
        if kind == 'node':
            try:
                pkg = json.loads(text)
            except ValueError:
                pkg = {}
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            item['hints'] = {k: v for k, v in sorted(deps.items()) if NODE_HINTS.match(k)}
            item['scripts'] = sorted(pkg.get('scripts', {}))
            if pkg.get('engines'):
                item['engines'] = pkg['engines']
        elif kind in ('gradle', 'maven'):
            item['hints'] = sorted(k for k, pat in JVM_HINTS.items() if re.search(pat, text, re.I))
            boot = re.search(r'spring-boot-starter-parent</artifactId>\s*<version>([^<]+)', text) \
                or re.search(r"org\.springframework\.boot['\"]?\)?\s*version\s*['\"]([^'\"]+)", text)
            if boot:
                item['spring_boot'] = boot.group(1)
            m = re.search(r'(?:sourceCompatibility|java\.version|languageVersion)\D{0,40}?(\d+(?:\.\d+)?)', text)
            if m:
                item['java'] = m.group(1)
        tools = sorted({m.lower() for m in QUALITY_TOOLS.findall(text)})
        if tools:
            item['quality_tools'] = tools
        found.append(item)
    return found


def scan_ci(root, files):
    names = set(map(str, files))
    ci = [f for f in CI_FILES if f in names]
    ci += [str(f) for f in files if str(f).startswith('.github/workflows/')]
    detail = {}
    for f in ci:
        text = read(root, Path(f)) or ''
        lines = [l.strip() for l in text.splitlines()
                 if re.search(r'\b(only|except|rules|if|branches|when|stage|stages|on)\s*:', l)]
        detail[f] = lines[:12]
    return detail


def scan_db(root, files):
    sql = [f for f in files if f.suffix.lower() == '.sql']
    sql_dirs = Counter(str(f.parent) for f in sql).most_common(8)
    mappers, migrations, kinds = [], set(), Counter()
    for f in files:
        s = str(f)
        if re.search(r'(db/migration|migrations?/|liquibase|alembic|prisma/schema\.prisma)', s):
            migrations.add(str(f.parent))
        if f.suffix == '.xml' and len(mappers) < 2000:
            text = read(root, f)
            if text and '<mapper namespace' in text:
                mappers.append(s)
        if re.match(r'(application.*\.(ya?ml|properties)|\.env\.example|.*\.env\.sample)$', f.name):
            text = read(root, f) or ''
            for kind, pat in DB_KINDS:
                if re.search(pat, text, re.I):
                    kinds[kind] += 1
    mapper_dirs = Counter(str(Path(m).parent.parent) for m in mappers).most_common(5)
    entities, read_n = 0, 0
    for f in files:
        if f.suffix in ('.java', '.kt', '.py', '.ts') and read_n < 8000:
            read_n += 1
            text = read(root, f) or ''
            if re.search(r'^\s*@Entity\b|\(models\.Model\)|@Entity\(|^\s*@Table\(', text, re.M):
                entities += 1
        elif f.name == 'schema.prisma':
            entities += len(re.findall(r'^model\s+\w+', read(root, f) or '', re.M))
    init_scripts = sorted(str(f) for f in sql if re.match(r'(schema|data|init|seed)[\w-]*\.sql$', f.name))[:10]
    return {'sql_files': len(sql), 'sql_dirs': sql_dirs, 'mybatis_mappers': len(mappers),
            'orm_entities': entities, 'init_scripts': init_scripts,
            'mapper_roots': mapper_dirs, 'migration_dirs': sorted(migrations)[:10],
            'db_kinds_in_config': dict(kinds)}


def scan_ai_config(root, files):
    names = set(map(str, files))
    present = [f for f in AI_CONFIG if (root / f).exists()]
    claude = root / '.claude'
    detail = {}
    if claude.is_dir():
        detail['.claude/agents'] = sorted(p.stem for p in (claude / 'agents').glob('*.md'))
        detail['.claude/skills'] = sorted(p.parent.name for p in (claude / 'skills').glob('*/SKILL.md'))
        detail['.claude/settings'] = sorted(p.name for p in claude.glob('settings*.json'))
    for d in ('docs/rules', '.cursor/rules', 'docs/guide', 'docs/conventions'):
        if (root / d).is_dir():
            detail[d] = sorted(p.name for p in (root / d).iterdir() if p.is_file())[:30]
    gitignore = (root / '.gitignore')
    ignored = []
    if gitignore.exists():
        for line in gitignore.read_text(errors='replace').splitlines():
            if re.search(r'CLAUDE|\.claude|AGENTS|\.codex|\.cursor|docs', line):
                ignored.append(line.strip())
    docs_top = sorted({str(f).split('/')[1] for f in files if str(f).startswith('docs/') and len(f.parts) > 1})
    tracked = run(['git', 'ls-files', 'docs'], root)
    docs_tracked = len(tracked.splitlines()) if tracked is not None else None
    return {'present': present, 'detail': detail, 'gitignore_lines': ignored, 'docs_tracked': docs_tracked,
            'docs_top': docs_top[:40], 'has_mcp_json': '.mcp.json' in names or (root / '.mcp.json').exists()}


def indent_of(text):
    """Estimate a file's indent unit: 'tab' | 2 | 4 | other number | None."""
    tabs, widths = 0, Counter()
    prev = 0
    for line in text.splitlines()[:400]:
        if not line.strip():
            continue
        lead = len(line) - len(line.lstrip(' \t'))
        if line.startswith('\t'):
            tabs += 1
            continue
        if lead and lead != prev:
            widths[abs(lead - prev)] += 1
        prev = lead
    if tabs > sum(widths.values()):
        return 'tab'
    for w, _ in widths.most_common():
        if w in (2, 4, 3, 8):
            return w
    return None


def scan_style_and_code(root, files):
    by_ext = defaultdict(list)
    for f in files:
        if f.suffix in SOURCE_EXTS:
            by_ext[f.suffix].append(f)
    style = {}
    js_int, js_ext, java_int, py_int = Counter(), Counter(), Counter(), Counter()
    packages, path_shapes, mappings, warn_hits = Counter(), defaultdict(Counter), Counter(), []
    warn_count = Counter()
    top_dirs = {f.parts[0] for f in files if len(f.parts) > 1}
    read_count = 0
    java_texts = []
    js_calls, java_calls = Counter(), Counter()
    for ext, items in sorted(by_ext.items()):
        crlf, indents = 0, Counter()
        for i, rel in enumerate(items):
            if read_count >= MAX_READ_FILES:
                break
            text = read(root, rel)
            read_count += 1
            if text is None:
                continue
            if i < STYLE_SAMPLE_PER_EXT:
                if '\r\n' in text:
                    crlf += 1
                indents[str(indent_of(text))] += 1
            if ext in ('.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte'):
                seen = set()
                for spec in JS_IMPORT.findall(text):
                    key = resolve_js(rel, spec)
                    if key and key not in seen:
                        seen.add(key)
                        (js_int if key.startswith('@internal:') else js_ext)[key.replace('@internal:', '')] += 1
                for call in {f'{a}.{b}' for a, b in MEMBER_CALL.findall(text) if a not in GENERIC_RECEIVERS}:
                    js_calls[call] += 1
                for lit in set(JS_PATH_LITERAL.findall(text)):
                    path_shapes[lit.split('/')[1]][lit] += 1
            elif ext in ('.java', '.kt'):
                for p in JAVA_PACKAGE.findall(text):
                    packages['.'.join(p.split('.')[:3])] += 1
                java_texts.append(text)
                for recv in {a for a, _ in MEMBER_CALL.findall(text) if a not in GENERIC_RECEIVERS}:
                    java_calls[recv] += 1
                for m in JAVA_MAPPING.findall(text):
                    mappings[m] += 1
            elif ext == '.py':
                for a, b in PY_IMPORT.findall(text):
                    mod = (a or b).split('.')[0]
                    if mod in top_dirs or (root / f'{mod}.py').exists():
                        py_int[a or b] += 1
            if ext not in ('.css', '.scss'):
                for n, line in enumerate(text.splitlines(), 1):
                    m = WARN_MARK.search(line)
                    if m and len(line) < 300 and re.match(r'\s*(//|#|\*|/\*|--|<!--|{/\*)', line):
                        warn_count[m.group(1)] += 1
                        if len(warn_hits) < 60:
                            warn_hits.append(f'{rel}:{n}: {line.strip()[:140]}')
        style[ext] = {'files': len(items), 'sampled': min(len(items), STYLE_SAMPLE_PER_EXT),
                      'crlf_files': crlf, 'indent': dict(indents.most_common(4))}
    project_pkg = packages.most_common(1)[0][0] if packages else None
    if project_pkg:
        for text in java_texts:
            for imp in set(JAVA_IMPORT.findall(text)):
                if imp.startswith(project_pkg):
                    java_int[imp] += 1
    configs = sorted(str(f) for f in files if STYLE_CONFIG.match(f.name) and len(f.parts) <= 3)
    shapes = {seg: c.most_common(3) for seg, c in sorted(path_shapes.items(), key=lambda kv: -sum(kv[1].values()))[:15]}
    return {
        'style': style, 'style_configs': configs,
        'js_internal_imports': js_int.most_common(30), 'js_external_imports': js_ext.most_common(15),
        'java_project_package': project_pkg, 'java_internal_imports': java_int.most_common(30),
        'python_internal_imports': py_int.most_common(20),
        'js_member_calls': js_calls.most_common(30), 'java_receivers': java_calls.most_common(25),
        'front_path_literals': shapes, 'java_mappings': mappings.most_common(30),
        'warning_comments': {'counts': dict(warn_count.most_common()), 'samples': warn_hits},
    }


def resolve_js(rel, spec):
    """Map an import path to a repo-relative module key. Internal modules get the '@internal:' prefix."""
    if spec.startswith('.'):
        target = os.path.normpath(os.path.join(str(rel.parent), spec))
        parts = target.split('/')
        # Count a relative path and the `@/` alias for the same module once (treat src/ as `@/`)
        if 'src' in parts:
            target = '@/' + '/'.join(parts[parts.index('src') + 1:])
        return '@internal:' + re.sub(r'\.(jsx?|tsx?|vue)$', '', target)
    if spec.startswith(('@/', '~/', 'src/')):
        return '@internal:' + re.sub(r'\.(jsx?|tsx?|vue)$', '', spec)
    parts = spec.split('/')
    return '/'.join(parts[:2]) if spec.startswith('@') else parts[0]


VERSION_FILES = ['.nvmrc', '.node-version', '.tool-versions', '.python-version', '.java-version',
                 '.sdkmanrc', '.ruby-version', 'rust-toolchain', 'rust-toolchain.toml']
PORT_PATTERNS = [
    (re.compile(r'^\s*port\s*:\s*(\d{2,5})\b', re.M), 'port:'),
    (re.compile(r'server\.port\s*=\s*(\d{2,5})'), 'server.port'),
    (re.compile(r'\bport\s*:\s*(\d{2,5})\b'), 'dev server port'),
    (re.compile(r'^\s*-\s*["\']?(\d{2,5}:\d{2,5})["\']?\s*$', re.M), 'compose ports'),
    (re.compile(r'^\s*PORT\s*=\s*(\d{2,5})', re.M), 'PORT='),
]
PROXY_TARGET = re.compile(r'target\s*:\s*[\'"]([^\'"]+)[\'"]')
CONFIG_FILE = re.compile(r'(^|/)(application[\w-]*\.(ya?ml|properties)|\.env[\w.-]*|(vite|webpack|next|nuxt)\.config\.[cm]?[jt]s|'
                         r'docker-compose[\w.-]*\.ya?ml|compose\.ya?ml|settings[\w-]*\.py|appsettings[\w.-]*\.json|config/[\w.-]+\.(json|ya?ml|toml))$')
SECRET_KEY = re.compile(r'(?i)^\s*["\']?([\w.-]*(password|passwd|pwd|(?<![a-z])pass(?![a-z])|secret|api[_-]?key|access[_-]?key|token|private[_-]?key)[\w.-]*)["\']?\s*[:=]\s*["\']?([^\s"\'#,]+)')
# Skip keys that hold a name or format rather than a secret (tokenName, secretHeader, ...)
NAME_LIKE_KEY = re.compile(r'(?i)(name|header|type|url|uri|path|expire[sd]?|expiration|validity|length|prefix|enabled)$')
SPRING_DEFAULT = re.compile(r'^\$\{[\w.-]+:([^}]*)\}')
PLACEHOLDER = re.compile(r'^(\$\{|<|\{\{|%|changeme|change-me|your[_-]|xxx|\*+$|null$|none$|true$|false$|""$|\'\'$)', re.I)


def scan_env(root, files):
    """Collect runtime facts (versions, ports, profiles, proxies) and locations of plaintext secrets in tracked config files. Secret values are never output."""
    versions, ports, proxies, profiles, secrets = {}, [], [], set(), []
    for name in VERSION_FILES:
        p = root / name
        if p.is_file():
            versions[name] = p.read_text(errors='replace').strip().splitlines()[0][:60] if p.stat().st_size else ''
    for wrapper in root.glob('**/gradle/wrapper/gradle-wrapper.properties'):
        if any(part in SKIP_DIRS for part in wrapper.relative_to(root).parts):
            continue
        m = re.search(r'gradle-([\d.]+)-', wrapper.read_text(errors='replace'))
        if m:
            versions[str(wrapper.relative_to(root))] = f'Gradle {m.group(1)}'
    for wrapper in root.glob('**/.mvn/wrapper/maven-wrapper.properties'):
        m = re.search(r'apache-maven-([\d.]+)', wrapper.read_text(errors='replace'))
        if m:
            versions[str(wrapper.relative_to(root))] = f'Maven {m.group(1)}'
    dc = root / '.devcontainer' / 'devcontainer.json'
    if dc.is_file():
        m = re.search(r'"image"\s*:\s*"([^"]+)"', dc.read_text(errors='replace'))
        if m:
            versions['.devcontainer/devcontainer.json'] = m.group(1)
    for f in files:
        name = f.name
        if name == 'Dockerfile' and len(f.parts) <= 3:
            froms = re.findall(r'^FROM\s+(\S+)', read(root, f) or '', re.M)
            if froms:
                versions[str(f)] = ' → '.join(froms[:3])
        m = re.match(r'application-([\w]+)\.(ya?ml|properties)$', name)
        if m:
            profiles.add(m.group(1))
    tracked = set((run(['git', 'ls-files'], root) or '').splitlines())
    for f in files:
        name = f.name
        if not CONFIG_FILE.search(str(f)):
            continue
        text = read(root, f) or ''
        is_js = bool(re.search(r'\.[cm]?[jt]s$', name))
        for pat, label in PORT_PATTERNS:
            if (label == 'dev server port') != is_js and label in ('dev server port', 'port:'):
                continue
            for v in list(dict.fromkeys(pat.findall(text)))[:5]:
                ports.append(f'{f}: {label} {v}')
        for t in list(dict.fromkeys(PROXY_TARGET.findall(text)))[:5]:
            proxies.append(f'{f}: {SECRET_IN_URL.sub("//", t)}')
        m = re.search(r'profiles\.active\s*[:=]\s*([\w,${}:-]+)', text) or re.search(r'active\s*:\s*([\w,${}:-]+)', text)
        if m and 'application' in name:
            profiles.add(f'active={m.group(1)}')
        if str(f) in tracked and not name.endswith(('.example', '.sample', '.template')):
            for n, line in enumerate(text.splitlines(), 1):
                sm = SECRET_KEY.match(line)
                if not sm or NAME_LIKE_KEY.search(sm.group(1)):
                    continue
                value = sm.group(3)
                default = SPRING_DEFAULT.match(value)
                if default:
                    # A plaintext default in ${ENV:default} is also a secret left in the repo
                    value = default.group(1)
                    where = '(default · may be a dev value)'
                else:
                    where = ''
                if value and not PLACEHOLDER.match(value) and len(value) >= 4:
                    secrets.append(f'{f}:{n} `{sm.group(1)}`{where}')
    return {'versions': versions, 'ports': ports[:20], 'proxy_targets': proxies[:10],
            'profiles': sorted(profiles), 'tracked_plain_secrets': secrets[:30]}


def scan_git(root, since):
    if run(['git', 'rev-parse', '--is-inside-work-tree'], root) is None:
        return {'available': False}
    remotes = sorted({SECRET_IN_URL.sub('//', l.split()[1]) for l in (run(['git', 'remote', '-v'], root) or '').splitlines() if l.split()})
    host_kind = 'gitlab' if any('gitlab' in r for r in remotes) else 'github' if any('github' in r for r in remotes) \
        else 'bitbucket' if any('bitbucket' in r for r in remotes) else ('other' if remotes else 'none')
    if host_kind in ('other', 'none'):
        # If the remote URL doesn't tell, infer the host from the CI config
        if (root / '.gitlab-ci.yml').exists():
            host_kind = 'gitlab (inferred from CI config)'
        elif (root / '.github' / 'workflows').is_dir():
            host_kind = 'github (inferred from CI config)'
    remote_names = set((run(['git', 'remote'], root) or '').split())
    branches = [b for b in (run(['git', 'branch', '-a', '--format=%(refname:short)'], root) or '').split()
                if b not in remote_names and not b.endswith('/HEAD')]
    rng = []
    if since:
        # With a bare date git uses the current time of day and drops same-day commits, so pin it to midnight
        rng = [f'--since={since}T00:00:00'] if re.match(r'\d{4}-\d{2}-\d{2}$', since) else [f'{since}..HEAD']
    log = run(['git', 'log', '--no-merges', f'-n{HISTORY_LIMIT}', '--date=short', '--name-only',
               '--format=%x1e%h%x1f%ad%x1f%s%x1f%b%x1d'] + rng, root) or ''
    commits = []
    for chunk in log.split('\x1e')[1:]:
        head, _, names = chunk.partition('\x1d')
        h, d, s, b = (head.split('\x1f') + ['', '', '', ''])[:4]
        commits.append({'hash': h, 'date': d, 'subject': s, 'body': b,
                        'files': [n for n in names.strip().splitlines() if n]})
    types, scopes, trailers = Counter(), Counter(), Counter()
    conv = hangul = 0
    hot_files, hot_dirs, churn = Counter(), Counter(), Counter()
    fixes, doc_commits = [], []
    for c in commits:
        m = CONVENTIONAL.match(c['subject'])
        if m:
            conv += 1
            types[m.group(1)] += 1
            if m.group(2):
                scopes[m.group(2)] += 1
        if HANGUL.search(c['subject']):
            hangul += 1
        for t in re.findall(r'^([A-Z][\w-]+-by):', c['body'], re.M):
            trailers[t] += 1
        for f in c['files']:
            if (root / f).exists():
                churn[f] += 1
        if FIX_SUBJECT.search(c['subject']):
            fixes.append(f"{c['hash']} {c['date']} {c['subject']}")
            for f in c['files']:
                hot_files[f] += 1
                hot_dirs[str(Path(f).parent)] += 1
        if any(re.search(r'(^docs/|CLAUDE\.md|AGENTS\.md|CONTRIBUTING|rules)', f) for f in c['files']):
            doc_commits.append(f"{c['hash']} {c['date']} {c['subject']}")
    merge_subjects = (run(['git', 'log', '--merges', '-n300', '--format=%s'], root) or '').splitlines()
    merge_into = Counter()
    for subj in merge_subjects:
        m = re.search(r"into '?([\w./-]+)'?", subj)
        if m:
            merge_into[m.group(1)] += 1
        elif re.match(r"Merge (branch|pull request|remote-tracking branch)", subj):
            merge_into['(default branch)'] += 1
    shallow = (run(['git', 'rev-parse', '--is-shallow-repository'], root) or '').strip() == 'true'
    total = run(['git', 'rev-list', '--count', 'HEAD'], root)
    merges = run(['git', 'rev-list', '--merges', '--count', 'HEAD'], root)
    n = len(commits)
    return {
        'available': True, 'remotes': remotes, 'host_kind': host_kind, 'shallow': shallow,
        'branches': branches[:40], 'total_commits': int(total) if total else None,
        'merge_commits': int(merges) if merges else None, 'merge_into': merge_into.most_common(6),
        'analyzed_commits': len(commits),
        'since': since, 'conventional_ratio': round(conv / n, 2) if n else None,
        'hangul_subject_ratio': round(hangul / n, 2) if n else None,
        'types': types.most_common(10), 'scopes': scopes.most_common(12), 'trailers': dict(trailers),
        'subject_samples': [c['subject'] for c in commits[:12]],
        'fix_commits': fixes[:50], 'fix_hot_files': hot_files.most_common(20),
        'fix_hot_dirs': hot_dirs.most_common(12), 'churn_files': churn.most_common(15),
        'doc_commits': doc_commits[:30],
    }


def to_markdown(r):
    out = [f"# Repository fingerprint: {r['root']}", '']
    if r['walk_truncated']:
        out.append(f'> More than {MAX_WALK_FILES} files; only part was scanned. Rerun on a subfolder if needed.\n')
    out.append('## Layout')
    for m in r['manifests']:
        extra = {k: v for k, v in m.items() if k not in ('path', 'kind') and v}
        out.append(f"- `{m['path']}` ({m['kind']}) {json.dumps(extra, ensure_ascii=False) if extra else ''}")
    out.append(f"- Top extensions: {', '.join(f'{e} {c}' for e, c in r['ext_counts'])}")
    out.append('\n## CI')
    for f, lines in r['ci'].items():
        out.append(f'- `{f}`: ' + ' / '.join(lines[:8]))
    if not r['ci']:
        out.append('- none')
    d = r['db']
    out.append('\n## DB traces')
    mapper = f" · SQL mappers (MyBatis) {d['mybatis_mappers']} {d['mapper_roots']}" if d['mybatis_mappers'] else ''
    out.append(f"- SQL files {d['sql_files']} {d['sql_dirs'][:5]} · ORM entities {d['orm_entities']}{mapper}")
    out.append(f"- Init scripts {d['init_scripts'] or 'none'}")
    out.append(f"- Migration folders {d['migration_dirs'] or 'none'} · DB kinds in config {d['db_kinds_in_config'] or 'none'}")
    a = r['ai_config']
    out.append('\n## Existing rules and AI config')
    out.append(f"- Present: {a['present'] or 'none'} · .mcp.json {'yes' if a['has_mcp_json'] else 'no'}")
    for k, v in a['detail'].items():
        out.append(f'- `{k}`: {v}')
    out.append(f"- Related .gitignore lines: {a['gitignore_lines'] or 'none'}")
    out.append(f"- docs/ top level: {a['docs_top'] or 'none'} · Tracked docs/ files {a['docs_tracked'] if a['docs_tracked'] is not None else 'unknown'}")
    e = r['env']
    out.append('\n## Runtime environment (from config files · not verified by running)')
    out.append(f"- Versions: {e['versions'] or 'none'}")
    out.append(f"- Profiles: {e['profiles'] or 'none'}")
    out.append('- Ports: ' + (' · '.join(e['ports']) if e['ports'] else 'none'))
    out.append('- Proxy targets: ' + (' · '.join(e['proxy_targets']) if e['proxy_targets'] else 'none'))
    if e['tracked_plain_secrets']:
        out.append(f"- ⚠ Possible plaintext secrets in Git-tracked config files: {len(e['tracked_plain_secrets'])} (values not shown): "
                   + ', '.join(e['tracked_plain_secrets'][:12]))
    c = r['code']
    out.append('\n## Code style')
    for ext, s in c['style'].items():
        out.append(f"- `{ext}` {s['files']} files · indent {s['indent']} · CRLF {s['crlf_files']}/{s['sampled']} (sampled)")
    out.append(f"- Style configs: {c['style_configs'] or 'none'}")
    out.append('\n## Most-used internal modules (S1 candidates, by file count)')
    for title, key in (('JS internal', 'js_internal_imports'), ('Java internal', 'java_internal_imports'),
                       ('Python internal', 'python_internal_imports'), ('JS external', 'js_external_imports')):
        if c[key]:
            out.append(f'- {title}: ' + ', '.join(f'`{m}` {n}' for m, n in c[key][:20]))
    if c['js_member_calls']:
        out.append('- JS calls (receiver.method): ' + ', '.join(f'`{m}` {n}' for m, n in c['js_member_calls'][:20]))
    if c['java_receivers']:
        out.append('- Call receivers (Java: injected fields, shared classes): ' + ', '.join(f'`{m}` {n}' for m, n in c['java_receivers'][:20]))
    out.append('\n## Path shapes (S2 candidates)')
    for seg, items in c['front_path_literals'].items():
        out.append(f'- `/{seg}/…`: ' + ', '.join(f'`{p}` {n}' for p, n in items))
    if c['java_mappings']:
        out.append('- Java mappings: ' + ', '.join(f'`{p}` {n}' for p, n in c['java_mappings'][:20]))
    w = c['warning_comments']
    out.append(f"\n## Warning comments (S3 candidates) {w['counts']}")
    out.extend(f'- {s}' for s in w['samples'][:30])
    g = r['git']
    out.append('\n## Git')
    if not g.get('available'):
        out.append('- not a git repository, or git is unavailable')
    else:
        out.append(f"- Remotes {g['remotes']} ({g['host_kind']}) · branches {g['branches'][:15]}")
        if g.get('shallow'):
            out.append('- ⚠ Shallow clone: commit counts and repetitions are lower than the full history')
        out.append(f"- Commits {g['total_commits']} (merge {g['merge_commits']}, Merge targets {g['merge_into'] or 'none'}) · analyzed {g['analyzed_commits']}"
                   f"{' · since ' + g['since'] if g['since'] else ''}")
        na = lambda v: 'n/a' if v is None else v
        out.append(f"- conventional ratio {na(g['conventional_ratio'])} · Korean-subject ratio {na(g['hangul_subject_ratio'])}"
                   f" · type {g['types']} · scope {g['scopes']} · trailers {g['trailers'] or 'none'}")
        out.append('- Subject samples: ' + ' | '.join(g['subject_samples'][:8]))
        out.append(f"\n### Fix commits: {len(g['fix_commits'])} (S3 candidates)")
        out.extend(f'- {s}' for s in g['fix_commits'][:30])
        mark = lambda f: ' (archive?)' if ARCHIVE_DIR.search(f) else ''
        out.append('- Fix hotspots (files): ' + ', '.join(f'`{f}` {n}{mark(f)}' for f, n in g['fix_hot_files'][:12]))
        out.append('- Fix hotspots (folders): ' + ', '.join(f'`{f}` {n}{mark(f)}' for f, n in g['fix_hot_dirs'][:8]))
        out.append('- Most-changed files: ' + ', '.join(f'`{f}` {n}' for f, n in g['churn_files'][:10]))
        out.append(f"\n### Rule and doc commits: {len(g['doc_commits'])} (how the rules grew)")
        out.extend(f'- {s}' for s in g['doc_commits'][:20])
    return '\n'.join(out)


def main(argv):
    args = argv[1:]
    if args and args[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    if not args:
        print(__doc__)
        return 2
    root = Path(args[0]).expanduser().resolve()
    if not root.is_dir():
        print(f'not a repository root: {root}; check the path and rerun.', file=sys.stderr)
        return 2
    since = args[args.index('--since') + 1] if '--since' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else None
    files, truncated = walk(root)
    result = {
        'root': str(root), 'walk_truncated': truncated, 'file_count': len(files),
        'ext_counts': Counter(f.suffix or f.name for f in files
                              if (f.suffix or f.name) not in ASSET_EXTS).most_common(15),
        'manifests': scan_manifests(root, files), 'ci': scan_ci(root, files),
        'db': scan_db(root, files), 'ai_config': scan_ai_config(root, files),
        'code': scan_style_and_code(root, files), 'env': scan_env(root, files), 'git': scan_git(root, since),
    }
    if out:
        Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(to_markdown(result))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
