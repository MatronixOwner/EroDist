import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'packages/erodist-control-center/usr/lib/python3/dist-packages/erodist_control_center/wine.py'
spec=importlib.util.spec_from_file_location('wine_actions',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class WineActionsTests(unittest.TestCase):
 def test_root_refused(self):
  with patch.object(m.os,'geteuid',return_value=0):
   with self.assertRaises(m.WineActionError):m.command_for('configure')
 def test_tools(self):
  with patch.object(m.os,'geteuid',return_value=1000),patch.object(m.shutil,'which',return_value='/usr/bin/wine'):
   self.assertEqual(m.command_for('configure'),('/usr/bin/wine',['winecfg']))
   self.assertEqual(m.command_for('uninstall'),('/usr/bin/wine',['uninstaller']))
   with self.assertRaises(m.WineActionError):m.command_for('delete-prefix')
 def test_missing_wine(self):
  with patch.object(m.os,'geteuid',return_value=1000),patch.object(m.shutil,'which',return_value=None):
   with self.assertRaises(m.WineActionError):m.command_for('configure')
 def test_exe_validated_as_single_absolute_argument(self):
  with tempfile.TemporaryDirectory() as d,patch.object(m.os,'geteuid',return_value=1000),patch.object(m.shutil,'which',return_value='/usr/bin/wine'):
   p=Path(d)/'- strange ; file.EXE';p.write_bytes(b'MZtest')
   self.assertEqual(m.command_for('run',p),('/usr/bin/wine',[str(p)]))
   p.write_bytes(b'not exe')
   with self.assertRaises(m.WineActionError):m.command_for('run',p)
   with self.assertRaises(m.WineActionError):m.command_for('run',Path(d))
