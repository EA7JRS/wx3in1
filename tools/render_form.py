#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Manuel - EA7JRS
#
# Renders a C++Builder form (JSON made by extract_forms.py) as a
# Windows-7-classic style HTML mock, filled with values from a WX3in1 Plus 2.0
# .cfg file, and screenshots it with Playwright. Used to illustrate the
# Configurator v1.13 tabs in the manual ("Configurator v1.13 layout").
#
# Usage: render_form.py spec.json
#   spec.json = [{"form": "forms/form1.json", "cfg": "config.cfg",
#                 "active": ["TabSheet_beacons", "TabSheet_gps_smartbeaconing"],
#                 "out": "img/v113_smartbeaconing.png",
#                 "title": "WX3in1 Plus 2.0 Configurator v1.13"}, ...]
import json, sys, html, re

ALIAS = {
    'position_report_mode': 'ReportMode', 'position_report_encoding': 'ReportEncoding',
    'smartbeaconing_min_turn_angle': 'MinTurnAngle', 'smartbeaconing_turn_slope': 'TurnSlope',
    'smartbeaconing_min_turn_time': 'MinTurnTime', 'smartbeaconing_slow_speed': 'SlowSpeed',
    'smartbeaconing_slow_period': 'SlowPeriod', 'smartbeaconing_fast_speed': 'FastSpeed',
    'smartbeaconing_fast_period': 'FastPeriod', 'position_symbol_code': 'SymbolCode',
    'position_symbol_table': 'SymbolTable', 'mice_message': 'MiceMessage',
    'position_path1': 'Path1', 'position_path2': 'Path2', 'position_path3': 'Path3',
    'position_ssid1': 'SSID1', 'position_ssid2': 'SSID2', 'position_ssid3': 'SSID3',
    'position_status_text': 'Status', 'position_time': 'PositionTime',
    'position_coursespeed': 'CourseSpeed', 'position_altitude': 'PositionAltitude',
    'teletitle': 'Tele_title', 'www_password': 'Www_pass', 'telnet_password': 'Telnet_pass',
    'aprsis_heard_timeout': 'Aprsis_heardtimeout', 'ptt': 'PTT', 'ssid': 'SSID',
}


ANALOG = ['Not used', '(M) Current1 (5A fullscale)', '(M) Current1 (2.5A fullscale)', '(M) Current1 (1.25A fullscale)',
          '(M) Current2 (5A fullscale)', '(M) Current2 (2.5A fullscale)', '(M) Current2 (1.25A fullscale)',
          '(M) Voltage1', '(M) Voltage2', '(M) Temperature (DS18B20)', '(M) Temperature (DS18S20)',
          '(E) Temperature (DS18B20)', '(E) Temperature (DS18S20)', '(I) Input voltage',
          "(I) RX'ed packets (1 hour)", "(I) RX'ed packets (10 min)", "(I) DIGI'ed packets (1 hour)",
          "(I) DIGI'ed packets (10 min)", '(I) Decode efficiency (total)', '(I) Decode efficiency (1 hour)',
          "(I) DIGI'ed/RX'ed (1 hour)", "(I) DIGI'ed/RX'ed (total)", "(I) DIGI'ed/pkt starts (1 hour)",
          "(I) DIGI'ed/pkt starts (total)"]
DIGITAL = ['Not used', '(M) Output 1', '(M) Output 2', '(M) Output 3', '(M) Output 4',
           '(M) Input 1', '(M) Input 2', '(M) Input 3', '(M) Input 4']
ITEMS = {'Teleanalog#_source': ANALOG, 'Teledigital#_source': DIGITAL}


def load_cfg(path):
    vals = {}
    sec = None
    for line in open(path, encoding='latin1').read().splitlines():
        line = line.strip()
        if line.startswith('['):
            sec = line[1:-1]
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            vals.setdefault(k.lower(), v)
            vals[(sec + '.' + k).lower()] = v
    return vals


def find(node, name):
    if node['name'] == name:
        return node
    for k in node['kids']:
        r = find(k, name)
        if r:
            return r
    return None


def esc(s):
    return html.escape(str(s))


