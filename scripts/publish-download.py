"""Actions-only: assemble the published release and deliver to the session server."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen

event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
inputs = event.get('inputs', {})
url = (inputs.get('upload_url') or json.loads(Path('site/deploy.json').read_text())['url']).rstrip('/')
token = inputs.get('upload_token') or os.environ['GH_TOKEN']
print('::add-mask::' + token, flush=True)
if not url.startswith('https://8080-') or not url.endswith('.e2b.app'):
    raise ValueError('Not a session preview URL')
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
                          'Content-Type': 'application/octet-stream'}, method='POST')
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
