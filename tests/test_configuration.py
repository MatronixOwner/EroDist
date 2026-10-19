"""Source tests only. Boot/installation need a separate VM test."""
import ast
import json
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'archiso/airootfs'


class ConfigurationTests(unittest.TestCase):
    def test_python_syntax(self):
        for path in [*(LIVE / 'usr/local/bin').glob('*'), *(LIVE / 'usr/local/libexec').glob('*'), *(LIVE / 'usr/share/erodist').glob('*.py'), ROOT / 'scripts/check-arch.py']:
            if path.suffix == '.py' or path.read_text().startswith('#!/usr/bin/python3'):
                ast.parse(path.read_text())

    def test_shell_syntax(self):
        subprocess.run(['bash', '-n', str(ROOT / 'scripts/build.sh')], check=True)
        for path in [*(LIVE / 'usr/local/bin').glob('*'), *(LIVE / 'usr/local/libexec').glob('*')]:
            if path.read_text().startswith(('#!/bin/sh', '#!/bin/bash')):
                subprocess.run(['bash', '-n', str(path)], check=True)

    def test_xml(self):
        for path in LIVE.rglob('*'):
            if path.suffix in ('.xml', '.svg', '.policy'):
                ET.parse(path)

    def test_launchers(self):
        for path in LIVE.rglob('*.desktop'):
            text = path.read_text()
            self.assertIn('[Desktop Entry]', text)
            command = next(line[5:].split()[0] for line in text.splitlines() if line.startswith('Exec='))
            self.assertTrue((LIVE / 'usr/local/bin' / command).is_file() or command in {'thunar', 'firefox', 'flameshot', '/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1'}, command)

    def test_arch_only_backend(self):
        for name in ['erodist-apps', 'erodist-updates']:
            text = (LIVE / 'usr/local/bin' / name).read_text()
            self.assertNotIn('apt-get', text)
            self.assertIn('pacman', text)
        text = (LIVE / 'usr/local/libexec/erodist-install').read_text()
        self.assertIn("'-Syu'", text)
        self.assertNotIn("'-Sy'", text)
        self.assertNotIn('--noconfirm', text)
        self.assertIn('zstd', (ROOT / 'scripts/build.sh').read_text())

    def test_catalog_allowlist(self):
        import runpy
        from unittest.mock import patch
        module = runpy.run_path(str(LIVE / 'usr/local/libexec/erodist-install'))
        contents = (LIVE / 'usr/share/erodist/apps.json').read_text()
        catalog = json.loads(contents)
        with patch('pathlib.Path.read_text', return_value=contents):
            for key, entry in catalog.items():
                self.assertEqual(module['packages_for'](key), entry['packages'])
            for key in ['../../etc/passwd', '--overwrite', 'python;id', 'unknown']:
                with self.assertRaises(ValueError):
                    module['packages_for'](key)
        self.assertEqual(catalog['python']['packages'], ['python', 'python-pip', 'tk'])

    def test_installer_has_no_disk_or_credentials_preset(self):
        config = json.loads((LIVE / 'etc/erodist/archinstall.json').read_text())
        for key in ['disk_config', 'disk_layouts', '!users', 'users', '!root-password', 'silent']:
            self.assertNotIn(key, config)
        self.assertEqual(config['profile_config']['profile']['main'], 'EroDist XFCE')
        source = (LIVE / 'usr/local/libexec/erodist-system-installer').read_text()
        self.assertIn('/usr/bin/archinstall', source)
        self.assertNotIn('--silent', source)
        self.assertNotIn('mkfs', source)
        self.assertIn('flock -n 9', source)

    def test_target_excludes_live_account(self):
        text = (ROOT / 'scripts/build.sh').read_text()
        self.assertIn('target-overlay', text)
        self.assertIn('rm -f "$PAYLOAD/usr/local/libexec/erodist-live-setup"', text)
        profile = (LIVE / 'usr/share/erodist/archinstall-profile.py').read_text()
        self.assertNotIn('chpasswd', profile)
        self.assertNotIn('tester', profile)

    def test_live_guard(self):
        tree = ast.parse((LIVE / 'usr/local/bin/erodist-installer').read_text())
        guard = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'is_live')
        scope = {}
        exec(compile(ast.Module(body=[guard], type_ignores=[]), '<guard>', 'exec'), scope)
        for cmdline in ['quiet', 'boot=live', 'notarchisobasedir=x', '']:
            self.assertFalse(scope['is_live'](cmdline))
        self.assertTrue(scope['is_live']('quiet archisobasedir=erodist'))

    def test_wallpaper_and_version(self):
        self.assertTrue((LIVE / 'usr/share/backgrounds/erodist/black-gradient.png').is_file())
        self.assertEqual((LIVE / 'etc/erodist-version').read_text().strip(), '0.7.0-arch1')
