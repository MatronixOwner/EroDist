import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / 'packages/erodist-system'
INSTALLER = ROOT / 'packages/erodist-installer'
sys.path.insert(0, str(SYSTEM / 'usr/lib/python3/dist-packages'))
from erodist.editions import catalog, validate_selection, apt_install_command
from erodist import info
loader = importlib.machinery.SourceFileLoader('provision', str(INSTALLER / 'usr/lib/erodist/provision-edition'))
spec = importlib.util.spec_from_loader('provision', loader)
worker = importlib.util.module_from_spec(spec)
loader.exec_module(worker)


class EditionTests(unittest.TestCase):
    def test_catalog(self):
        entries = catalog(SYSTEM / 'usr/share/erodist/editions.json')
        self.assertEqual(entries['home']['packages'], [])
        self.assertIn('steam-installer', entries['pro']['packages'])
        self.assertIn('mesa-vulkan-drivers:i386', entries['pro']['packages'])
        for item in ('git', 'python3-venv', 'godot3', 'blender'):
            self.assertIn(item, entries['program']['packages'])
        self.assertTrue(entries['program']['requires_network'])

    def test_selection(self):
        for key in ('home', 'program'):
            self.assertEqual(validate_selection({'edition': key, 'steam_terms': False}), key)
        self.assertEqual(validate_selection({'edition': 'pro', 'steam_terms': True}), 'pro')
        for data in (None, {}, {'edition': 'pro', 'steam_terms': False},
                     {'edition': 'home', 'steam_terms': 1},
                     {'edition': 'enterprise', 'steam_terms': True},
                     {'edition': 'home', 'steam_terms': False, 'cmd': 'anything'}):
            with self.assertRaises(ValueError):
                validate_selection(data)

    def test_catalog_rejects_arguments(self):
        entries = json.loads((SYSTEM / 'usr/share/erodist/editions.json').read_text())
        entries['pro']['packages'] = ['--allow-unauthenticated']
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'catalog.json'
            path.write_text(json.dumps(entries))
            with self.assertRaises(ValueError):
                catalog(path)

    def test_apt_no_removal_or_shell(self):
        command = apt_install_command(['git', 'godot3'])
        self.assertIn('--no-remove', command)
        self.assertEqual(command[-3:], ['--', 'git', 'godot3'])
        self.assertNotIn('--allow-unauthenticated', command)

    def test_worker_refuses_unmounted_target(self):
        with patch.object(worker.os, 'geteuid', return_value=0), patch.object(worker.os.path, 'ismount', return_value=False), patch.object(sys, 'argv', ['provision-edition']):
            with self.assertRaises(SystemExit):
                worker.main()

    def test_worker_refuses_unprivileged(self):
        with patch.object(worker.os, 'geteuid', return_value=1000), patch.object(sys, 'argv', ['provision-edition']):
            with self.assertRaises(SystemExit):
                worker.main()

    def test_marker_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'var/lib/erodist/installation.json'
            for status in ('installing', 'failed', 'complete'):
                worker.atomic_json(path, {'edition': 'program', 'status': status})
                self.assertEqual(json.loads(path.read_text())['status'], status)
                self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_installer_package_is_live_only(self):
        build = (ROOT / 'scripts/build.sh').read_text()
        self.assertIn("printf '\\nerodist-installer\\n'", build)
        self.assertIn('filesystem.manifest-remove', build)
        plugin = (INSTALLER / 'usr/lib/ubiquity/plugins/ubi-erodist.py').read_text()
        self.assertIn("BEFORE = 'partman'", plugin)
        self.assertIn('install_misc.chroot_setup(target)', plugin)
        self.assertIn('install_misc.chroot_cleanup(target)', plugin)
        self.assertNotIn('mkfs', plugin)

    def test_identity(self):
        base = json.loads((SYSTEM / 'usr/share/erodist/base.json').read_text())
        self.assertEqual(base['creator'], 'd50130483-ship-it')
        self.assertEqual(base['edition'], 'live')
        self.assertEqual(base['version'], '1.0.0-rc2-mint1')

    def test_worker_status_tracks_success_and_failure(self):
        entries = catalog(SYSTEM / 'usr/share/erodist/editions.json')
        for edition, fail in [('home', False), ('program', False), ('pro', False), ('program', True)]:
            with self.subTest(edition=edition, fail=fail), tempfile.TemporaryDirectory() as temp:
                target = Path(temp)
                base = target / 'usr/share/erodist/base.json'
                base.parent.mkdir(parents=True)
                base.write_text('{}')
                selection = Mock()
                selection.stat.return_value = Mock(st_uid=0, st_mode=0o100600)
                selection.read_text.return_value = json.dumps({'edition': edition, 'steam_terms': edition == 'pro'})
                def command(*args, **kwargs):
                    if fail:
                        raise worker.subprocess.CalledProcessError(100, 'apt-get')
                with patch.object(worker, 'TARGET', target), patch.object(worker, 'SELECTION', selection), \
                     patch.object(worker.os, 'geteuid', return_value=0), \
                     patch.object(worker.os.path, 'ismount', return_value=True), \
                     patch.object(Path, 'resolve', return_value=Path('/target')), \
                     patch.object(worker, 'catalog', return_value=entries), \
                     patch.object(worker.shutil, 'disk_usage', return_value=Mock(free=100 * 1024**3)), \
                     patch.object(worker, 'run_in_target', side_effect=command) as run, \
                     patch.object(worker.subprocess, 'run', return_value=Mock(stdout='installed')), \
                     patch.object(sys, 'argv', ['provision-edition']):
                    result = worker.main()
                marker = json.loads((target / 'var/lib/erodist/installation.json').read_text())
                self.assertEqual(result, 1 if fail else 0)
                self.assertEqual(marker['status'], 'failed' if fail else 'complete')
                self.assertEqual(marker['edition'], edition)
                if edition == 'home':
                    run.assert_not_called()
                if edition == 'program' and not fail:
                    self.assertTrue((target / 'etc/dconf/db/erodist.d/70-program-terminal').exists())
