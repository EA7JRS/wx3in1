#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Manuel - EA7JRS
#
# Builds the WX3in1 Plus 2.0 v1.13 PDF documents from the HTML sources:
#   build.py en     -> docs/manual/wx3in1plus20_v113_manual_english.pdf
#   build.py es     -> docs/manual/wx3in1plus20_v113_manual_espanol.pdf
#   build.py guia   -> docs/guia-rapida/wx3in1plus20_guia_rapida.pdf
#   build.py all    -> all of them
# Pass 1 renders the PDF, finds the page of every heading and fills the TOC,
# pass 2 renders the final PDF with page numbers.
# Needs: Python 3, playwright (Chromium), pypdf, pdftotext (poppler-utils)
# and the Carlito font.
import os, re, subprocess, html
from playwright.sync_api import sync_playwright
import pypdf

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

DOCS = os.path.join(os.path.dirname(HERE), 'docs')
TARGETS = {
    'en': dict(src='manual_en.html', out=os.path.join(DOCS, 'manual', 'wx3in1plus20_v113_manual_english.pdf'),
               start='About this revision', skip=2,
               meta={'/Title': 'WX3in1 Plus 2.0 (firmware v1.13) - Instruction manual and Configuration software manual',
                     '/Author': 'Mateusz Plocinski SQ3PLX / Microsat; v1.13 revision by Manuel EA7JRS',
                     '/Subject': 'Manual revision 5 November 2026, updated from revision 15 March 2016',
                     '/Keywords': 'WX3in1 Plus 2.0, APRS, digipeater, igate, Microsat, firmware v1.13'}),
    'es': dict(src='manual_es.html', out=os.path.join(DOCS, 'manual', 'wx3in1plus20_v113_manual_espanol.pdf'),
               start='Acerca de esta revisión', skip=2,
               meta={'/Title': 'WX3in1 Plus 2.0 (firmware v1.13) - Manual de instrucciones y manual del software de configuracion',
                     '/Author': 'Mateusz Plocinski SQ3PLX / Microsat; revision v1.13 y traduccion al espanol: Manuel EA7JRS',
                     '/Subject': 'Revision del manual 5 de noviembre de 2026, basada en la revision del 15 de marzo de 2016',
                     '/Keywords': 'WX3in1 Plus 2.0, APRS, digipetidor, igate, Microsat, firmware v1.13, manual en espanol'}),
    'guia': dict(src='guia_rapida.html', out=os.path.join(DOCS, 'guia-rapida', 'wx3in1plus20_guia_rapida.pdf'),
                 start='1. Qué necesita', skip=0,
                 meta={'/Title': 'WX3in1 Plus 2.0 (firmware v1.13) - Guia rapida de puesta en marcha',
                       '/Author': 'Manuel EA7JRS',
                       '/Subject': 'Puesta en marcha de un digipetidor / I-Gate APRS con el WX3in1 Plus 2.0',
                       '/Keywords': 'WX3in1 Plus 2.0, APRS, digipetidor, igate, guia rapida'}),
}
SRC = OUT = START = META = None
SKIP = 2

FOOTER = ('<div style="width:100%;text-align:center;font-family:Carlito,sans-serif;'
          'font-size:10.5px;color:#000;"><span class="pageNumber"></span></div>')


def headings(doc):
    out = []
    for m in re.finditer(r'<h([123])[^>]*id="([^"]+)"[^>]*>(.*?)</h\1>', doc, re.S):
        lvl, hid, inner = int(m.group(1)), m.group(2), m.group(3)
        if hid in ('rev',):
            pass
        text = re.sub(r'<span class="new">.*?</span>', '', inner)
        text = html.unescape(re.sub(r'<[^>]+>', '', text)).strip()
        out.append((lvl, hid, text))
    return out


def toc_html(hs, pages):
    rows = []
    for lvl, hid, text in hs:
        p = pages.get(hid, '')
        rows.append(f'<div class="l{lvl}"><span class="n">{html.escape(text)}</span>'
                    f'<span class="d"></span><span class="p">{p}</span></div>')
    return '\n'.join(rows)


def render(doc, path):
    tmp = os.path.join(HERE, '_render.html')
    open(tmp, 'w').write(doc)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto('file://' + tmp)
        pg.wait_for_load_state('networkidle')
        pg.pdf(path=path, format='A4', print_background=True, prefer_css_page_size=True,
               display_header_footer=True, header_template='<div></div>', footer_template=FOOTER,
               margin={'top': '16mm', 'bottom': '20mm', 'left': '19mm', 'right': '19mm'})
        b.close()
    os.remove(tmp)


def norm(s):
    return re.sub(r'\s+', ' ', s.replace('­', '')).strip()


def find_pages(pdf, hs):
    n = len(pypdf.PdfReader(pdf).pages)
    texts = []
    for i in range(1, n + 1):
        t = subprocess.run(['pdftotext', '-f', str(i), '-l', str(i), '-layout', pdf, '-'],
                           capture_output=True, text=True).stdout
        texts.append(norm(t))
    # first page after the table of contents
    start = next(i for i, t in enumerate(texts) if START in t and i >= SKIP)
    pages = {}
    cur = start
    for lvl, hid, text in hs:
        key = norm(text)[:45]
        for i in range(cur, n):
            if key in texts[i]:
                pages[hid] = i + 1
                cur = i
                break
        else:
            print('NOT FOUND:', text)
    return pages, n


def build(target):
    global SRC, OUT, START, META, SKIP
    t = TARGETS[target]
    SRC, OUT, START, META = os.path.join(HERE, t['src']), t['out'], t['start'], t['meta']
    SKIP = t['skip']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = open(SRC).read()
    # keep sub-headings together with the next paragraph/figure
    doc = re.sub(r'(<h[23][^>]*>.*?</h[23]>)\s*(<(p|figure)\b[^>]*>.*?</\3>)',
                 r'<div class="keep">\1\2</div>', doc, flags=re.S)
    hs = [h for h in headings(doc) if h[1] != 'toc']
    # pass 1 with placeholder numbers (same width)
    d1 = doc.replace('<!--TOC-->', toc_html(hs, {h[1]: '00' for h in hs}))
    render(d1, OUT)
    pages, n = find_pages(OUT, hs)
    d2 = doc.replace('<!--TOC-->', toc_html(hs, pages))
    render(d2, OUT)
    pages2, n2 = find_pages(OUT, hs)
    if pages2 != pages:
        print('page numbers moved, re-rendering')
        render(doc.replace('<!--TOC-->', toc_html(hs, pages2)), OUT)
    # metadata
    r = pypdf.PdfReader(OUT)
    w = pypdf.PdfWriter(clone_from=r)
    w.add_metadata(META)
    # bookmarks
    parents = {}
    for lvl, hid, text in hs:
        p = pages2.get(hid)
        if not p:
            continue
        par = parents.get(lvl - 1) if lvl > 1 else None
        parents[lvl] = w.add_outline_item(text, p - 1, parent=par)
    w.write(OUT)
    print('pages:', n2, '->', OUT)


def main(argv):
    targets = argv[1:] or ['all']
    if targets == ['all']:
        targets = list(TARGETS)
    for t in targets:
        if t not in TARGETS:
            raise SystemExit('unknown target %s (use: %s, all)' % (t, ', '.join(TARGETS)))
        build(t)


if __name__ == '__main__':
    main(sys.argv)
