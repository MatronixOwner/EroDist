import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mint_common import checksum_for, sha256, update_md5
spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package-release.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class MintTests(unittest.TestCase):
    def test_source_is_pinned_cinnamon(self):
        config = json.loads((ROOT / 'mint/source.json').read_text())
        self.assertEqual(config['edition'], 'cinnamon')
        self.assertEqual(config['mint_version'], '22.3')
        self.assertEqual(config['signing_fingerprint'], '27DEB15644C6B3CF3BD7D291300F846BA25BAE09')

    def test_checksum_exact_selection(self):
        value = 'a' * 64
        self.assertEqual(checksum_for(f'{value} *test.iso\n', 'test.iso'), value)
        for text in ['', 'oops test.iso', f'{value} test.iso\n{value} test.iso']:
            with self.assertRaises(ValueError):
                checksum_for(text, 'test.iso')

    def test_md5_only_changed_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file'
            path.write_bytes(b'updated')
            result = update_md5('a'*32+'  ./keep\n'+'b'*32+'  ./casper/filesystem.squashfs\n', {'casper/filesystem.squashfs':path})
            self.assertIn('a'*32+'  ./keep', result)
            self.assertIn(hashlib.md5(b'updated').hexdigest(), result)
            self.assertNotIn('b'*32, result)

    def test_split_and_linux_assembly(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'test.iso'
            data = bytes(range(256)) * 8
            iso.write_bytes(data)
            parts = packager.package_iso(iso, part_size=600, limit=1000)
            self.assertEqual(len(parts), 4)
            self.assertFalse(iso.exists())
            subprocess.run(['bash', str(Path(temp) / 'assemble.sh')], check=True, capture_output=True)
            self.assertEqual(iso.read_bytes(), data)
            self.assertEqual(sha256(iso), hashlib.sha256(data).hexdigest())
            retry = subprocess.run(['bash', str(Path(temp) / 'assemble.sh')], capture_output=True)
            self.assertNotEqual(retry.returncode, 0)

    def test_corrupt_part_blocks_assembly(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'test.iso'
            iso.write_bytes(b'abcdef' * 30)
            parts = packager.package_iso(iso, part_size=100, limit=150)
            (Path(temp) / parts[0]['name']).write_bytes(b'broken')
            result = subprocess.run(['bash', str(Path(temp) / 'assemble.sh')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(iso.exists())

    def test_small_iso_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            iso = Path(temp) / 'small.iso'
            iso.write_bytes(b'small')
            self.assertEqual(packager.package_iso(iso, limit=100), [])
            self.assertTrue(iso.exists())
            self.assertTrue((Path(temp) / 'SHA256SUMS').exists())

    def test_minimal_overlay(self):
        overlay = ROOT / 'mint/overlay'
        self.assertFalse((ROOT / 'archiso').exists())
        for disallowed in ['etc/os-release', 'etc/passwd', 'etc/shadow', 'etc/apt/sources.list', 'usr/local/bin/erodist-installer']:
            self.assertFalse((overlay / disallowed).exists())
        self.assertIn('Mint-Y-Dark', (overlay / 'etc/dconf/db/erodist.d/50-erodist').read_text())
        self.assertTrue((overlay / 'usr/share/backgrounds/erodist/black-gradient.png').is_file())

    def test_verification_before_extraction(self):
        source = (ROOT / 'scripts/build.sh').read_text()
        self.assertLess(source.index('gpg --batch --verify'), source.index('unsquashfs -d'))
        self.assertIn('checksum mismatch', source.lower())
        self.assertIn('-boot_image any replay', source)
        self.assertNotIn('apt-get install', source)
        subprocess.run(['bash', '-n', str(ROOT / 'scripts/build.sh')], check=True)
