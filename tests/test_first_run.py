from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/erodist-system/usr/lib/python3/dist-packages'))
from erodist import onboarding, diagnostics, preflight


class FirstRunTests(unittest.TestCase):
    def test_welcome_only_after_complete_install(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'welcome.json'
            data = {'edition': 'program', 'status': 'complete'}
            self.assertTrue(onboarding.should_show(data, 'quiet splash', marker))
            self.assertFalse(onboarding.should_show(data, 'boot=casper quiet', marker))
            for state in ('failed', 'installing', 'unconfigured', 'live'):
                self.assertFalse(onboarding.should_show({**data, 'status': state}, '', marker))
            self.assertFalse(onboarding.should_show({'edition':'unknown', 'status':'complete'}, '', marker))
            onboarding.finish(marker)
            self.assertFalse(onboarding.should_show(data, '', marker))
            self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
            onboarding.finish(marker)  # Reopening/closing manually is idempotent.

    def test_relative_xdg_state_is_ignored(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.assertEqual(onboarding.marker_path(), Path.home() / '.local/state/erodist/welcome-complete.json')

    def test_report_saves_exact_preview_privately(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'report.txt'
            diagnostics.save_report(path, 'Только показанный текст\n')
            self.assertEqual(path.read_text(), 'Только показанный текст\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            diagnostics.save_report(path, 'Updated')
            self.assertEqual(path.read_text(), 'Updated')
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_report_does_not_follow_existing_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            original, chosen = Path(temp)/'original', Path(temp)/'chosen'
            original.write_text('Private file')
            chosen.symlink_to(original)
            diagnostics.save_report(chosen, 'Report')
            self.assertEqual(original.read_text(), 'Private file')
            self.assertFalse(chosen.is_symlink())
            self.assertEqual(chosen.read_text(), 'Report')

    def test_network_probe_success(self):
        response = Mock(status=206)
        response.read.return_value = b'-----BEGIN PGP SIGNED MESSAGE-----\n'
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        with patch.object(preflight, 'urlopen', return_value=context) as call:
            self.assertTrue(preflight.network_check()[0])
            self.assertEqual(call.call_args.kwargs['timeout'], 8)
            response.read.assert_called_once_with(256)

    def test_network_timeout_and_captive_portal_fail_closed(self):
        with patch.object(preflight, 'urlopen', side_effect=TimeoutError):
            self.assertFalse(preflight.network_check()[0])
        response = Mock(status=200)
        response.read.return_value = b'<html>Login to Wi-Fi</html>'
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        with patch.object(preflight, 'urlopen', return_value=context):
            self.assertFalse(preflight.network_check()[0])

    def test_network_probe_is_not_a_signature_verifier(self):
        # The UI may only call it connectivity; APT must still verify signed metadata.
        self.assertIn('https://archive.ubuntu.com/', preflight.PROBE_URL)
        source = (ROOT / 'packages/erodist-installer/usr/lib/erodist/provision-edition').read_text()
        self.assertIn('APT::Update::Error-Mode=any', source)
        self.assertNotIn('--allow-unauthenticated', source)
