import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'packages/erodist-control-center/usr/lib/python3/dist-packages/erodist_control_center/model.py'
spec=importlib.util.spec_from_file_location('control_center_model',PATH)
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

class ControlCenterTests(unittest.TestCase):
 def test_no_retired_editions_or_privileged_commands(self):
  for entries in model.SECTIONS.values():
   for title,description,icon,command in entries:
    self.assertIn(command[0],{'systemsettings','plasma-discover','plasma-apply-icontheme'})
    self.assertTrue(all(isinstance(arg,str) for arg in command))
  for filename in PATH.parent.glob('*.py'):
   code=filename.read_text()
   for legacy in ('erodist_neon','erodist.editions','Home / Pro','pkexec','apt-get','sudo'):
    self.assertNotIn(legacy,code)
 def test_report_is_local_summary(self):
  text=model.system_report()
  self.assertIn('Центр настроек EroDist',text)
  self.assertIn('Система:',text)
  for field in ('hostname:','MAC:','IP:','serial:'):
   self.assertNotIn(field,text)
 def test_atomic_private_export(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'report.txt';model.save_report(p,'hello')
   self.assertEqual(p.read_text(),'hello')
   self.assertEqual(p.stat().st_mode&0o777,0o600)
   model.save_report(p,'new');self.assertEqual(p.read_text(),'new')
   target=Path(directory)/'target';target.write_text('untouched')
   p.unlink();p.symlink_to(target)
   model.save_report(p,'safe')
   self.assertEqual(target.read_text(),'untouched')
   self.assertFalse(p.is_symlink())
   self.assertEqual(list(Path(directory).glob('.erodist-*')),[])
 def test_original_svg_assets_and_fallback(self):
  theme=ROOT/'packages/erodist-icons/usr/share/icons/EroDist'
  self.assertIn('Inherits=breeze-dark,breeze,hicolor',(theme/'index.theme').read_text())
  for name in ('files','terminal','browser','software','editor','appearance','display','network'):
   node=ET.parse(theme/'scalable/apps'/f'erodist-{name}.svg').getroot()
   self.assertEqual(node.attrib['viewBox'],'0 0 256 256')
 def test_binary_and_desktop_name_match(self):
  pkg=ROOT/'packages/erodist-control-center'
  desktop=(pkg/'usr/share/applications/erodist-control-center.desktop').read_text()
  self.assertIn('Exec=erodist-control-center',desktop)
  self.assertTrue((pkg/'usr/bin/erodist-control-center').is_file())
