"""생성한 규칙·라우터·가이드·에이전트·스킬 문서를 점검한다. 파일은 고치지 않는다.

사용: python3 -I check_docs.py <저장소 루트> [--allow <식별자> ...]
  --allow: 저장소에 없어도 의도해서 쓴 식별자(외부 도구·제품·표준 이름)를 근거 검사에서 뺀다.

검사 대상: CLAUDE.md · docs/rules/*.md · docs/guide/*.md · .claude/agents/*.md · .claude/skills/*/*.md
검사 항목:
  ERROR  깨진 상대 링크 · 비밀값 형태 · 채우지 않은 템플릿 빈칸 `{{…}}` · 에이전트 frontmatter 누락
  WARN   규칙 문서의 코드 표기(`…`) 중 저장소에서 근거를 찾지 못한 식별자 · 길이 초과 · 쓰기 도구가 있는 에이전트
         · 루트 README 에서 docs/rules·docs/guide 로 가는 깨진 링크
  INFO   `확인 필요`·`미확인`·TODO 남은 개수
ERROR 가 하나라도 있으면 종료 코드 1. 스킬 폴더 자체 점검은 suggest-skills 의 check_skill.py 로 한다.
"""
import re
import subprocess
import sys
from pathlib import Path

# 라우터는 매 세션 읽히므로 짧아야 한다(원래 프로젝트 CLAUDE.md 21줄 기준, 여유를 둔 경고선)
CLAUDE_MD_WARN = 40
# 규칙 문서 하나가 이보다 길면 영역을 나누는 편이 읽기 쉽다(원래 프로젝트 최대 111줄 기준)
RULE_DOC_WARN = 150
GENERATED_GLOBS = ['CLAUDE.md', 'docs/rules/*.md', 'docs/guide/*.md', '.claude/agents/*.md',
                   '.claude/skills/*/SKILL.md', '.claude/skills/*/*.md']
# 근거 검사는 규칙 정본에만 한다(스킬·에이전트에는 명령 예시가 많아 잡음이 크다)
EVIDENCE_GLOBS = ['CLAUDE.md', 'docs/rules/*.md']
LINK = re.compile(r'\]\(([^)\s]+)\)')
FENCE = re.compile(r'```.*?```', re.S)
INLINE_CODE = re.compile(r'`([^`\n]+)`')
# 길이 제한 없이 한 줄 안의 빈칸을 모두 잡는다
SLOT = re.compile(r'\{\{[^\n]*?\}\}')
OPEN_MARKS = re.compile(r'확인 필요|미확인|TODO|TBD')
SECRETS = [
    ('AWS 액세스 키', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('개인 키', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('GitLab/GitHub 토큰', re.compile(r'\b(glpat-[\w-]{20,}|gh[pousr]_[A-Za-z0-9]{30,})')),
    ('Slack 토큰', re.compile(r'\bxox[abpr]-[\w-]{10,}')),
    ('URL 안 계정', re.compile(r'://[^/\s:@]+:[^/\s@<>{}$]+@')),
    ('비밀번호 값', re.compile(r'(?i)(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*["\']?(?![<${*]|\s|$|개별|별도|환경변수|미확인)[^\s"\'`|]{4,}')),
]
# 식별자로 볼 코드 표기: 경로·점 표기·밑줄·camelCase·접두어 형태. 공백이 있으면 명령이라 뺀다
IDENT_LIKE = re.compile(r'^[@\w./:{}*-]+$')
IDENT_SIGNAL = re.compile(r'[./_]|[a-z][A-Z]|^[A-Z]{2,}[A-Z_]*_$')
# 어느 저장소에나 쓰는 일반 표기(근거 검사 제외)
GENERIC = {
    'docs/rules', 'docs/rules/', 'docs/guide', 'docs/guide/', 'CLAUDE.md', 'CLAUDE.local.md', '.claude/',
    '.gitignore', 'README.md', 'git.md', 'common.md', 'environments.md', 'git add .', '--force', '--no-verify',
    '.claude/settings.json', '.claude/settings.local.json', '.devkit/', '.env', '.env.example', 'scratchpad',
}


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))


def collect(root, globs):
    seen = []
    for g in globs:
        for p in sorted(root.glob(g)):
            if p.is_file() and p not in seen:
                seen.append(p)
    return seen


def check_links(root, path, text, rep, level='ERROR', only_prefix=None):
    for target in LINK.findall(FENCE.sub('', text)):
        if re.match(r'^[a-z]+:', target) or target.startswith('#'):
            continue
        rel = target.split('#')[0]
        if only_prefix and not any(rel.startswith(p) for p in only_prefix):
            continue
        if rel and not (path.parent / rel).exists():
            rep.add(level, path.relative_to(root), f'깨진 링크: {target}')


def check_secrets(root, path, text, rep):
    for name, pat in SECRETS:
        for m in pat.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            rep.add('ERROR', f'{path.relative_to(root)}:{line}', f'{name} 형태 — 값을 지우고 "개별 전달"로 쓴다')


