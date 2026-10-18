"""Pure-function tests: do not execute Windows files or require GTK/root."""
from pathlib import Path
import runpy
import struct
import tempfile
import unittest
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / 'live/includes.chroot/usr/local/bin'


class AboutTests(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(BIN / 'erodist-about'))

    def test_memory(self):
        self.assertEqual(self.module['memory_gib']('MemTotal: 4194304 kB\n'), '4.0 ГиБ')
        self.assertEqual(self.module['memory_gib'](''), 'Не определено')

    def test_cpu(self):
        self.assertEqual(self.module['cpu_name']('model name\t: Test CPU\n'), 'Test CPU')

    def test_graphics_failure(self):
        with patch('subprocess.run', side_effect=OSError('missing')):
            self.assertIn('Не удалось', self.module['graphics']())

    def test_graphics_filter(self):
        import subprocess
        result = subprocess.CompletedProcess([], 0, '00:01 VGA compatible controller: Test GPU\n\tKernel driver in use: test\n00:02 Network controller: private\n')
        with patch('subprocess.run', return_value=result):
            output = self.module['graphics']()
        self.assertIn('Test GPU', output)
        self.assertIn('driver in use', output)
        self.assertNotIn('private', output)


class WineTests(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(BIN / 'erodist-wine'))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def executable(self, name='program.exe', machine=0x8664):
        path = Path(self.temp.name) / name
        data = bytearray(128)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 60, 64)
        data[64:68] = b'PE\0\0'
        struct.pack_into('<H', data, 68, machine)
        path.write_bytes(data)
        return path

    def test_x86_and_x64(self):
        for machine in [0x14c, 0x8664]:
            path = self.executable(machine=machine)
            self.assertEqual(self.module['validate_exe'](path), path.resolve())

    def test_filename_is_single_argument(self):
        path = self.executable('test ; $(touch unexpected) файл.EXE')
        valid = self.module['validate_exe'](path)
        self.assertEqual(self.module['command_for'](valid), ['/usr/bin/wine', str(path)])
        self.assertFalse((Path(self.temp.name) / 'unexpected').exists())

    def test_reject_arm(self):
        with self.assertRaises(ValueError):
            self.module['validate_exe'](self.executable(machine=0xaa64))

    def test_reject_non_exe(self):
        with self.assertRaises(ValueError):
            self.module['validate_exe'](self.executable('script.txt'))

    def test_reject_invalid_header(self):
        path = Path(self.temp.name) / 'bad.exe'
        for data in [b'#!/bin/sh\n', b'MZ' + bytes(62)]:
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                self.module['validate_exe'](path)

    def test_reject_missing_file(self):
        with self.assertRaises(OSError):
            self.module['validate_exe'](Path(self.temp.name) / 'missing.exe')

    def test_wine_catalog_multiarch(self):
        import json
        root = BIN.parents[2]
        catalog = json.loads((root / 'usr/share/erodist/apps.json').read_text())
        self.assertIn('wine32:i386', catalog['wine']['packages'])
        self.assertIn('wine64', catalog['wine']['packages'])

    def test_no_privilege_escalation(self):
        source = (BIN / 'erodist-wine').read_text()
        self.assertIn('os.geteuid() == 0', source)
        self.assertNotIn('shell=True', source)
        self.assertNotIn("['sudo'", source)
        self.assertNotIn("['pkexec'", source)
