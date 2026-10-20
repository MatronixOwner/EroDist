from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class InstallerLayoutSourceTests(unittest.TestCase):
    def test_one_vertical_scroll_container(self):
        source = (ROOT/'packages/erodist-installer/usr/lib/ubiquity/plugins/ubi-erodist.py').read_text()
        self.assertEqual(source.count('Gtk.ScrolledWindow()'), 1)
        self.assertIn('Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC', source)
        self.assertNotIn('set_min_content_height(220)', source)
        self.assertIn('set_width_chars(1)', source)
        self.assertIn('Pango.WrapMode.WORD_CHAR', source)
        self.assertIn('plugin_title = None', source)

    def test_debconf_templates_use_transport_safe_fallbacks(self):
        templates = (ROOT/'packages/erodist-installer/DEBIAN/templates').read_bytes()
        self.assertTrue(templates.isascii())
        self.assertIn(b'Description: EroDist edition', templates)

    def test_real_geometry_checks_gate_iso(self):
        workflow = (ROOT/'.github/workflows/iso.yml').read_text()
        self.assertIn('needs: installer-layout', workflow)
        configure = (ROOT/'scripts/configure-root.sh').read_text()
        self.assertIn('python3 /tmp/installer-layout.py', configure)
        geometry = (ROOT/'scripts/installer-layout.py').read_text()
        for case in ('800,600,10', '1024,768,10', '800,600,13'):
            self.assertIn(case, geometry)
        self.assertIn('Home hidden at startup', geometry)
