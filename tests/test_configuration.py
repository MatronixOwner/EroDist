"""Dependency-free source checks; these are NOT boot/installation tests."""
import ast
import pathlib
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIVE = ROOT / 'live/includes.chroot'


class ConfigurationTests(unittest.TestCase):
    def test_python_syntax(self):
        ast.parse((LIVE / 'usr/local/bin/erodist-welcome').read_text())

    def test_shell_syntax(self):
        subprocess.run(['bash', '-n', str(ROOT / 'scripts/build.sh')], check=True)
        for path in list((LIVE / 'usr/local/bin').glob('*')) + list((ROOT / 'live/hooks/normal').glob('*')):
            if path.read_text().startswith('#!/bin/sh'):
                subprocess.run(['sh', '-n', str(path)], check=True)

    def test_xml(self):
        for path in LIVE.rglob('*'):
            if path.suffix in ('.xml', '.svg'):
                ET.parse(path)

    def test_launchers(self):
        for path in LIVE.rglob('*.desktop'):
            text = path.read_text()
            self.assertIn('[Desktop Entry]', text)
            command = next(line[5:].split()[0] for line in text.splitlines() if line.startswith('Exec='))
            self.assertTrue((LIVE / 'usr/local/bin' / command).is_file(), command)

    def test_versions(self):
        for name in ['scripts/build.sh', '.github/workflows/iso.yml', 'live/includes.chroot/usr/local/bin/erodist-report']:
            self.assertIn('0.2.0', (ROOT / name).read_text())
            self.assertNotIn('0.1.0', (ROOT / name).read_text())

    def test_report_private_and_local(self):
        text = (LIVE / 'usr/local/bin/erodist-report').read_text()
        self.assertIn('umask 077', text)
        self.assertNotIn('curl', text)
        self.assertNotIn('wget', text)

    def test_guide(self):
        self.assertTrue((LIVE / 'usr/share/erodist/guide.html').is_file())
