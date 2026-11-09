"""List candidate check commands (lint, type, build, test) in a repository. Runs nothing.

Usage: python3 -I discover.py <repo root>
Output: a subproject · kind · command · evidence table. Server-start, deploy and autofix commands are listed separately as excluded.
Requires: Python 3.8+ (below 3.11, pyproject tool settings are only found by text search).
"""
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', 'build', 'dist', 'out', 'target', '.gradle', 'vendor', 'venv',
             '.venv', '__pycache__', '.claude', '.next', '.nuxt', 'coverage'}
MAX_DEPTH = 3
# Kind is decided by the package.json script name. Start, deploy and autofix are not checks, so they go to the excluded list
KIND_BY_SCRIPT = [
    ('lint', re.compile(r'^(lint|eslint|stylelint)(:.*)?$')),
    ('type', re.compile(r'^(typecheck|type-check|tsc|check-types|types)(:.*)?$')),
    ('build', re.compile(r'^build(:.*)?$')),
    ('test', re.compile(r'^(test|unit|e2e|vitest|jest)(:.*)?$')),
]
EXCLUDE_SCRIPT = re.compile(r'^(dev|start|serve|preview|watch|deploy|release|publish|prepare|postinstall|format|fix|lint:fix|.*:fix|.*:watch)$')
MAKE_TARGETS = re.compile(r'^(lint|check|test|build|typecheck|vet)\s*:', re.M)


def find(root, names):
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if len(rel.parts) > MAX_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.'))
        for n in filenames:
            if n in names:
                yield rel, n


def node(root, rel, rows, excluded):
    try:
        pkg = json.loads((root / rel / 'package.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return
    lock = 'npm'
    if (root / rel / 'pnpm-lock.yaml').exists():
        lock = 'pnpm'
    elif (root / rel / 'yarn.lock').exists():
        lock = 'yarn'
    elif (root / rel / 'bun.lockb').exists() or (root / rel / 'bun.lock').exists():
        lock = 'bun'
    has_modules = (root / rel / 'node_modules').is_dir()
    for name, body in sorted(pkg.get('scripts', {}).items()):
        cmd = f'{lock} run {name}'
        if EXCLUDE_SCRIPT.match(name):
            excluded.append((str(rel), cmd, 'start/deploy/autofix'))
            continue
        for kind, pat in KIND_BY_SCRIPT:
            if pat.match(name):
                note = f'package.json scripts.{name} = {body[:60]}'
                if not has_modules:
                    note += ' · no node_modules (install only after the user confirms)'
                rows.append((str(rel), kind, cmd, note))
                break
    if 'typescript' in {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})} \
            and not any(r[0] == str(rel) and r[1] == 'type' for r in rows):
        rows.append((str(rel), 'type', 'npx tsc --noEmit', 'typescript dependency · no type-check script'))


def gradle(root, rel, rows, excluded):
    wrapper = './gradlew' if (root / rel / 'gradlew').exists() else 'gradle'
    text = ''.join((root / rel / n).read_text(errors='replace') for n in ('build.gradle', 'build.gradle.kts')
                   if (root / rel / n).exists())
    for marker, task in (('spring-javaformat', 'checkFormat'), ('checkstyle', 'checkstyleMain'),
                         ('spotless', 'spotlessCheck'), ('ktlint', 'ktlintCheck'), ('detekt', 'detekt')):
        if marker in text:
            rows.append((str(rel), 'lint', f'{wrapper} --no-daemon {task}', f'{marker} in build.gradle'))
    rows.append((str(rel), 'build', f'{wrapper} --no-daemon compileJava', 'build.gradle'))
    rows.append((str(rel), 'test', f'{wrapper} --no-daemon test', 'build.gradle · first check whether tests need a DB or other external service'))
    excluded.append((str(rel), f'{wrapper} bootRun', 'server start'))


def maven(root, rel, rows, excluded):
    mvn = './mvnw' if (root / rel / 'mvnw').exists() else 'mvn'
    text = (root / rel / 'pom.xml').read_text(errors='replace')
    for marker, goal in (('spring-javaformat', 'spring-javaformat:validate'), ('maven-checkstyle-plugin', 'checkstyle:check'),
                         ('spotless', 'spotless:check'), ('nohttp', 'validate')):
        if marker in text:
            rows.append((str(rel), 'lint', f'{mvn} -q {goal}', f'{marker} in pom.xml'))
    rows.append((str(rel), 'build', f'{mvn} -q compile', 'pom.xml'))
    rows.append((str(rel), 'test', f'{mvn} -q test', 'pom.xml · first check whether tests need external services'))
    excluded.append((str(rel), f'{mvn} spring-boot:run', 'server start'))


