#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Manuel - EA7JRS
#
# Extracts the window (form) definitions stored as RCDATA resources inside
# "WX3in1 Plus 2 Configurator.exe" (C++Builder, binary DFM "TPF0") and saves
# them as JSON trees, for render_form.py and for documentation work.
#
# The Configurator itself is not included in this repository: use your own
# copy of the official Microsat package.
#
# Usage: extract_forms.py "WX3in1 Plus 2 Configurator.exe" OUTDIR
#        -> OUTDIR/form1.json (main window), form2.json, form4.json, ...
"""Extract C++Builder DFM forms from a Win32 PE file to JSON."""

import json
import os
import struct
import sys


# ---------------------------------------------------------------- PE resources
def pe_resources(data):
    """Yield (path, bytes) for every resource leaf of a PE file."""
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    nsec = struct.unpack_from('<H', data, pe + 6)[0]
    optsz = struct.unpack_from('<H', data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from('<H', data, opt)[0]
    ddir = opt + (96 if magic == 0x10B else 112)
    rva_res = struct.unpack_from('<I', data, ddir + 2 * 8)[0]
    secs = []
    for i in range(nsec):
        o = opt + optsz + i * 40
        vsz, va, rsz, raw = struct.unpack_from('<IIII', data, o + 8)
        secs.append((va, max(vsz, rsz), raw))

    def r2o(rva):
        for va, sz, raw in secs:
            if va <= rva < va + sz:
                return rva - va + raw
        raise ValueError('RVA %x outside sections' % rva)

    base = r2o(rva_res)

    def name_of(e):
        if e & 0x80000000:
            o = base + (e & 0x7FFFFFFF)
            n = struct.unpack_from('<H', data, o)[0]
            return data[o + 2:o + 2 + 2 * n].decode('utf-16le')
        return str(e)

    def walk(off, path):
        nn, ni = struct.unpack_from('<HH', data, base + off + 12)
        for i in range(nn + ni):
            e, t = struct.unpack_from('<II', data, base + off + 16 + 8 * i)
            p = path + [name_of(e)]
            if t & 0x80000000:
                yield from walk(t & 0x7FFFFFFF, p)
            else:
                rva, sz = struct.unpack_from('<II', data, base + t)
                o = r2o(rva)
                yield p, data[o:o + sz]

    yield from walk(0, [])


# ------------------------------------------------------------ binary DFM parser
class Dfm:
    def __init__(self, d):
        if d[:4] != b'TPF0':
            raise ValueError('not a binary DFM')
        self.d, self.p = d, 4

    def b(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def rd(self, n):
        s = self.d[self.p:self.p + n]
        self.p += n
        return s

    def sstr(self):
        return self.rd(self.b()).decode('latin-1')

    def i32(self):
        return struct.unpack('<i', self.rd(4))[0]

    def val(self):
        t = self.b()
        if t == 0:
            return None
        if t == 1:                                   # list
            out = []
            while self.d[self.p] != 0:
                out.append(self.val())
            self.p += 1
            return out
        if t == 2:
            return struct.unpack('<b', self.rd(1))[0]
        if t == 3:
            return struct.unpack('<h', self.rd(2))[0]
        if t == 4:
            return self.i32()
        if t == 5:
            self.rd(10)
            return '<extended>'
        if t in (6, 7):                              # string, ident
            return self.sstr()
        if t == 8:
            return False
        if t == 9:
            return True
        if t == 10:                                  # binary
            self.rd(self.i32())
            return None
        if t == 11:                                  # set
            out = []
            while True:
                s = self.sstr()
                if not s:
                    break
                out.append(s)
            return sorted(out)
        if t == 12:                                  # long string
            return self.rd(self.i32()).decode('latin-1')
        if t == 13:                                  # nil
            return None
        if t == 14:                                  # collection
            items = []
            while self.d[self.p] != 0:
                if self.d[self.p] in (2, 3, 4):
                    self.val()
                props = {}
                while self.d[self.p] != 0:
                    k = self.sstr()
                    props[k] = self.val()
                self.p += 1
                items.append(props)
            self.p += 1
            return items
        if t == 15:
            return struct.unpack('<f', self.rd(4))[0]
        if t in (16, 17, 19, 21):
            return struct.unpack('<q', self.rd(8))[0] if t == 19 else None
        if t == 18:                                  # wide string
            return self.rd(2 * self.i32()).decode('utf-16le')
        if t == 20:                                  # utf8 string
            return self.rd(self.i32()).decode('utf-8')
        raise ValueError('unknown DFM value type %d at %d' % (t, self.p))

    def obj(self):
        f = self.d[self.p]
        if f & 0xF0 == 0xF0:
            self.p += 1
            if f & 2:
                self.val()
        cls, name, props = self.sstr(), self.sstr(), {}
        while self.d[self.p] != 0:
            k = self.sstr()
            v = self.val()
            if v is not None:
                props[k] = v
        self.p += 1
        kids = []
        while self.d[self.p] != 0:
            kids.append(self.obj())
        self.p += 1
        return {'name': name, 'cls': cls, 'props': props, 'kids': kids}


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__ + '\nusage: extract_forms.py CONFIGURATOR.exe OUTDIR\n')
        return 1
    data = open(argv[1], 'rb').read()
    os.makedirs(argv[2], exist_ok=True)
    n = 0
    for path, blob in pe_resources(data):
        if blob[:4] != b'TPF0' or len(path) < 2:
            continue
        name = path[1].lower()                      # e.g. TFORM1 -> tform1
        name = name[1:] if name.startswith('t') else name
        tree = Dfm(blob).obj()
        out = os.path.join(argv[2], name + '.json')
        with open(out, 'w') as f:
            json.dump(tree, f, indent=1, ensure_ascii=False)
        print('%s -> %s (%s)' % (path[1], out, tree['props'].get('Caption', '')))
        n += 1
    return 0 if n else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