class R:
    def __init__(self, cfg, active, overrides):
        self.cfg, self.active, self.ov = cfg, active, overrides
        self.out = []

    def value(self, name):
        if name in self.ov:
            return self.ov[name]
        key = ALIAS.get(name.lower(), name).lower()
        return self.cfg.get(key)

    def text_w(self, s):
        return int(len(s) * 5.6) + 2

    def node(self, n, ox, oy):
        p, c = n['props'], n['cls']
        x, y = ox + p.get('Left', 0), oy + p.get('Top', 0)
        w, h = p.get('Width', 0), p.get('Height', 0)
        st = f'left:{x}px;top:{y}px;width:{w}px;height:{h}px'
        if p.get('Visible') is False:
            return
        bold = ' b' if 'fsBold' in (p.get('Font.Style') or []) else ''
        red = ' red' if p.get('Font.Color') == 'clRed' else ''
        if c == 'TLabel':
            cap = p.get('Caption', '')
            ww = '' if not p.get('WordWrap') else ' wrap'
            self.out.append(f'<div class="lbl{bold}{red}{ww}" style="left:{x}px;top:{y}px;'
                            f'{"width:%dpx;" % w if p.get("WordWrap") else ""}">{esc(cap)}</div>')
        elif c == 'TEdit':
            v = self.value(n['name'])
            v = p.get('Text', '') if v is None else v
            self.out.append(f'<div class="edit" style="{st}"><span>{esc(v)}</span></div>')
        elif c == 'TComboBox':
            items = p.get('Items.Strings') or ITEMS.get(re.sub(r'\d+', '#', n['name']), [])
            v = self.value(n['name'])
            if v is not None and v.lstrip('-').isdigit() and int(v) < 0:
                v = ''
            txt = ''
            if v is not None and items:
                try:
                    txt = items[int(v)]
                except (ValueError, IndexError):
                    txt = v
            elif v is not None:
                txt = v
            self.out.append(f'<div class="combo" style="{st}"><span>{esc(txt)}</span><i></i></div>')
        elif c == 'TCheckBox':
            v = self.value(n['name'])
            chk = (v == '1') if v is not None else p.get('Checked', False)
            cap = p.get('Caption', '')
            self.out.append(f'<div class="chk" style="{st}"><b class="{"on" if chk else ""}"></b>{esc(cap)}</div>')
        elif c in ('TButton', 'TBitBtn'):
            cap = p.get('Caption') or {'bkOK': 'OK', 'bkCancel': 'Cancel'}.get(p.get('Kind'), '')
            self.out.append(f'<div class="btn" style="{st}">{esc(cap)}</div>')
        elif c == 'TGroupBox':
            self.out.append(f'<div class="grp" style="{st}"><span>{esc(p.get("Caption", ""))}</span></div>')
            for k in n['kids']:
                self.node(k, x, y)
            return
        elif c == 'TMemo':
            self.out.append(f'<div class="memo" style="{st}"><i></i></div>')
        elif c == 'TProgressBar':
            self.out.append(f'<div class="prog" style="left:0;top:{y}px;width:800px;height:{h}px"></div>')
        elif c == 'TPageControl':
            self.pagecontrol(n, x, y, w, h)
            return
        for k in n['kids']:
            self.node(k, x, y)

    def pagecontrol(self, n, x, y, w, h):
        p = n['props']
        tabs = n['kids']
        act = next((t for t in tabs if t['name'] in self.active), None) or find(n, p.get('ActivePage')) or tabs[0]
        buttons = p.get('Style') == 'tsButtons'
        if buttons:
            row = ''.join(f'<span class="{"tbtn on" if t is act else "tbtn"}">{esc(t["props"].get("Caption", ""))}</span>'
                          for t in tabs)
            self.out.append(f'<div class="trow b3" style="left:{x}px;top:{y}px">{row}</div>')
            cy = y + 27
            cx = x
        else:
            self.out.append(f'<div class="pcbody" style="left:{x}px;top:{y + 20}px;width:{w - 2}px;height:{h - 22}px"></div>')
            row = ''.join(f'<span class="{"tab on" if t is act else "tab"}">{esc(t["props"].get("Caption", ""))}</span>'
                          for t in tabs)
            self.out.append(f'<div class="trow" style="left:{x + 2}px;top:{y}px">{row}</div>')
            cy = y + 24
            cx = x + 4
        for k in act['kids']:
            self.node(k, cx, cy)


