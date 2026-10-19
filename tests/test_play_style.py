from pathlib import Path
import json
import runpy
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'live/includes.chroot'


class PlayTests(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(LIVE / 'usr/local/bin/erodist-play'))

    def test_installed_tools(self):
        with patch('shutil.which', side_effect=lambda name: '/usr/bin/' + name):
            self.assertEqual(self.module['tool_command']('obs'), ['/usr/bin/obs'])
            self.assertEqual(self.module['tool_command']('gamepad'), ['/usr/bin/jstest-gtk'])

    def test_steam_games_path(self):
        with patch('shutil.which', return_value=None), patch('os.access', return_value=True):
            self.assertEqual(self.module['tool_command']('steam'), ['/usr/games/steam'])

    def test_missing_tool_does_not_install(self):
        with patch('shutil.which', return_value=None), patch('os.access', return_value=False), patch('subprocess.Popen') as spawn:
            for key in ['steam', 'obs', 'gamepad']:
                self.assertIsNone(self.module['tool_command'](key))
                self.assertEqual(self.module['catalog_command'](key), ['erodist-apps', '--app', key])
            spawn.assert_not_called()

    def test_unknown_tool_rejected(self):
        with self.assertRaises(KeyError):
            self.module['tool_command']('steam; rm -rf something')

    def test_catalog_bundles(self):
        catalog = json.loads((LIVE / 'usr/share/erodist/apps.json').read_text())
        self.assertIn('steam-installer', catalog['steam']['packages'])
        self.assertIn('mesa-vulkan-drivers:i386', catalog['steam']['packages'])
        self.assertIn('steam-devices', catalog['gamepad']['packages'])
        self.assertEqual(catalog['obs']['packages'], ['obs-studio'])
        image_packages = (ROOT / 'live/package-lists/desktop.list.chroot').read_text().splitlines()
        for name in ['steam-installer', 'obs-studio', 'jstest-gtk', 'kdeconnect', 'albert', 'ulauncher']:
            self.assertNotIn(name, image_packages)

    def test_docs_and_no_auto_record(self):
        for guide in ['gaming.html', 'recording.html']:
            self.assertTrue((LIVE / 'usr/share/erodist' / guide).is_file())
        source = (LIVE / 'usr/local/bin/erodist-play').read_text()
        for forbidden in ['--startrecording', '--startstreaming', 'shell=True', 'password']:
            self.assertNotIn(forbidden, source)


class StyleTests(unittest.TestCase):
    def test_theme_references(self):
        css = LIVE / 'usr/share/themes/EroDist-Black/gtk-3.0/gtk.css'
        self.assertIn('Arc-Dark/gtk-3.0/gtk.css', css.read_text())
        self.assertIn('EroDist-Black', (LIVE / 'etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml').read_text())
        self.assertIn('EroDist-Black', (LIVE / 'etc/lightdm/lightdm-gtk-greeter.conf.d/50-erodist.conf').read_text())

    def test_panel_translucency(self):
        tree = ET.parse(LIVE / 'etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml')
        panel = tree.find("./property[@name='panels']/property[@name='panel-1']")
        properties = {p.attrib['name']: p.attrib.get('value') for p in panel.findall('property')}
        self.assertEqual(properties['background-style'], '1')
        color = panel.find("property[@name='background-rgba']")
        self.assertEqual(color.attrib['type'], 'array')
        self.assertEqual([float(v.attrib['value']) for v in color], [0.039216, 0.039216, 0.039216, 0.9])

    def test_terminal_theme(self):
        from configparser import ConfigParser
        config = ConfigParser()
        config.read(LIVE / 'etc/xdg/xfce4/terminal/terminalrc')
        self.assertEqual(config['Configuration']['ColorBackground'], '#101010')
