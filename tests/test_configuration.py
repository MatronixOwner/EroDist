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
        for path in list((LIVE / 'usr/local/bin').glob('*')) + list((LIVE / 'usr/local/libexec').glob('*')) + list((ROOT / 'live/hooks/normal').glob('*')):
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
            self.assertIn('0.5.0', (ROOT / name).read_text())
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
                self.assertRegex(package, r'^[a-z0-9][a-z0-9+.-]*(?::(?:amd64|i386))?$')

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

    def test_system_installer_live_guard(self):
        # Test the pure guard without requiring GTK on the source-test runner.
        tree = ast.parse((LIVE / 'usr/local/bin/erodist-installer').read_text())
        guard = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'is_live')
        scope = {}
        exec(compile(ast.Module(body=[guard], type_ignores=[]), '<guard>', 'exec'), scope)
        for cmdline in ['quiet', 'notboot=live', 'boot=live-persistence', '']:
            self.assertFalse(scope['is_live'](cmdline))
        self.assertTrue(scope['is_live']('quiet boot=live components'))

    def test_system_installer_authorization(self):
        root_helper = (LIVE / 'usr/local/libexec/erodist-system-installer').read_text()
        self.assertIn('flock -n 9', root_helper)
        self.assertIn('trap restore_fstab EXIT', root_helper)
        self.assertIn('[ "$#" -eq 0 ]', root_helper)
        policy = ET.parse(LIVE / 'usr/share/polkit-1/actions/org.erodist.installer.policy')
        action = policy.find('action')
        self.assertEqual(action.find('defaults/allow_active').text, 'auth_admin')
        annotations = {n.attrib['key']: n.text for n in action.findall('annotate')}
        self.assertEqual(annotations['org.freedesktop.policykit.exec.path'], '/usr/local/libexec/erodist-system-installer')

    def test_installer_branding_assets(self):
        branding = LIVE / 'etc/calamares/branding/erodist'
        for asset in ['branding.desc', 'logo.svg', 'welcome.svg', 'show.qml', 'stylesheet.qss']:
            self.assertTrue((branding / asset).is_file(), asset)
        hook = (ROOT / 'live/hooks/normal/0600-erodist-installer.hook.chroot').read_text()
        self.assertIn("'prompt-install': True", hook)
        self.assertIn("partition['initialPartitioningChoice'] = 'none'", hook)
        welcome = (LIVE / 'usr/local/bin/erodist-welcome').read_text()
        self.assertIn("self.launch(['erodist-installer'])", welcome)
        self.assertNotIn("['xfce4-session-logout', '--reboot']", welcome)
