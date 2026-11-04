"""저장소의 지문(구성·관례·이력)을 모아 핀포인트 분석의 출발점을 만든다. 파일은 고치지 않는다.

사용: python3 -I scan_repo.py <저장소 루트> [--since <YYYY-MM-DD | 커밋>] [--out <결과.json>]
- 표준 출력: 사람이 읽을 요약(Markdown). --out 에는 전체 결과를 JSON으로 쓴다.
- --since 를 주면 이력 항목(fix 커밋·핫스팟·문서 커밋)을 그 이후로 한정한다(갱신 모드).
필요: Python 3.8 이상. git 이 없거나 저장소가 아니면 이력 항목만 건너뛴다.
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 생성물·의존성·도구 폴더는 프로젝트 관례가 아니므로 건너뛴다
SKIP_DIRS = {
    '.git', 'node_modules', 'build', 'dist', 'out', 'target', '.gradle', '.idea', '.vscode',
    'vendor', 'venv', '.venv', '__pycache__', 'coverage', '.next', '.nuxt', 'bin', 'obj',
    'logs', '.claude', '.codex', '.agents', '.cache', 'tmp',
}
# 아주 큰 저장소에서도 1~2분 안에 끝나도록 읽는 파일 수를 제한한다
MAX_WALK_FILES = 40000
MAX_READ_FILES = 15000
MAX_READ_BYTES = 1024 * 1024
STYLE_SAMPLE_PER_EXT = 300
# fix 커밋 핫스팟은 최근 이력이 의미 있으므로 이 개수까지만 본다
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
# package.json 에서 구조 판단에 쓰는 의존성(버전을 함께 보여 준다)
NODE_HINTS = re.compile(
    r'^(react|react-dom|react-router-dom|vue|nuxt|next|@angular/core|svelte|vite|webpack|typescript|'
    r'eslint|prettier|jest|vitest|axios|redux|@reduxjs/toolkit|zustand|@tanstack/react-query|'
    r'tailwindcss|express|@nestjs/core|@syncfusion/.+|ag-grid.*|antd|@mui/material|electron)$')
# 빌드 설정에 들어 있는 포맷·정적 검사 도구 — "린터가 이미 막는 것"을 판단하는 근거다
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
# 작성자가 남긴 주의 표시는 사고·함정의 흔적이다(S3 후보)
WARN_MARK = re.compile(r'(주의|반드시|금지|하지 말 것|하지 않는다|절대|IMPORTANT|WARNING|CAUTION|HACK|FIXME|XXX|'
                       r"[Dd]on't|[Dd]o not|[Mm]ust not|[Nn]ever |[Nn]eeds to stay|[Kk]eep in sync|[Cc]areful)")
# 결함 수정 커밋은 'fix' 외의 동사로도 쓴다(Prevent HTTP 500…, Validate…, Mitigate…)
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
# 확장자 순위에서 뺄 자산·생성물(관례 판단에 쓸모없다)
ASSET_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.woff', '.woff2', '.ttf', '.eot',
              '.otf', '.rels', '.map', '.lock', '.DS_Store', '.pdf', '.zip', '.jar', '.class', '.mp4', '.mp3'}
# 보관본·예전 코드 폴더. fix 핫스팟에 나오면 근거로 쓰지 않도록 표시한다
ARCHIVE_DIR = re.compile(r'(^|/)(archive|archived|old|deprecated|legacy|backup)(/|$)', re.I)
# 주입 필드·공통 객체는 import 로 안 잡히므로 `수신자.메서드(` 호출을 파일 수로 센다(S1·S2 후보)
MEMBER_CALL = re.compile(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(')
# 언어 내장·지역 변수로 흔한 수신자는 프로젝트 관례가 아니므로 뺀다
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
    """파일의 들여쓰기 단위를 추정한다: 'tab' | 2 | 4 | 기타 숫자 | None."""
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
    """import 경로를 저장소 기준 모듈 키로 바꾼다. 내부 모듈은 '@internal:' 접두어를 붙인다."""
    if spec.startswith('.'):
        target = os.path.normpath(os.path.join(str(rel.parent), spec))
        parts = target.split('/')
        # 상대 경로와 `@/` 별칭이 같은 모듈을 가리키면 하나로 센다(src 아래를 `@/` 로 본다)
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
# 비밀값이 아니라 이름·형식을 담는 키(tokenName, secretHeader 등)는 뺀다
NAME_LIKE_KEY = re.compile(r'(?i)(name|header|type|url|uri|path|expire[sd]?|expiration|validity|length|prefix|enabled)$')
SPRING_DEFAULT = re.compile(r'^\$\{[\w.-]+:([^}]*)\}')
PLACEHOLDER = re.compile(r'^(\$\{|<|\{\{|%|changeme|change-me|your[_-]|xxx|\*+$|null$|none$|true$|false$|""$|\'\'$)', re.I)


def scan_env(root, files):
    """실행 환경 사실(버전·포트·프로필·프록시)과 추적 중인 설정 파일의 평문 비밀값 위치를 모은다. 값은 비밀값이면 출력하지 않는다."""
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
                    # ${ENV:기본값} 의 기본값이 평문이면 그것도 저장소에 남은 비밀값이다
                    value = default.group(1)
                    where = '(기본값 · 개발용 값일 수 있음)'
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
        # 원격 주소로 못 정하면 CI 설정으로 추정한다
        if (root / '.gitlab-ci.yml').exists():
            host_kind = 'gitlab(CI 설정으로 추정)'
        elif (root / '.github' / 'workflows').is_dir():
            host_kind = 'github(CI 설정으로 추정)'
    remote_names = set((run(['git', 'remote'], root) or '').split())
    branches = [b for b in (run(['git', 'branch', '-a', '--format=%(refname:short)'], root) or '').split()
                if b not in remote_names and not b.endswith('/HEAD')]
    rng = []
    if since:
        # 날짜만 주면 git 이 그날의 현재 시각을 써서 같은 날 커밋이 빠진다 — 0시로 고정한다
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
            merge_into['(기본 브랜치)'] += 1
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
    out = [f"# 저장소 지문: {r['root']}", '']
    if r['walk_truncated']:
        out.append(f'> 파일이 {MAX_WALK_FILES}개를 넘어 일부만 보았다. 하위 폴더를 따로 지정해 다시 실행할 수 있다.\n')
    out.append('## 구성')
    for m in r['manifests']:
        extra = {k: v for k, v in m.items() if k not in ('path', 'kind') and v}
        out.append(f"- `{m['path']}` ({m['kind']}) {json.dumps(extra, ensure_ascii=False) if extra else ''}")
    out.append(f"- 확장자 상위: {', '.join(f'{e} {c}' for e, c in r['ext_counts'])}")
    out.append('\n## CI')
    for f, lines in r['ci'].items():
        out.append(f'- `{f}`: ' + ' / '.join(lines[:8]))
    if not r['ci']:
        out.append('- 없음')
    d = r['db']
    out.append('\n## DB 흔적')
    mapper = f" · SQL 매퍼(MyBatis) {d['mybatis_mappers']}개 {d['mapper_roots']}" if d['mybatis_mappers'] else ''
    out.append(f"- SQL 파일 {d['sql_files']}개 {d['sql_dirs'][:5]} · ORM 엔티티 {d['orm_entities']}개{mapper}")
    out.append(f"- 초기화 스크립트 {d['init_scripts'] or '없음'}")
    out.append(f"- 마이그레이션 폴더 {d['migration_dirs'] or '없음'} · 설정의 DB 종류 {d['db_kinds_in_config'] or '없음'}")
    a = r['ai_config']
    out.append('\n## 기존 규칙·AI 설정')
    out.append(f"- 있는 파일: {a['present'] or '없음'} · .mcp.json {'있음' if a['has_mcp_json'] else '없음'}")
    for k, v in a['detail'].items():
        out.append(f'- `{k}`: {v}')
    out.append(f"- .gitignore 관련 줄: {a['gitignore_lines'] or '없음'}")
    out.append(f"- docs/ 최상위: {a['docs_top'] or '없음'} · docs/ 추적 파일 {a['docs_tracked'] if a['docs_tracked'] is not None else '알 수 없음'}개")
    e = r['env']
    out.append('\n## 실행 환경 (설정 파일 기준 · 실제 실행은 미확인)')
    out.append(f"- 버전: {e['versions'] or '없음'}")
    out.append(f"- 프로필: {e['profiles'] or '없음'}")
    out.append('- 포트: ' + (' · '.join(e['ports']) if e['ports'] else '없음'))
    out.append('- 프록시 대상: ' + (' · '.join(e['proxy_targets']) if e['proxy_targets'] else '없음'))
    if e['tracked_plain_secrets']:
        out.append(f"- ⚠ Git 추적 설정 파일의 평문 비밀값 의심 {len(e['tracked_plain_secrets'])}곳(값은 출력하지 않음): "
                   + ', '.join(e['tracked_plain_secrets'][:12]))
    c = r['code']
    out.append('\n## 코드 스타일')
    for ext, s in c['style'].items():
        out.append(f"- `{ext}` {s['files']}개 · 들여쓰기 {s['indent']} · CRLF {s['crlf_files']}/{s['sampled']}(표본)")
    out.append(f"- 스타일 설정: {c['style_configs'] or '없음'}")
    out.append('\n## 많이 쓰는 내부 모듈 (S1 후보: 파일 수 기준)')
    for title, key in (('JS 내부', 'js_internal_imports'), ('Java 내부', 'java_internal_imports'),
                       ('Python 내부', 'python_internal_imports'), ('JS 외부', 'js_external_imports')):
        if c[key]:
            out.append(f'- {title}: ' + ', '.join(f'`{m}` {n}' for m, n in c[key][:20]))
    if c['js_member_calls']:
        out.append('- JS 호출(수신자.메서드): ' + ', '.join(f'`{m}` {n}' for m, n in c['js_member_calls'][:20]))
    if c['java_receivers']:
        out.append('- Java 호출 수신자(주입 필드·공통 클래스): ' + ', '.join(f'`{m}` {n}' for m, n in c['java_receivers'][:20]))
    out.append('\n## 경로 모양 (S2 후보)')
    for seg, items in c['front_path_literals'].items():
        out.append(f'- `/{seg}/…`: ' + ', '.join(f'`{p}` {n}' for p, n in items))
    if c['java_mappings']:
        out.append('- Java 매핑: ' + ', '.join(f'`{p}` {n}' for p, n in c['java_mappings'][:20]))
    w = c['warning_comments']
    out.append(f"\n## 주의 주석 (S3 후보) {w['counts']}")
    out.extend(f'- {s}' for s in w['samples'][:30])
    g = r['git']
    out.append('\n## Git')
    if not g.get('available'):
        out.append('- git 저장소가 아니거나 git 이 없다')
    else:
        out.append(f"- 원격 {g['remotes']} ({g['host_kind']}) · 브랜치 {g['branches'][:15]}")
        if g.get('shallow'):
            out.append('- ⚠ 얕은 복제(shallow) — 커밋 수·반복 횟수가 전체 이력보다 적게 나온다')
        out.append(f"- 커밋 {g['total_commits']} (merge {g['merge_commits']}, 합쳐진 대상 {g['merge_into'] or '없음'}) · 분석 {g['analyzed_commits']}"
                   f"{' · since ' + g['since'] if g['since'] else ''}")
        na = lambda v: 'n/a' if v is None else v
        out.append(f"- conventional 비율 {na(g['conventional_ratio'])} · 한글 제목 비율 {na(g['hangul_subject_ratio'])}"
                   f" · type {g['types']} · scope {g['scopes']} · 트레일러 {g['trailers'] or '없음'}")
        out.append('- 제목 예: ' + ' | '.join(g['subject_samples'][:8]))
        out.append(f"\n### fix 커밋 {len(g['fix_commits'])}개 (S3 후보)")
        out.extend(f'- {s}' for s in g['fix_commits'][:30])
        mark = lambda f: ' (보관본?)' if ARCHIVE_DIR.search(f) else ''
        out.append('- fix 핫스팟 파일: ' + ', '.join(f'`{f}` {n}{mark(f)}' for f, n in g['fix_hot_files'][:12]))
        out.append('- fix 핫스팟 폴더: ' + ', '.join(f'`{f}` {n}{mark(f)}' for f, n in g['fix_hot_dirs'][:8]))
        out.append('- 변경 많은 파일: ' + ', '.join(f'`{f}` {n}' for f, n in g['churn_files'][:10]))
        out.append(f"\n### 규칙·문서 커밋 {len(g['doc_commits'])}개 (규칙이 자란 기록)")
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
        print(f'저장소 루트가 아니다: {root} — 경로를 확인해 다시 실행한다.', file=sys.stderr)
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
