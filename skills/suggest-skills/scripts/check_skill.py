"""스킬 폴더가 작성 원칙을 지키는지 점검한다. 파일은 고치지 않는다.

사용: python3 -I check_skill.py <스킬 폴더> [<스킬 폴더> ...]
ERROR가 하나라도 있으면 종료 코드 1.
"""
import json
import re
import sys
from pathlib import Path

# 공식 frontmatter 제약
NAME_MAX = 64
DESC_MAX = 1024
RESERVED = ('claude', 'anthropic')
# 공식 권장: SKILL.md 본문 500줄 미만
BODY_MAX_LINES = 500
# 공식 권장: 100줄 넘는 참조 파일은 맨 위에 목차
TOC_REQUIRED_LINES = 100
# 목차는 앞부분만 읽어도 보여야 하므로 제목에서 이 줄 수 안에 있어야 한다
TOC_SEARCH_LINES = 15
# 공식 권장: 평가 시나리오 최소 3개
EVALS_MIN = 3
# 무엇+언제를 담기에 이보다 짧으면 대개 언제 쓰는지가 빠져 있다(경험치, 경고만)
DESC_SHORT = 100
# 스킬 폴더에 쌓인 실행 결과·백업을 잡기 위한 기준
LARGE_FILE_BYTES = 1024 * 1024
SKIP_DIRS = {'node_modules', '.git', '__pycache__'}
ARCHIVE_SUFFIXES = ('.tgz', '.tar.gz', '.zip', '.dmp', '.tar')
STALE_WORDS = re.compile(r'아직|곧 |최근에|이번 주|이번 달|올해|처음 실행할 때')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|「[^」]*」')
FIRST_PERSON =re.compile(r'\b(I can|I will|You can)\b|저는 |제가 ')
LINK = re.compile(r'\]\(([^)\s]+)\)')
XML_TAG = re.compile(r'<[A-Za-z/][^>]*>')


class Report:
    def __init__(self, root):
        self.root = root
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))

    @property
    def errors(self):
        return sum(1 for level, _, _ in self.items if level == 'ERROR')


