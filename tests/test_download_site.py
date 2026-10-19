import hashlib
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
read_text = Path.read_text

def text(path, *args, **kwargs):
    return 'test-upload-token' if path.name == 'upload-token' else read_text(path, *args, **kwargs)

spec = importlib.util.spec_from_file_location('download_site', ROOT / 'scripts/download-server.py')
site = importlib.util.module_from_spec(spec)
with patch.object(Path, 'read_text', text):
    spec.loader.exec_module(site)

class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        self.patch = patch.multiple(site, PART=folder/'test.upload', ISO=folder/'test.iso', SIZE=8,
                                    STATE={'ready': False, 'sha256': None})
        self.patch.start()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), site.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.payload = b'ISO-test'
        self.sha = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.patch.stop()
        self.temp.cleanup()

    def request(self, path, data=None, headers=None, method=None):
        return urlopen(Request(self.url+path, data=data, headers=headers or {}, method=method), timeout=5)

    def post(self, path, data):
        with self.request(path, data, {'Authorization': 'Bearer test-upload-token'}) as response:
            return json.load(response)

    def publish(self):
        value = {'output': site.NAME, 'sha256': self.sha, 'parts': [{'size': 8}]}
        self.post('/api/begin', json.dumps(value).encode())
        self.post('/api/chunk?offset=0', self.payload)
        # Retrying an already committed chunk must not duplicate bytes.
        self.post('/api/chunk?offset=0', self.payload)
        self.post('/api/finalize', b'')

    def test_not_ready_and_unauthorized(self):
        for path, data, status in [('/download/'+site.NAME, None, 503), ('/api/begin', b'{}', 403)]:
            with self.assertRaises(HTTPError) as caught:
                self.request(path, data)
            self.assertEqual(caught.exception.code, status)
            caught.exception.close()

    def test_verified_download_and_ranges(self):
        self.publish()
        with self.request('/download/'+site.NAME) as response:
            self.assertEqual(response.read(), self.payload)
            self.assertIn('attachment', response.headers['Content-Disposition'])
        for requested, expected in [('bytes=0-2', b'ISO'), ('bytes=4-', b'test'), ('bytes=-4', b'test')]:
            with self.request('/download/'+site.NAME, headers={'Range': requested}) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), expected)
        with self.request('/download/'+site.NAME, method='HEAD') as response:
            self.assertEqual(response.headers['Content-Length'], '8')
            self.assertEqual(response.read(), b'')
        with self.assertRaises(HTTPError) as caught:
            self.request('/download/'+site.NAME, headers={'Range':'bytes=99-'})
        self.assertEqual(caught.exception.code, 416)
        caught.exception.close()
        with self.assertRaises(HTTPError) as caught:
            self.post('/api/chunk?offset=8', b'')
        self.assertEqual(caught.exception.code, 409)
        caught.exception.close()

    def test_bad_digest_never_published(self):
        value = {'output': site.NAME, 'sha256': '0'*64, 'parts':[{'size':8}]}
        self.post('/api/begin', json.dumps(value).encode())
        self.post('/api/chunk?offset=0', self.payload)
        with self.assertRaises(HTTPError) as caught:
            self.post('/api/finalize', b'')
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        self.assertFalse(site.STATE['ready'])
        self.assertFalse(site.ISO.exists())
