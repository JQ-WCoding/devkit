"""extract_deck.py tests with generated pptx, pdf, image and text inputs.
Usage: python3 -I skills/develop-screen/scripts/extract_deck_test.py
"""
import json
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, 'extract_deck.py')
sys.path.insert(0, HERE)
import extract_deck as ed  # noqa: E402

FAILS = []
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')


def check(name, cond, detail=''):
    print(('ok    ' if cond else 'FAIL  ') + name)
    if not cond:
        FAILS.append(name)
        print('      ' + str(detail)[:1200])


def run(*args):
    r = subprocess.run([sys.executable, '-I', SCRIPT, *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def sp(lines):
    paras = ''.join(f'<a:p><a:r><a:t>{t}</a:t></a:r></a:p>' for t in lines)
    return f'<p:sp><p:txBody>{paras}</p:txBody></p:sp>'


def make_pptx(path):
    """Two slides whose presentation order is the reverse of their file names (slide2 is p1)."""
    z = zipfile.ZipFile(path, 'w')
    z.writestr('ppt/presentation.xml', f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst>'
               '<p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>')
    z.writestr('ppt/_rels/presentation.xml.rels', f'<Relationships xmlns="{REL}">'
               f'<Relationship Id="rId1" Type="{R}/slide" Target="slides/slide1.xml"/>'
               f'<Relationship Id="rId2" Type="{R}/slide" Target="slides/slide2.xml"/></Relationships>')
    body = lambda lines: f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree>{sp(lines)}</p:spTree></p:cSld></p:sld>'
    z.writestr('ppt/slides/slide2.xml', body(['화면ID', 'WmsOrderList', '화면명', '출고 지시 목록', '1. 조회 버튼', '수정 → 삭제']))
    z.writestr('ppt/slides/slide1.xml', body(['Screen ID: UserEdit', 'Screen name: Edit user', '10/21 수정', 'New']))
    z.writestr('ppt/slides/_rels/slide2.xml.rels', f'<Relationships xmlns="{REL}">'
               f'<Relationship Id="rId1" Type="{R}/image" Target="../media/image1.png"/>'
               f'<Relationship Id="rId2" Type="{R}/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
               f'<Relationship Id="rId3" Type="{R}/hyperlink" Target="https://example.com" TargetMode="External"/>'
               '</Relationships>')
    z.writestr('ppt/notesSlides/notesSlide1.xml', f'<p:notes xmlns:p="{P}" xmlns:a="{A}">{sp(["[확인필요] 엑셀 전체 다운로드"])}</p:notes>')
    z.writestr('ppt/media/image1.png', PNG)
    z.close()


def make_pdf(path, pages):
    objs = ['<< /Type /Catalog /Pages 2 0 R >>',
            f'<< /Type /Pages /Kids [{" ".join(f"{3 + i} 0 R" for i in range(pages))}] /Count {pages} >>']
    objs += ['<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>'] * pages
    out = b'%PDF-1.4\n'
    for i, o in enumerate(objs, 1):
        out += f'{i} 0 obj\n{o}\nendobj\n'.encode()
    out += b'trailer\n<< /Root 1 0 R >>\n%%EOF\n'
    open(path, 'wb').write(out)


def index(out):
    rows = open(os.path.join(out, 'index.tsv'), encoding='utf-8').read().splitlines()
    return [r.split('\t') for r in rows[1:]]


def test_pptx():
    tmp = tempfile.mkdtemp()
    deck = os.path.join(tmp, '설계서 v3.pptx')
    make_pptx(deck)
    out = os.path.join(tmp, 'out')
    code, text = run(deck, out, '--pages', '1')
    rows = index(out)
    check('pptx: order follows sldIdLst, not slideN names', code == 0 and rows[0][1] == 'WmsOrderList'
          and rows[1][1] == 'UserEdit', text + str(rows))
    check('pptx: Korean label table gives id and title', rows[0][2] == '출고 지시 목록', rows)
    check('pptx: "수정 → 삭제" ends as delete', rows[0][3:5] == ['수정 → 삭제', 'delete'], rows)
    check('pptx: date note "10/21 수정" is not a status; English "New" is', rows[1][4] == 'new', rows)
    pages = json.load(open(os.path.join(out, 'pages.json'), encoding='utf-8'))
    check('pptx: notes and slide image extracted', pages['1']['notes'] == '[확인필요] 엑셀 전체 다운로드'
          and len(pages['1']['images']) == 1 and os.path.getsize(pages['1']['images'][0]) == len(PNG), pages['1'])
    check('pptx: --pages prints the page with its image path', '=== PAGE 1' in text and 'image ' in text, text)


def test_pdf_without_tools():
    tmp = tempfile.mkdtemp()
    pdf = os.path.join(tmp, 'deck.pdf')
    make_pdf(pdf, 3)
    out = os.path.join(tmp, 'out')
    code, text = run(pdf, out, '--pages', '2')
    pages = json.load(open(os.path.join(out, 'pages.json')))
    if ed.shutil.which('pdftotext'):
        check('pdf: pdftotext path ran', code == 0, text)
    else:
        check('pdf without pdftotext: page count recorded and Read tool suggested',
              code == 0 and len(pages) == 3 and pages['2'].get('read_with') == 'Read pages="2"' and 'Read tool' in text, text)


def test_images_and_folder():
    tmp = tempfile.mkdtemp()
    for name in ('b.png', 'a.png', 'notes.txt'):
        open(os.path.join(tmp, name), 'wb').write(PNG)
    out = os.path.join(tmp, 'out')
    code, text = run(tmp, out)
    pages = json.load(open(os.path.join(out, 'pages.json')))
    check('image folder: one page per image, sorted by name', code == 0 and len(pages) == 2
          and pages['1']['images'][0].endswith('a.png'), pages)


def test_text_inputs():
    tmp = tempfile.mkdtemp()
    drive = os.path.join(tmp, 'drive.json')
    md = '| 화면ID | MdmItem | 화면명 | 상품 | 화면경로 | 기준정보 |\n본문\n유지/수정\n\\-1-\n| 화면ID | - | 화면명 | 팝업 |\n신규\n\\-2-\n'
    json.dump({'fileContent': md}, open(drive, 'w', encoding='utf-8'), ensure_ascii=False)
    out = os.path.join(tmp, 'o1')
    code, text = run(drive, out)
    rows = index(out)
    check('Drive pptx export: pages split on \\-N-, "-" id is empty', code == 0 and len(rows) == 2
          and rows[0][1] == 'MdmItem' and rows[1][1] == '', rows)
    check('"유지/수정" is unclear, not guessed', rows[0][4] == 'unclear', rows)
    slides = os.path.join(tmp, 'slides.txt')
    open(slides, 'w', encoding='utf-8').write('화면ID A1 화면명 하나 내용 신규화면ID B2 화면명 둘 내용 (운송사)1234수정 → 삭제')
    out = os.path.join(tmp, 'o2')
    code, text = run(slides, out)
    rows = index(out)
    check('Slides dump: split on the ID label, trailing badge read', code == 0 and [r[1] for r in rows] == ['A1', 'B2']
          and rows[1][4] == 'delete', rows)


def test_status_symbols_and_errors():
    tmp = tempfile.mkdtemp()
    f = os.path.join(tmp, 't.txt')
    open(f, 'w', encoding='utf-8').write('Screen ID: X1\nbody\n★\n-----\nScreen ID: X2\nbody\n')
    out = os.path.join(tmp, 'o')
    code, text = run(f, out, '--status', '★=new,☆=modify')
    rows = index(out)
    check('repo legend via --status (★=new); no mark is unmarked', code == 0 and rows[0][4] == 'new'
          and rows[1][4] == 'unmarked', rows)
    code, text = run(f, out, '--status', '★=brand-new')
    check('bad --status value is refused', code == 2 and 'must be new' in text, text)
    for name in ('old.ppt', 'missing.pptx'):
        path = os.path.join(tmp, name)
        if name == 'old.ppt':
            open(path, 'w').write('x')
        code, text = run(path, out)
        check(f'{name}: refused with a next step', code == 2 and ('export' in text or 'does not exist' in text), text)
    bad = os.path.join(tmp, 'bad.pptx')
    open(bad, 'w').write('not a zip')
    code, text = run(bad, out)
    check('corrupt pptx: refused', code == 2 and 'not a valid pptx' in text, text)


if __name__ == '__main__':
    for fn in [v for k, v in sorted(globals().items()) if k.startswith('test_')]:
        fn()
    print(f'\n{"FAILED: " + ", ".join(FAILS) if FAILS else "all passed"}')
    sys.exit(1 if FAILS else 0)
