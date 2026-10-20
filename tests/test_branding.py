import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/erodist-system/usr/lib/python3/dist-packages'))
from erodist.branding import candidates, is_vendor_art


class BrandingTests(unittest.TestCase):
    def test_branding_targets(self):
        for path in ('usr/share/icons/Mint-Y/apps/32/linuxmint-logo.svg',
                     'usr/share/icons/hicolor/scalable/apps/mintupdate.svg',
                     'usr/share/pixmaps/distributor-logo.png',
                     'usr/share/icons/Mint-Y/places/start-here-symbolic.svg',
                     'usr/share/linuxmint/common/artwork/logo.svg',
                     'usr/share/plymouth/themes/mint-logo/logo.png',
                     'usr/share/pixmaps/ubiquity.png',
                     'usr/share/backgrounds/linuxmint/default_background.jpg'):
            self.assertTrue(is_vendor_art(path), path)

    def test_does_not_replace_normal_icons_or_backup_credits(self):
        for path in ('usr/share/icons/Mint-Y/apps/32/firefox.svg',
                     'usr/share/icons/Mint-Y/apps/32/distributor-logo-fedora.svg',
                     'usr/share/linuxmint/mintlocale/flags/ru.png',
                     'usr/share/doc/mint-artwork/copyright',
                     'usr/share/pixmaps/linuxmint-logo.svg.erodist-original',
                     'usr/share/icons/hicolor/scalable/apps/erodist.svg',
                     'etc/apt/sources.list'):
            self.assertFalse(is_vendor_art(path), path)

    def test_scans_only_visual_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('usr/share/pixmaps/mint-logo.png', 'etc/apt/mint-logo.png', 'usr/share/doc/mint-logo.png'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(candidates(root), ['/usr/share/pixmaps/mint-logo.png'])

    def test_boot_images_do_not_include_boot_code(self):
        # Import only the selector; no Pillow dependency needed for selection tests.
        source = (ROOT/'scripts/brand-iso.py').read_text()
        namespace = {'__name__': 'test_import'}
        exec(compile(source.replace('from PIL import Image', ''), 'brand-iso.py', 'exec'), namespace)
        for name in ('/boot/grub/splash.png', '/isolinux/splash.jpg'):
            self.assertTrue(namespace['boot_image'](name))
        for name in ('/boot/grub/grub.cfg', '/casper/vmlinuz', '/EFI/BOOT/BOOTX64.EFI', '/boot/grub/font.pf2'):
            self.assertFalse(namespace['boot_image'](name))

    def test_managed_diversions_and_initramfs(self):
        module = (ROOT/'packages/erodist-system/usr/lib/python3/dist-packages/erodist/branding.py').read_text()
        self.assertIn("'dpkg-divert'", module)
        self.assertIn("'.erodist-original'", module)
        self.assertIn('def restore():', module)
        script = (ROOT/'scripts/configure-root.sh').read_text()
        self.assertIn('mkinitramfs -o /tmp/erodist-initrd "$KERNEL"', script)
        self.assertIn("grep -q 'scripts/casper'", script)
        self.assertIn('BRANDING-REPORT.json', script)
