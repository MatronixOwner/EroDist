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
        for path in [*(LIVE / 'usr/local/bin').glob('*'), *(LIVE / 'usr/local/libexec').glob('*')]:
            if path.read_text().startswith('#!/usr/bin/python3'):
                ast.parse(path.read_text())

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
            self.assertTrue((LIVE / 'usr/local/bin' / command).is_file() or command in {'thunar', 'firefox-esr', 'flameshot'}, command)

    def test_versions(self):
        for name in ['scripts/build.sh', '.github/workflows/iso.yml', 'live/includes.chroot/usr/local/bin/erodist-report']:
            self.assertIn('0.3.0', (ROOT / name).read_text())
            self.assertNotIn('0.1.0', (ROOT / name).read_text())

    def test_report_private_and_local(self):
        text = (LIVE / 'usr/local/bin/erodist-report').read_text()
        self.assertIn('umask 077', text)
        self.assertNotIn('curl', text)
        self.assertNotIn('wget', text)

    def test_guide(self):
        self.assertTrue((LIVE / 'usr/share/erodist/guide.html').is_file())

    def test_catalog(self):
        import json
        catalog = json.loads((LIVE / 'usr/share/erodist/apps.json').read_text())
        self.assertEqual(catalog['python']['packages'], ['python3', 'python3-pip', 'python3-venv', 'idle'])
        for app in catalog.values():
            for package in app['packages']:
                self.assertRegex(package, r'^[a-z0-9][a-z0-9+.-]*$')

    def test_installer_allowlist(self):
        import runpy
        from unittest.mock import patch
        module = runpy.run_path(str(LIVE / 'usr/local/libexec/erodist-install'))
        contents = (LIVE / 'usr/share/erodist/apps.json').read_text()
        with patch('pathlib.Path.read_text', return_value=contents):
            self.assertIn('python3-venv', module['packages_for']('python'))
            for key in ['../../etc/passwd', '--allow-unauthenticated', 'python;id', 'unknown']:
                with self.assertRaises(ValueError):
                    module['packages_for'](key)

    def test_wallpaper_references(self):
        wallpaper = '/usr/share/backgrounds/erodist/black-gradient.png'
        self.assertTrue((LIVE / wallpaper.lstrip('/')).is_file())
        self.assertIn(wallpaper, (LIVE / 'usr/local/bin/erodist-session').read_text())
