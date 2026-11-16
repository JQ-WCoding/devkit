"""Split a screen design document into pages with text, notes, images, screen ID and status.

Usage: python3 -I extract_deck.py <input> <out dir> [--pages N ...] [--id-label REGEX] [--status WORD=STATUS,...]
Input (detected by extension):
  .pptx           slides in presentation order (sldIdLst, not the slideN file name), text, speaker notes, embedded pictures
  .pdf            text per page with pdftotext and PNG per requested page with pdftoppm when installed;
                  otherwise only the page count is recorded and pages are read with the Read tool (pages="N")
  .png .jpg ...   one page per image; a folder of images works too (sorted by name)
  .json .txt .md  exported text (a Drive read_file_content result, a Google Slides text dump, pasted text)
Output: <out dir>/pages.json and index.tsv (page, screen_id, title, status_raw, status, images, notes).
`status` is new | modify | keep | delete, `unclear` when the mark names two (e.g. "keep/modify"),
or `unmarked`. With --pages the chosen pages are printed in full.
"""
import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

# Status words seen in Korean and English decks -> canonical status. --status adds or overrides entries.
STATUS_WORDS = {'신규': 'new', '수정': 'modify', '유지': 'keep', '삭제': 'delete', '변경': 'modify',
                'new': 'new', 'add': 'new', 'added': 'new', 'modify': 'modify', 'modified': 'modify',
                'change': 'modify', 'changed': 'modify', 'update': 'modify', 'updated': 'modify',
                'keep': 'keep', 'unchanged': 'keep', 'as-is': 'keep', 'delete': 'delete', 'deleted': 'delete',
                'remove': 'delete', 'removed': 'delete'}
ID_LABEL = r'화면\s*ID|화면\s*코드|프로그램\s*ID|Screen\s*ID|Screen\s*code|Program\s*ID|Page\s*ID'
TITLE_LABEL = r'화면\s*명|화면\s*이름|프로그램\s*명|Screen\s*name|Page\s*name|Title'
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
PDF_DPI = 150  # readable mockup text at a size the Read tool still accepts


class DeckError(Exception):
    pass


# ---------- pptx ----------

def _rels(z, part):
    """Relationship id -> target path (resolved against the part's folder)."""
    folder, name = posixpath.split(part)
    rel_path = posixpath.join(folder, '_rels', name + '.rels')
    if rel_path not in z.namelist():
        return {}
    out = {}
    for r in ET.fromstring(z.read(rel_path)).findall('rel:Relationship', NS):
        if r.get('TargetMode') == 'External':
            continue
        out[r.get('Id')] = (posixpath.normpath(posixpath.join(folder, r.get('Target'))), r.get('Type', ''))
    return out


def _text(z, part):
    """Paragraph text of a slide or notes part, one line per <a:p>."""
    root = ET.fromstring(z.read(part))
    lines = []
    for para in root.iter(f'{{{NS["a"]}}}p'):
        line = ''.join(t.text or '' for t in para.iter(f'{{{NS["a"]}}}t')).strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)


def read_pptx(path, out):
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise DeckError(f'{path} is not a valid pptx (zip) file')
    with z:
        pres = 'ppt/presentation.xml'
        if pres not in z.namelist():
            raise DeckError(f'{path} has no ppt/presentation.xml; export it as .pptx again')
        rels = _rels(z, pres)
        order = [s.get(f'{{{NS["r"]}}}id') for s in ET.fromstring(z.read(pres)).iter(f'{{{NS["p"]}}}sldId')]
        media_dir = os.path.join(out, 'media')
        pages = {}
        for n, rid in enumerate(order, 1):
            slide = rels[rid][0]
            srels = _rels(z, slide)
            notes = next((t for t, kind in srels.values() if kind.endswith('/notesSlide')), None)
            images = []
            for i, (target, kind) in enumerate(sorted(srels.values())):
                if kind.endswith('/image') and target in z.namelist():
                    os.makedirs(media_dir, exist_ok=True)
                    dest = os.path.join(media_dir, f'p{n}-{i}{os.path.splitext(target)[1].lower()}')
                    with z.open(target) as src, open(dest, 'wb') as dst:  # only known parts, never arbitrary names
                        shutil.copyfileobj(src, dst)
                    images.append(dest)
            pages[n] = {'text': _text(z, slide), 'notes': _text(z, notes) if notes else '', 'images': images,
                        'source': slide}
    return pages, 'pptx'