def check_agent(root, path, text, rep):
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m:
        rep.add('ERROR', path.relative_to(root), 'frontmatter 없음')
        return
    fm = m.group(1)
    for key in ('name', 'description', 'tools'):
        if not re.search(rf'^{key}:', fm, re.M):
            rep.add('ERROR', path.relative_to(root), f'frontmatter `{key}` 없음')
    tools = re.search(r'^tools:\s*(.+)$', fm, re.M)
    if tools and re.search(r'\b(Edit|Write|NotebookEdit)\b', tools.group(1)):
        rep.add('WARN', path.relative_to(root), '쓰기 도구가 있다 — 조회 담당 에이전트면 뺀다')
    if not re.search(r'^model:', fm, re.M):
        rep.add('WARN', path.relative_to(root), '`model` 없음 — 탐색 담당은 sonnet 으로 둔다')


def evidence_checker(root):
    """식별자가 저장소(규칙 문서 제외)의 경로나 내용에 있는지 본다. git 이 없으면 None."""
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                            cwd=root, capture_output=True, text=True)
    if listed.returncode != 0:
        return None
    paths = listed.stdout
    cache = {}
    excludes = [':(exclude)CLAUDE.md', ':(exclude)docs/rules', ':(exclude)docs/guide', ':(exclude).claude']

    def has(token):
        if token in cache:
            return cache[token]
        probe = token.strip('/').split('{')[0].split('*')[0].rstrip('/.:') or token
        found = probe in paths or (root / probe).exists()
        if not found and len(probe) >= 3:
            found = subprocess.run(['git', 'grep', '-q', '-F', '--untracked', probe, '--', '.'] + excludes,
                                   cwd=root, capture_output=True).returncode == 0
        if not found:
            # `User.name`·`value/onChange`·`_ID/_NO` 같은 표기는 조각이 모두 있으면 근거가 있다고 본다
            parts = [x.strip('*') for x in re.split(r'[/.]', probe) if len(x.strip('*')) >= 2]
            found = len(parts) >= 2 and all(has(x) for x in parts)
        cache[token] = found
        return found
    return has


def check_evidence(root, files, rep, allow):
    has = evidence_checker(root)
    if has is None:
        rep.add('WARN', '.', 'git 저장소가 아니라 식별자 근거 검사를 건너뛴다')
        return
    for path in files:
        text = FENCE.sub('', path.read_text(encoding='utf-8', errors='replace'))
        missing = []
        for token in dict.fromkeys(INLINE_CODE.findall(text)):
            t = token.strip()
            if t in GENERIC or t in allow or not IDENT_LIKE.match(t) or not IDENT_SIGNAL.search(t):
                continue
            if t.startswith(('http', '--', '-', '/devkit:', 'devkit:', '@/')) or SLOT.search(t) or '...' in t or '…' in t:
                continue
            if not has(t):
                missing.append(t)
        if missing:
            rep.add('WARN', path.relative_to(root),
                    f'저장소에서 근거를 찾지 못한 식별자 {len(missing)}개: {missing[:8]} — 다른 프로젝트에서 옮겼거나 오타인지 확인한다')


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0 if len(argv) >= 2 else 2
    root = Path(argv[1]).expanduser().resolve()
    allow = set(argv[argv.index('--allow') + 1:]) if '--allow' in argv else set()
    rep = Report()
    files = collect(root, GENERATED_GLOBS)
    if not files:
        print(f'점검할 문서가 없다: {root} — CLAUDE.md·docs/rules 를 만든 뒤 실행한다.')
        return 2
    open_count = 0
    for path in files:
        text = path.read_text(encoding='utf-8', errors='replace')
        rel = path.relative_to(root)
        lines = text.count('\n') + 1
        if path.name == 'CLAUDE.md' and path.parent == root and lines > CLAUDE_MD_WARN:
            rep.add('WARN', rel, f'{lines}줄 — 라우터는 표와 호출 기준만 남기고 규칙은 docs/rules 로 옮긴다')
        if 'docs/rules' in str(rel) and lines > RULE_DOC_WARN:
            rep.add('WARN', rel, f'{lines}줄 — 영역을 나누거나 예제를 별도 가이드로 옮긴다')
        check_links(root, path, text, rep)
        check_secrets(root, path, text, rep)
        if '.claude/agents' in str(rel):
            check_agent(root, path, text, rep)
        for m in SLOT.finditer(text):
            line = text.count('\n', 0, m.start()) + 1
            rep.add('ERROR', f'{rel}:{line}', f'채우지 않은 빈칸 {m.group(0)[:80]}')
        marks = OPEN_MARKS.findall(FENCE.sub('', text))
        if marks:
            open_count += len(marks)
            rep.add('INFO', rel, f'남은 표시 {len(marks)}개: {sorted(set(marks))}')
    readme = root / 'README.md'
    if readme.is_file():
        check_links(root, readme, readme.read_text(encoding='utf-8', errors='replace'), rep,
                    level='WARN', only_prefix=('docs/rules', 'docs/guide', './docs/rules', './docs/guide'))
    check_evidence(root, collect(root, EVIDENCE_GLOBS), rep, allow)
    for level in ('ERROR', 'WARN', 'INFO'):
        for lv, where, msg in rep.items:
            if lv == level:
                print(f'{lv:5} {where}: {msg}')
    errors = sum(1 for lv, _, _ in rep.items if lv == 'ERROR')
    warns = sum(1 for lv, _, _ in rep.items if lv == 'WARN')
    print(f'\n문서 {len(files)}개 · ERROR {errors} · WARN {warns} · 남은 표시 {open_count}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
