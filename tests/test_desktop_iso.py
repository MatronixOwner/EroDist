from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DesktopISOTests(unittest.TestCase):
    def test_required_packages_are_in_image_plan(self):
        image=json.loads((ROOT/'neon/image.json').read_text())
        self.assertTrue({'erodist-control-center','erodist-icons','wine','wine64','wine32:i386','fonts-wine'}<=set(image['packages']))
        self.assertEqual(image['default_icon_theme'],'EroDist')
        self.assertNotIn('/',image['output'])
        self.assertTrue(image['output'].endswith('.iso'))

    def test_build_preserves_boot_and_checks_roundtrip(self):
        build=(ROOT/'scripts/desktop-iso.sh').read_text()
        for safety in ('ERODIST_WITH_WINE=1','/proc/self/mountinfo','-boot_image any replay','md5sum --quiet -c','cmp "$WORK/upstream-vmlinuz"','cmp "$WORK/upstream-initrd"','final-status.txt','full_vm_install_tested'):
            self.assertIn(safety,build)
        self.assertNotIn('configure-root.sh',build)
        self.assertNotIn('ubi-erodist',build)

    def test_wine_no_shared_prefix_or_downloaded_exe(self):
        smoke=(ROOT/'scripts/wine-smoke.py').read_text()
        self.assertIn("('win64', 'win32')",smoke)
        self.assertIn('WINEPREFIX=',smoke)
        self.assertIn("['wineserver', '-k']",smoke)
        self.assertIn("Path('/root/.wine')",smoke)
        self.assertNotIn('https://',smoke)