# ---------- pdf ----------

def read_pdf(path, out, wanted):
    pages = {}
    if shutil.which('pdftotext'):
        r = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True)
        if r.returncode == 0:
            for n, chunk in enumerate(r.stdout.split('\f'), 1):
                if chunk.strip() or n == 1:
                    pages[n] = {'text': chunk.strip(), 'notes': '', 'images': []}
    if not pages:  # no pdftotext: count pages from the PDF structure, text comes from the Read tool
        data = open(path, 'rb').read()
        count = len(re.findall(rb'/Type\s*/Page(?!s)\b', data))
        if not count:
            raise DeckError(f'{path}: no pages found; read it with the Read tool (pages="1-5")')
        pages = {n: {'text': '', 'notes': '', 'images': [], 'read_with': f'Read pages="{n}"'} for n in range(1, count + 1)}
    if shutil.which('pdftoppm'):
        img_dir = os.path.join(out, 'img')
        os.makedirs(img_dir, exist_ok=True)
        for n in (wanted or []):
            if n in pages:
                prefix = os.path.join(img_dir, f'p{n}')
                subprocess.run(['pdftoppm', '-png', '-r', str(PDF_DPI), '-f', str(n), '-l', str(n), '-singlefile',
                                path, prefix], capture_output=True)
                if os.path.exists(prefix + '.png'):
                    pages[n]['images'].append(prefix + '.png')
    return pages, 'pdf'


# ---------- images and text ----------

def read_images(paths):
    return {n: {'text': '', 'notes': '', 'images': [os.path.abspath(p)]} for n, p in enumerate(paths, 1)}, 'images'