def walk(root):
    for path in sorted(root.rglob('*')):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def parse_frontmatter(text):
    """간단한 YAML 파서: 최상위 키와 `>-`·`|` 여러 줄 값만 다룬다."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return None, text
    try:
        end = lines.index('---', 1)
    except ValueError:
        return None, text
    meta, key = {}, None
    for line in lines[1:end]:
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            meta[key] = '' if value in ('>-', '>', '|', '|-') else value.strip('"\'')
        elif key and line.startswith((' ', '\t')):
            meta[key] = (meta[key] + ' ' + line.strip()).strip()
    return meta, '\n'.join(lines[end + 1:])


def prose_lines(text):
    """코드 펜스 밖 줄을 인라인 코드를 지운 채 (번호, 내용)으로 돌려준다."""
    inside = False
    for no, line in enumerate(text.split('\n'), 1):
        if line.lstrip().startswith('```'):
            inside = not inside
            continue
        if not inside:
            yield no, re.sub(r'`[^`]*`', '', line)


def check_frontmatter(rep, skill_md, meta):
    if meta is None:
        rep.add('ERROR', skill_md, 'frontmatter(--- ... ---)가 없다')
        return {}
    name = meta.get('name', '')
    if not name:
        rep.add('ERROR', skill_md, 'name이 없다')
    else:
        if len(name) > NAME_MAX or not re.fullmatch(r'[a-z0-9-]+', name):
            rep.add('ERROR', skill_md, f'name "{name}": {NAME_MAX}자 이하 소문자·숫자·하이픈만 쓴다')
        if any(word in name.lower() for word in RESERVED):
            rep.add('ERROR', skill_md, f'name "{name}"에 예약어(claude·anthropic)가 있다')
        if name != rep.root.name:
            rep.add('WARN', skill_md, f'name "{name}"이 폴더 이름 "{rep.root.name}"과 다르다')
    desc = meta.get('description', '')
    if not desc:
        rep.add('ERROR', skill_md, 'description이 비어 있다')
    else:
        if len(desc) > DESC_MAX:
            rep.add('ERROR', skill_md, f'description {len(desc)}자 — {DESC_MAX}자 이하로 줄인다')
        if XML_TAG.search(desc):
            rep.add('ERROR', skill_md, 'description에 XML 태그가 있다')
        if FIRST_PERSON.search(desc):
            rep.add('WARN', skill_md, 'description이 1·2인칭이다. 3인칭 서술로 쓴다')
        if len(desc) < DESC_SHORT and meta.get('disable-model-invocation') != 'true':
            rep.add('WARN', skill_md, f'description {len(desc)}자 — 언제 쓰는지(요청 표현)가 들어 있는지 확인한다')
    return meta


def check_links(rep, path, text):
    """상대 링크가 실제 파일을 가리키는지 확인하고, 가리키는 경로를 돌려준다."""
    targets = set()
    for no, line in prose_lines(text):
        for link in LINK.findall(line):
            if re.match(r'^[a-z]+:', link) or link.startswith('#'):
                continue
            target = (path.parent / link.split('#')[0]).resolve()
            if not target.exists():
                rep.add('ERROR', f'{path}:{no}', f'링크 대상이 없다: {link}')
            else:
                targets.add(target)
    return targets


def check_skill(root):
    rep = Report(root)
    skill_md = root / 'SKILL.md'
    if not skill_md.is_file():
        rep.add('ERROR', root, 'SKILL.md가 없다')
        return rep
    text = skill_md.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(text)
    meta = check_frontmatter(rep, skill_md, meta)
    body_lines = body.count('\n')
    if body_lines >= BODY_MAX_LINES:
        rep.add('ERROR', skill_md, f'본문 {body_lines}줄 — {BODY_MAX_LINES}줄 미만으로 나눈다')

    direct = check_links(rep, skill_md, text)
    for path in walk(root):
        rel = path.relative_to(root)
        size = path.stat().st_size
        if size > LARGE_FILE_BYTES or path.name.endswith(ARCHIVE_SUFFIXES):
            rep.add('WARN', rel, f'큰 파일·압축 파일({size // 1024}KB). 실행 결과·백업이면 스킬 폴더 밖으로 옮긴다')
        if path.suffix != '.md' or path == skill_md:
            continue
        md = path.read_text(encoding='utf-8')
        check_links(rep, path, md)
        covered = path.resolve() in direct or any(t.is_dir() and t in path.resolve().parents for t in direct)
        if not covered and rel.parts[0] != 'evals':
            rep.add('WARN', rel, 'SKILL.md에서 직접 링크하지 않는다(참조는 한 단계로)')
        lines = md.split('\n')
        if len(lines) > TOC_REQUIRED_LINES:
            head = '\n'.join(lines[:TOC_SEARCH_LINES])
            if not re.search(r'^(목차|## 목차|## Contents)', head, re.M):
                rep.add('WARN', rel, f'{len(lines)}줄인데 앞 {TOC_SEARCH_LINES}줄 안에 목차가 없다')

    for path in [skill_md] + [p for p in walk(root) if p.suffix == '.md' and p != skill_md]:
        content = path.read_text(encoding='utf-8')
        # 머리에 기준일이 있는 문서는 시점 표현이 그 날짜 기준이라 건너뛴다
        dated_doc = DATE.search('\n'.join(content.split('\n')[:5]))
        for no, line in prose_lines(content):
            if re.search(r'[A-Za-z0-9_]\\+[A-Za-z0-9_]+\.[a-z]{1,4}\b', line):
                rep.add('WARN', f'{path.relative_to(root)}:{no}', '백슬래시 경로. `/`로 쓴다')
            unquoted = QUOTED.sub('', line)
            if not dated_doc and not DATE.search(line) and STALE_WORDS.search(unquoted):
                rep.add('WARN', f'{path.relative_to(root)}:{no}', f'시간이 지나면 틀려질 수 있는 표현: {line.strip()[:60]}')

    evals = root / 'evals' / 'evals.json'
    auto = meta.get('disable-model-invocation') != 'true'
    if evals.is_file():
        try:
            cases = json.loads(evals.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            rep.add('ERROR', 'evals/evals.json', f'JSON 오류: {e}')
        else:
            if not isinstance(cases, list) or not all(isinstance(c, dict) and c.get('query') and c.get('expected_behavior') for c in cases):
                rep.add('ERROR', 'evals/evals.json', '각 항목에 query와 expected_behavior가 있어야 한다')
            elif len(cases) < EVALS_MIN:
                rep.add('WARN', 'evals/evals.json', f'시나리오 {len(cases)}개 — {EVALS_MIN}개 이상 권장')
    elif auto:
        rep.add('WARN', root, f'evals/evals.json이 없다(시나리오 {EVALS_MIN}개 이상 권장)')
    return rep


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    total_errors = 0
    for arg in argv:
        root = Path(arg).expanduser().resolve()
        if not root.is_dir():
            print(f'== {arg}\n  ERROR  ' + ('경로가 없다' if not Path(arg).exists() else '폴더가 아니다'))
            total_errors += 1
            continue
        rep = check_skill(root)
        print(f'== {root}')
        if not rep.items:
            print('  OK')
        for level, where, msg in rep.items:
            print(f'  {level:5}  {where}: {msg}')
        total_errors += rep.errors
    return 1 if total_errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
