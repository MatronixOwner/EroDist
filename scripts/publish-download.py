"""Actions-only: assemble the published release and deliver to the session server."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import sys

event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
inputs = event.get('inputs', {})
url = (inputs.get('upload_url') or json.loads(Path('site/deploy.json').read_text())['url']).rstrip('/')
token = inputs.get('upload_token') or os.environ['GH_TOKEN']
print('::add-mask::' + token, flush=True)
if not url.startswith('https://8080-') or not url.endswith('.e2b.app'):
    raise ValueError('Not a session preview URL')
try:
    with urlopen(Request(url + '/api/status', headers={'User-Agent': 'Mozilla/5.0 EroDist-Transfer'}), timeout=30) as response:
        print('Public server status:', response.status, response.read(2000).decode(), flush=True)
except HTTPError as exc:
    print('Public endpoint:', exc.code, exc.headers.get('Server'), exc.read(3000).decode(errors='replace'), flush=True)
    raise
if '[probe-download]' in event.get('head_commit', {}).get('message', ''):
    sys.exit(0)
subprocess.run(['gh', 'release', 'download', 'test-0.9.0-mint1-22-1',
                '--pattern', '*.iso.part*', '--pattern', 'ASSEMBLY.json', '--pattern', 'assemble.sh',
                '--dir', 'published-iso'], check=True)
subprocess.run(['bash', 'assemble.sh'], cwd='published-iso', check=True)
folder = Path('published-iso')
manifest = (folder / 'ASSEMBLY.json').read_bytes()

def post(route, data):
    for attempt in range(5):
        try:
            req = Request(url + route, data=data, headers={'Authorization': 'Bearer ' + token,
                          'Content-Type': 'application/octet-stream', 'User-Agent': 'Mozilla/5.0 EroDist-Transfer'}, method='POST')
            with urlopen(req, timeout=180) as response:
                return json.load(response)
        except OSError:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))

state = post('/api/begin', manifest)
file = folder / json.loads(manifest)['output']
with file.open('rb') as stream:
    offset = state['bytes']
    stream.seek(offset)
    while data := stream.read(8 * 1024**2):
        state = post('/api/chunk?offset=' + str(offset), data)
        offset += len(data)
        if offset % (8 * 1024**2 * 20) == 0:
            print('Uploaded', offset, 'bytes', flush=True)
print(post('/api/finalize', b''), flush=True)

# Confirm that the public proxy preserves large-file metadata and Range delivery.
with urlopen(Request(url + '/download/' + file.name, method='HEAD'), timeout=30) as response:
    assert int(response.headers['Content-Length']) == file.stat().st_size
with urlopen(Request(url + '/download/' + file.name, headers={'Range': 'bytes=0-4095'}), timeout=30) as response:
    assert response.status == 206
    with file.open('rb') as source:
        assert response.read() == source.read(4096)
print('Public HTTPS download and resume check passed.', flush=True)