def load_text(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    try:
        return json.loads(raw)['fileContent']
    except (ValueError, KeyError, TypeError):
        return raw


def read_text(path, id_label):
    text = load_text(path)
    if re.search(r'\n\\-\d+-(?:\n|$)', text):  # Drive export of a pptx: each page ends with '\-N-'
        parts = re.split(r'\n\\-(\d+)-(?:\n|$)', text)
        chunks = {int(parts[i]): parts[i - 1] for i in range(1, len(parts), 2)}
    elif re.search(r'\n-{5,}\n', text):  # '-----' between slides
        chunks = {i + 1: c for i, c in enumerate(c for c in re.split(r'\n-{5,}\n', text) if c.strip())}
    elif re.search(r'\f', text):
        chunks = {i + 1: c for i, c in enumerate(text.split('\f')) if c.strip()}
    else:  # Google Slides dump: every slide starts with the screen ID label
        parts = [c for c in re.split(rf'(?=(?:{id_label})\s)', text) if c.strip()]
        chunks = {i + 1: c for i, c in enumerate(parts)}
    return {n: {'text': c.strip(), 'notes': '', 'images': []} for n, c in chunks.items()}, 'text'


# ---------- header and status ----------

def _cell_after(label, body):
    # '| 화면ID | ABC | 화면명 | ...' (markdown table) or 'Screen ID: ABC' / 'Screen ID ABC' on one line
    m = re.search(rf'(?:{label})\s*\|?\s*[:：]?\s*\|?\s*([^|\n]+?)\s*(?:\||\n|$)', body, re.I)
    if not m:
        return ''
    value = m.group(1).replace('\\', '').strip()
    return '' if value in ('-', '') else value


def parse_header(body, id_label):
    sid = _cell_after(id_label, body)
    sid = sid.split()[0] if sid else ''
    title = _cell_after(TITLE_LABEL, body)
    if not title:
        title = next((ln.strip() for ln in body.splitlines() if ln.strip()), '')[:60]
    return sid, title


def parse_status(body, words):
    alt = '|'.join(sorted((re.escape(w) for w in words), key=len, reverse=True))
    mark = rf'(?:{alt})(?:\s*[/→>-]+\s*(?:{alt}))*'
    text = re.sub(rf'\d{{1,2}}[/.]\d{{1,2}}\.?\s*(?:{alt})', '', body, flags=re.I)  # '10/21 수정' is a date note
    marks = [ln.strip() for ln in text.split('\n') if re.fullmatch(mark, ln.strip(), re.I)]
    if not marks:
        cells = re.findall(rf'(?:^|\|)\s*({mark})\s*(?=\||$)', text, re.I | re.M)  # a table cell holding only the mark
        marks = cells
    if not marks:
        m = re.search(rf'({mark})\s*$', text.strip(), re.I)  # Slides dumps end with the badge, no line break
        marks = [m.group(1)] if m else []
    if not marks:
        return '', 'unmarked'
    raw = marks[-1]
    last = re.split(r'→|->|>', raw)[-1].strip()  # 'modify → delete': the last change counts
    if '/' in last:  # 'keep/modify' does not decide; a person must
        return raw, 'unclear'
    return raw, words.get(last.lower(), words.get(last, 'unmarked'))


# ---------- main ----------

def main(argv=None):
    p = argparse.ArgumentParser(description='Split a screen design document into pages')
    p.add_argument('input')
    p.add_argument('out')
    p.add_argument('--pages', nargs='*', type=int, default=[])
    p.add_argument('--id-label', default=ID_LABEL, help='regex for the screen ID label')
    p.add_argument('--status', default='', help='extra WORD=STATUS pairs, comma separated (e.g. "★=new,☆=modify")')
    a = p.parse_args(argv)
    words = dict(STATUS_WORDS)
    for pair in filter(None, (s.strip() for s in a.status.split(','))):
        word, _, status = pair.partition('=')
        if status not in ('new', 'modify', 'keep', 'delete'):
            print(f'extract_deck: --status {pair!r}: status must be new, modify, keep or delete', file=sys.stderr)
            return 2
        words[word.strip().lower() if word.isascii() else word.strip()] = status
    os.makedirs(a.out, exist_ok=True)
    src = a.input
    try:
        if os.path.isdir(src):
            imgs = sorted(os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith(IMAGE_EXT))
            if not imgs:
                raise DeckError(f'{src}: no images ({", ".join(IMAGE_EXT)})')
            pages, fmt = read_images(imgs)
        elif not os.path.exists(src):
            raise DeckError(f'{src} does not exist')
        else:
            ext = os.path.splitext(src)[1].lower()
            if ext == '.pptx':
                pages, fmt = read_pptx(src, a.out)
            elif ext == '.pdf':
                pages, fmt = read_pdf(src, a.out, a.pages)
            elif ext in IMAGE_EXT:
                pages, fmt = read_images([src])
            elif ext in ('.ppt', '.key', '.docx', '.hwp'):
                raise DeckError(f'{ext} is not read directly; export the deck as .pptx or .pdf (or slide images)')
            else:
                pages, fmt = read_text(src, a.id_label)
    except DeckError as e:
        print(f'extract_deck: {e}', file=sys.stderr)
        return 2
    for n, pg in pages.items():
        body = pg['text'] + ('\n' + pg['notes'] if pg['notes'] else '')
        pg['screen_id'], pg['title'] = parse_header(pg['text'], a.id_label)
        pg['status_raw'], pg['status'] = parse_status(body, words)
    with open(os.path.join(a.out, 'pages.json'), 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in sorted(pages.items())}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, 'index.tsv'), 'w', encoding='utf-8') as f:
        f.write('page\tscreen_id\ttitle\tstatus_raw\tstatus\timages\tnotes\n')
        for n in sorted(pages):
            pg = pages[n]
            f.write('\t'.join([str(n), pg['screen_id'], pg['title'].replace('\t', ' '), pg['status_raw'], pg['status'],
                               str(len(pg['images'])), 'y' if pg['notes'] else '']) + '\n')
    print(f'format={fmt} pages={len(pages)} -> {a.out}/pages.json, index.tsv')
    if fmt == 'pdf' and not any(pg['text'] for pg in pages.values()):
        print('note: pdftotext is not installed; read the pages with the Read tool (pages="N"); mockups come from the same read')
    for n in a.pages:
        pg = pages.get(n)
        print(f'=== PAGE {n}')
        if not pg:
            print('(no such page)')
            continue
        print(f'screen_id={pg["screen_id"]} title={pg["title"]} status={pg["status"]} ({pg["status_raw"]})')
        print(pg['text'] or '(no text: read the image or the PDF page)')
        if pg['notes']:
            print(f'--- notes\n{pg["notes"]}')
        for img in pg['images']:
            print(f'image {img}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