def python(root, rel, rows, excluded):
    text = ''
    for n in ('pyproject.toml', 'setup.cfg', 'tox.ini'):
        p = root / rel / n
        if p.exists():
            text += p.read_text(encoding='utf-8', errors='replace')
    if 'ruff' in text or (root / rel / 'ruff.toml').exists():
        rows.append((str(rel), 'lint', 'ruff check <files>', 'ruff config'))
    if 'mypy' in text:
        rows.append((str(rel), 'type', 'mypy <path>', 'mypy config'))
    if 'pytest' in text or (root / rel / 'tests').is_dir():
        rows.append((str(rel), 'test', 'pytest <path>', 'pytest config or tests/'))


def go(root, rel, rows, excluded):
    rows.append((str(rel), 'lint', 'go vet ./...', 'go.mod'))
    rows.append((str(rel), 'build', 'go build ./...', 'go.mod'))
    rows.append((str(rel), 'test', 'go test ./...', 'go.mod'))


def rust(root, rel, rows, excluded):
    rows.append((str(rel), 'lint', 'cargo clippy', 'Cargo.toml'))
    rows.append((str(rel), 'build', 'cargo check', 'Cargo.toml'))
    rows.append((str(rel), 'test', 'cargo test', 'Cargo.toml'))


def make(root, rel, rows, excluded):
    text = (root / rel / 'Makefile').read_text(encoding='utf-8', errors='replace')
    for target in sorted(set(MAKE_TARGETS.findall(text))):
        rows.append((str(rel), 'lint' if target in ('lint', 'vet', 'check') else target if target in ('test', 'build') else 'type',
                     f'make {target}', 'Makefile target'))


def ci_commands(path):
    """Extract command lines from a CI file (GitHub `run:`, GitLab and Bitbucket `script:` lists)."""
    try:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []
    cmds, block, block_indent = [], False, 0
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if block:
            if stripped and indent > block_indent and not stripped.endswith(':'):
                cmds.append(stripped.lstrip('- ').strip())
                continue
            block = False
        m = re.match(r'(-\s*)?run:\s*(.*)$', stripped)
        if m:
            if m.group(2) in ('|', '>', ''):
                block, block_indent = True, indent
            else:
                cmds.append(m.group(2))
            continue
        if re.match(r'(before_script|script):\s*$', stripped):
            block, block_indent = True, indent
    # Keep only check/build commands (shell control, deploy and install lines are not the baseline)
    keep = re.compile(r'\b(test|lint|build|verify|check|compile|eslint|tsc|pytest|ruff|mypy|gradlew|mvnw|mvn|gradle|'
                      r'npm|yarn|pnpm|bun|go (vet|test|build)|cargo|make)\b')
    return [c for c in dict.fromkeys(cmds) if c and c not in ('|', '>') and not c.startswith('#') and keep.search(c)]


HANDLERS = {'package.json': node, 'build.gradle': gradle, 'build.gradle.kts': gradle, 'pom.xml': maven,
            'pyproject.toml': python, 'setup.cfg': python, 'go.mod': go, 'Cargo.toml': rust, 'Makefile': make}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = Path(argv[1]).expanduser().resolve()
    if not root.is_dir():
        print(f'not a repository root: {root}', file=sys.stderr)
        return 2
    rows, excluded, seen = [], [], set()
    for rel, name in find(root, set(HANDLERS)):
        key = (rel, HANDLERS[name].__name__)
        if key in seen:
            continue
        seen.add(key)
        HANDLERS[name](root, rel, rows, excluded)
    tools = {r[2].split()[0] for r in rows}
    if {'./mvnw', 'mvn'} & tools and {'./gradlew', 'gradle'} & tools:
        print('Two build tools (Maven and Gradle). Prefer the one the CI commands below use.\n')
    ci = [p for p in ('.gitlab-ci.yml', 'bitbucket-pipelines.yml', 'Jenkinsfile', 'azure-pipelines.yml')
          if (root / p).exists()]
    ci += [str(p.relative_to(root)) for p in sorted((root / '.github' / 'workflows').glob('*.y*ml'))] \
        if (root / '.github' / 'workflows').is_dir() else []
    if not rows:
        print('No candidate check commands found. Look in the repo rules (docs/rules) and CI config, or ask the user.')
    else:
        print('| Subproject | Kind | Command | Evidence |\n|---|---|---|---|')
        for r in rows:
            print(f'| `{r[0]}` | {r[1]} | `{r[2]}` | {r[3]} |')
    if excluded:
        print('\nExcluded (not checks): ' + ', '.join(f'`{c}`({w}, {why})' for w, c, why in excluded))
    if ci:
        print('\nCommands run by CI (use as the check baseline):')
        for c in ci:
            for cmd in ci_commands(root / c)[:8]:
                print(f'- `{c}`: `{cmd}`')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
