from pathlib import Path
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
THEME=ROOT/'packages/erodist-desktop/usr/share'

class GraphiteTests(unittest.TestCase):
 def test_new_plasma_theme_and_no_search_phone(self):
  meta=json.loads((THEME/'plasma/look-and-feel/org.erodist.graphite/metadata.json').read_text())
  self.assertEqual(meta['KPlugin']['Id'],'org.erodist.graphite')
  js=(THEME/'plasma/look-and-feel/org.erodist.graphite/contents/layouts/org.kde.plasma.desktop-layout.js').read_text()
  for wanted in ("panel.floating = true","panel.lengthMode = 'fit'","panel.location = 'bottom'","erodist-control-center"):
   self.assertIn(wanted,js)
  self.assertNotIn('kdeconnect',js)
  self.assertNotIn('milou',js)
 def test_native_login_no_authentication_changes(self):
  code=(ROOT/'scripts/desktop-theme-configure.py').read_text()
  self.assertIn('etc/plasmalogin.conf.d/90-erodist.conf',code)
  self.assertNotIn('pam.d/',code)
  self.assertNotIn('Autologin',code)
  self.assertNotIn('display-manager.service',code)
 def test_boot_prompt_and_payload_preservation(self):
  script=(THEME/'plymouth/themes/erodist/erodist.script').read_text()
  self.assertIn('SetDisplayPasswordFunction',script)
  self.assertIn('SetDisplayQuestionFunction',script)
  initrd=(ROOT/'scripts/desktop-initrd.sh').read_text()
  self.assertIn('original initrd payload preserved',initrd)
  self.assertIn('lsinitramfs',initrd)
 def test_vm_report_does_not_fake_install_or_hyperv(self):
  code=(ROOT/'scripts/desktop-vm-smoke.py').read_text()
  self.assertIn("'hyper_v_tested':False",code)
  self.assertIn("'disk_install_tested':False",code)
  self.assertIn("'center_observed':False",code)
