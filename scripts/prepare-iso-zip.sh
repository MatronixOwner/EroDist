#!/usr/bin/env bash
# An unchanged, already published ISO. upload-artifact creates the ZIP itself.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ ! -e published-iso ]] || { echo 'Fresh output directory required' >&2; exit 1; }
gh release download test-0.9.0-mint1-22-1 \
  --pattern '*.iso.part*' --pattern ASSEMBLY.json --pattern assemble.sh \
  --dir published-iso
bash published-iso/assemble.sh
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
folder = Path('published-iso')
manifest = json.loads((folder / 'ASSEMBLY.json').read_text())
assert manifest['output'] == 'erodist-0.9.0-mint1-cinnamon-amd64.iso'
iso = folder / manifest['output']
assert iso.stat().st_size == 3201630208
h = hashlib.sha256()
with iso.open('rb') as file:
    for block in iter(lambda: file.read(4 * 1024**2), b''):
        h.update(block)
assert h.hexdigest() == manifest['sha256'], 'ISO checksum mismatch'
print('Complete ISO SHA256:', h.hexdigest())
# Keep only the verified ISO in the directory passed to upload-artifact.
for path in folder.iterdir():
    if path != iso:
        path.unlink()
assert list(folder.iterdir()) == [iso]
print('Archive input contains exactly one complete ISO:', iso.name)
PY