CSS = '''
*{box-sizing:border-box}
body{margin:0;background:#fff;font:10.4px "Liberation Sans",Arial,sans-serif;letter-spacing:-0.1px;color:#000}
#win{position:relative;width:806px;height:%(H)dpx;border:1px solid #6d7d92;background:#c3d4e7;
 border-radius:6px 6px 0 0;overflow:hidden}
#title{position:absolute;left:0;top:0;width:100%%;height:25px;background:linear-gradient(#dbe6f4,#c4d5ea);}
#title .ico{position:absolute;left:6px;top:5px;width:16px;height:16px;background:#111;color:#fff;font:bold 12px Arial;text-align:center;line-height:16px}
#title .t{position:absolute;left:28px;top:6px;font-size:12px}
#title .wb{position:absolute;top:2px;height:18px;border:1px solid #707e93;border-radius:3px;background:linear-gradient(#f3f6fb,#cfdae8)}
#title .x{background:linear-gradient(#e8a493,#c45139)}
#client{position:absolute;left:2px;top:25px;width:800px;height:%(CH)dpx;background:#f0f0f0;overflow:hidden}
.lbl,.edit,.combo,.chk,.btn,.grp,.memo,.prog,.pcbody{position:absolute}
.lbl{white-space:nowrap;line-height:13px}
.lbl.wrap{white-space:normal}
.b{font-weight:bold}.red{color:#e00}
.edit{background:#fff;border:1px solid #abadb3;border-top-color:#8e8f8f;padding:3px 2px;line-height:13px;overflow:hidden;white-space:nowrap}
.combo{background:#fff;border:1px solid #abadb3;padding:3px 2px;line-height:13px;overflow:hidden;white-space:nowrap}
.combo i{position:absolute;right:1px;top:1px;bottom:1px;width:16px;background:linear-gradient(#f2f2f2,#dcdcdc);border-left:1px solid #bbb}
.combo i:after{content:"";position:absolute;left:4px;top:7px;border:4px solid transparent;border-top:4px solid #000}
.chk{white-space:nowrap;padding-left:17px;line-height:15px}
.chk b{position:absolute;left:0;top:1px;width:13px;height:13px;border:1px solid #8f8f8f;background:#fff}
.chk b.on:after{content:"\\2714";position:absolute;left:1px;top:-2px;font-size:11px;color:#222}
.btn{border:1px solid #707070;border-radius:3px;background:linear-gradient(#f2f2f2 50%%,#dddddd 50%%,#cfcfcf);text-align:center;line-height:22px}
.grp{border:1px solid #d5dfe5;border-radius:3px}
.grp span{position:absolute;left:6px;top:-8px;background:#f0f0f0;padding:0 2px}
.memo{background:#fff;border:1px solid #abadb3}
.memo i{position:absolute;right:0;top:0;bottom:0;width:17px;background:#f0f0f0;border-left:1px solid #e3e3e3}
.prog{background:#e6e6e6;border-top:1px solid #d0d0d0}
.pcbody{background:#fff;border:1px solid #898c95}
.trow{position:absolute;display:flex;align-items:flex-end;white-space:nowrap;z-index:2}
.trow.b3{gap:3px;align-items:flex-start}
.tab{display:block;height:18px;margin-top:2px;padding:0 5px;border:1px solid #898c95;border-right:none;border-bottom:none;background:linear-gradient(#f2f2f2,#e3e3e3);line-height:17px}
.tab:last-child{border-right:1px solid #898c95}
.tab.on{height:22px;margin:0 -2px 0 -2px;padding:0 7px;background:#fff;border-right:1px solid #898c95;position:relative;z-index:3;line-height:19px}
.tbtn{display:block;height:23px;padding:0 6px;border:1px solid #707070;border-radius:2px;background:linear-gradient(#f2f2f2 50%%,#dddddd 50%%);line-height:21px}
.tbtn.on{background:#fff;border-color:#555;box-shadow:inset 1px 1px 2px #999}
'''


def render(form_json, cfg_path, active, out_png, title, overrides=None, form_w=None):
    form = json.load(open(form_json))
    cfg = load_cfg(cfg_path) if cfg_path else {}
    r = R(cfg, set(active), overrides or {})
    for k in form['kids']:
        r.node(k, 0, 0)
    ch = form['props']['ClientHeight']
    cw = form['props']['ClientWidth']
    H = ch + 28
    css = CSS % {'H': H, 'CH': ch}
    if cw != 800:
        css = css.replace('width:806px', f'width:{cw + 6}px').replace('width:800px;height', f'width:{cw}px;height')
    btns = ''
    if form['cls'] == 'TForm1':
        btns = ('<div class="wb" style="left:704px;width:27px"></div><div class="wb" style="left:733px;width:27px"></div>'
                '<div class="wb x" style="left:762px;width:40px"></div>')
    else:
        btns = f'<div class="wb x" style="left:{cw - 42}px;width:40px"></div>'
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>'
           f'<div id="win"><div id="title"><div class="ico">M</div><div class="t">{esc(title)}</div>{btns}</div>'
           f'<div id="client">{"".join(r.out)}</div></div></body></html>')
    import os
    hp = os.path.abspath(out_png.rsplit('.', 1)[0] + '.html')
    open(hp, 'w').write(doc)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': cw + 6, 'height': H}, device_scale_factor=2)
        pg.goto('file://' + hp)
        pg.locator('#win').screenshot(path=out_png)
        b.close()


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    for s in spec:
        render(s['form'], s.get('cfg'), s.get('active', []), s['out'], s['title'], s.get('overrides'))
        print('ok', s['out'])
