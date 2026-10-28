from pathlib import Path
import json
import unittest
import ast

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'packages/neon-system'

class NeonTests(unittest.TestCase):
    def test_no_legacy_gui_dependencies(self):
        control=(PKG/'DEBIAN/control').read_text()
        depends=next(line for line in control.splitlines() if line.startswith('Depends:'))
        self.assertIn('python3-pyside6.qtwidgets',depends)
        for name in ('cinnamon','mintupdate','ubiquity','gtk','python3-gi'):
            self.assertNotIn(name,depends)
        gui=(PKG/'usr/lib/python3/dist-packages/erodist_neon/settings.py').read_text()
        self.assertIn('PySide6.QtWidgets',gui)
        self.assertNotIn('gi.repository',gui)
        ast.parse(gui)

    def test_new_identity_and_assets(self):
        base=json.loads((PKG/'usr/share/erodist-neon/base.json').read_text())
        self.assertEqual(base['creator'],'d50130483-ship-it')
        self.assertIn('KDE neon',base['base'])
        look=json.loads((PKG/'usr/share/plasma/look-and-feel/org.erodist.desktop/metadata.json').read_text())
        self.assertEqual(look['KPlugin']['Id'],'org.erodist.desktop')
        self.assertTrue((PKG/'usr/share/erodist-neon/black-gradient.png').is_file())
        self.assertTrue((PKG/'usr/share/color-schemes/EroDistGraphite.colors').is_file())

    def test_editions_remain_installer_only(self):
        entries=json.loads((PKG/'usr/share/erodist-neon/editions.json').read_text())
        self.assertEqual(set(entries),{'home','pro','program'})
        self.assertIn('steam-installer',entries['pro']['packages'])
        self.assertIn('blender',entries['program']['packages'])
        self.assertIn('godot3',entries['program']['packages'])
        self.assertIn('kate',entries['program']['packages'])
        gui=(PKG/'usr/lib/python3/dist-packages/erodist_neon/settings.py').read_text()
        self.assertNotIn('apt-get',gui)
        self.assertNotIn('set_edition',gui)

    def test_migration_does_not_trigger_old_mint_build(self):
        workflow=(ROOT/'.github/workflows/iso.yml').read_text()
        self.assertNotIn('  push:\n',workflow)
        self.assertTrue((ROOT/'.github/workflows/neon.yml').is_file())
