# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Manuel - EA7JRS
"""Tests for tools/wx3cfg.py (run: python3 -m unittest discover -s tests)."""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import wx3cfg  # noqa: E402

TEMPLATE = os.path.join(ROOT, 'config', 'wx3in1plus20_EA_plantilla.cfg')


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = wx3cfg.main(['--no-color', '--lang', 'en'] + list(argv))
    return code, buf.getvalue()


class Passcode(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(wx3cfg.aprs_passcode('N0CALL'), 13023)
        self.assertEqual(wx3cfg.aprs_passcode('n0call-10'), 13023)

    def test_ssid_ignored(self):
        self.assertEqual(wx3cfg.aprs_passcode('EA7JRS'), wx3cfg.aprs_passcode('EA7JRS-10'))


class Coordinates(unittest.TestCase):
    def test_lat(self):
        self.assertTrue(wx3cfg.lat_ok('3723.10N'))
        self.assertFalse(wx3cfg.lat_ok('3760.00N'))
        self.assertFalse(wx3cfg.lat_ok('9100.00S'))
        self.assertFalse(wx3cfg.lat_ok('372.10N'))

    def test_lon(self):
        self.assertTrue(wx3cfg.lon_ok('00559.40W'))
        self.assertFalse(wx3cfg.lon_ok('0559.40W'))
        self.assertFalse(wx3cfg.lon_ok('18100.00E'))


class Country(unittest.TestCase):
    def test_ntp(self):
        self.assertEqual(wx3cfg.ntp_for('EA7JRS'), '0.es.pool.ntp.org')
        self.assertEqual(wx3cfg.ntp_for('EB1ABC'), '0.es.pool.ntp.org')
        self.assertEqual(wx3cfg.ntp_for('SQ3PLX'), '0.pl.pool.ntp.org')
        self.assertEqual(wx3cfg.ntp_for('ZZ9ZZZ'), 'pool.ntp.org')


class Template(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_template_needs_callsign(self):
        code, out = run('check', TEMPLATE)
        self.assertEqual(code, 2)
        self.assertIn('NOCALL', out)

    def test_fix_template_is_clean(self):
        dst = os.path.join(self.tmp, 'ok.cfg')
        code, out = run('fix', TEMPLATE, '-o', dst, '--callsign', 'EA7JRS-10',
                        '--lat', '3631.20N', '--lon', '00612.30W', '--random-passwords')
        self.assertEqual(code, 0, out)
        cfg = wx3cfg.Cfg(dst)
        self.assertEqual(cfg.get('APRS-IS', 'Aprsis_user'), 'EA7JRS-10')
        self.assertEqual(cfg.get('APRS-IS', 'Aprsis_pass'), str(wx3cfg.aprs_passcode('EA7JRS')))
        self.assertNotEqual(cfg.get('WWW', 'Www_pass'), 'admin')

    def test_fix_keeps_bytes_outside_changes(self):
        dst = os.path.join(self.tmp, 'same.cfg')
        run('fix', TEMPLATE, '-o', dst)
        self.assertEqual(open(TEMPLATE, 'rb').read(), open(dst, 'rb').read())

    def test_errors_detected(self):
        dst = os.path.join(self.tmp, 'bad.cfg')
        run('fix', TEMPLATE, '-o', dst, '--callsign', 'EA7JRS',
            '--set', 'TXdelay=100', '--set', 'Latitude=3790.00N',
            '--set', 'Beacon1_msg=' + 'x' * 96, '--set', 'Callfilter_ssid3=16',
            '--set', 'Digipeater/Pathn1_lower=3', '--set', 'Pathn1_higher=2')
        code, out = run('check', dst)
        self.assertEqual(code, 2)
        for key in ('TXdelay', 'Latitude', 'Beacon1_msg', 'Callfilter_ssid3', 'Pathn1_lower'):
            self.assertIn(key, out)

    def test_smartbeaconing_without_gps(self):
        dst = os.path.join(self.tmp, 'sb.cfg')
        run('fix', TEMPLATE, '-o', dst, '--callsign', 'EA7JRS-9', '--lat', '3631.20N',
            '--lon', '00612.30W', '--set', 'ReportMode=1')
        code, out = run('check', dst)
        self.assertEqual(code, 2)
        self.assertIn('ReportMode', out)

    def test_wrong_passcode(self):
        dst = os.path.join(self.tmp, 'pc.cfg')
        run('fix', TEMPLATE, '-o', dst, '--callsign', 'EA7JRS', '--set', 'Aprsis_pass=12345')
        code, out = run('check', dst)
        self.assertIn('Aprsis_pass', out)


    def test_json_summary(self):
        import json
        dst = os.path.join(self.tmp, 'js.cfg')
        run('fix', TEMPLATE, '-o', dst, '--callsign', 'EA7JRS-10', '--lat', '3631.20N', '--lon', '00612.30W')
        code, out = run('check', '--json', dst)
        d = json.loads(out)
        self.assertEqual(d['summary']['callsign'], 'EA7JRS-10')
        self.assertTrue(d['summary']['digipeater']['on'])
        self.assertTrue(d['summary']['igate']['passcode_ok'])
        self.assertEqual(d['summary']['digipeater']['rules'][0]['n_max'], 2)
        self.assertIsNone(d['summary']['weather']['station'])
        self.assertNotIn('admin', json.dumps(d['summary']).replace('"user": "admin"', ''))
        self.assertEqual(d['counts']['error'], 0)


if __name__ == '__main__':
    unittest.main()
