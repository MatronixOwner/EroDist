#!/usr/bin/env python3
"""Split only oversized GitHub assets, with verified Windows/Linux assembly."""
import json
from pathlib import Path
import sys
from mint_common import sha256


def package_iso(iso, part_size=1_500_000_000, limit=2_147_483_647):
    iso = Path(iso)
    folder = iso.parent
    expected = sha256(iso)
    (folder / 'ISO-SHA256SUMS.txt').write_text(f'{expected}  {iso.name}\n')
    parts = []
    split = iso.stat().st_size > limit
    if split:
        with iso.open('rb') as src:
            number = 1
            while True:
                first = src.read(min(4 * 1024 * 1024, part_size))
                if not first:
                    break
                part = folder / f'{iso.name}.part{number:02d}'
                with part.open('wb') as dst:
                    dst.write(first)
                    remaining = part_size - len(first)
                    while remaining:
                        block = src.read(min(4 * 1024 * 1024, remaining))
                        if not block:
                            break
                        dst.write(block)
                        remaining -= len(block)
                parts.append({'name': part.name, 'sha256': sha256(part)})
                number += 1
        manifest = {'output': iso.name, 'sha256': expected, 'parts': parts}
        (folder / 'ASSEMBLY.json').write_text(json.dumps(manifest, indent=2) + '\n')
        (folder / 'assemble.ps1').write_text('''$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$m = Get-Content -LiteralPath './ASSEMBLY.json' -Raw | ConvertFrom-Json
if (Test-Path -LiteralPath $m.output) { throw 'Output ISO already exists. Move it away first.' }
$temp = $m.output + '.assembling'
if (Test-Path -LiteralPath $temp) { throw 'Temporary assembly file already exists. Check it before retrying.' }
foreach ($p in $m.parts) {
    if (!(Test-Path -LiteralPath $p.name)) { throw ('Missing part: ' + $p.name) }
    if ((Get-FileHash -LiteralPath $p.name -Algorithm SHA256).Hash.ToLower() -ne $p.sha256) { throw ('Damaged part: ' + $p.name) }
}
$out = [IO.File]::Open($temp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
    foreach ($p in $m.parts) {
        $input = [IO.File]::OpenRead((Join-Path $PSScriptRoot $p.name))
        try { $input.CopyTo($out) } finally { $input.Dispose() }
    }
} finally { $out.Dispose() }
if ((Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLower() -ne $m.sha256) { throw 'Final ISO SHA256 mismatch. Do not use it.' }
Move-Item -LiteralPath $temp -Destination $m.output
Write-Host ('Verified ISO ready: ' + $m.output)
''')
        (folder / 'assemble.cmd').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0assemble.ps1"\r\nif errorlevel 1 (echo Assembly failed. & pause & exit /b 1)\r\npause\r\n')
        (folder / 'assemble.sh').write_text('''#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 - <<'PYASSEMBLE'
import hashlib, json, pathlib, shutil
m=json.loads(pathlib.Path('ASSEMBLY.json').read_text())
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()
output=pathlib.Path(m['output'])
temp=output.with_name(output.name+'.assembling')
if output.exists() or temp.exists(): raise SystemExit('Output/temporary ISO exists; check it first.')
for part in m['parts']:
    p=pathlib.Path(part['name'])
    if digest(p)!=part['sha256']: raise SystemExit('Damaged part: '+str(p))
with temp.open('xb') as out:
    for part in m['parts']:
        with pathlib.Path(part['name']).open('rb') as src: shutil.copyfileobj(src,out,4*1024*1024)
if digest(temp)!=m['sha256']: raise SystemExit('ISO checksum mismatch. Do not use it.')
temp.rename(output)
print('Verified ISO ready:',output)
PYASSEMBLE
''')
        iso.unlink()
    (folder / 'DOWNLOAD.txt').write_text(
        'EroDist Mint Cinnamon — TEST BUILD, not an official Linux Mint ISO.\n'
        + ('GitHub limits each asset to 2 GiB, so the ISO is split. These parts are NOT bootable individually.\n'
           'Download ALL .partNN files, ASSEMBLY.json, assemble.ps1 and assemble.cmd into ONE folder.\n'
           'Windows: double-click assemble.cmd (local PowerShell script, no administrator rights).\n'
           'Linux: download assemble.sh too, then run: bash assemble.sh (requires Python 3).\n'
           'Assembly verifies every part and the resulting ISO SHA256. It does NOT write to disks.\n'
           if split else 'Download the ISO and ISO-SHA256SUMS.txt; verify SHA256 before boot.\n')
        + 'Start in a new VM with an EMPTY virtual disk. Disable Secure Boot for this untested derivative.\n'
        'Stock Mint installer and Live account are preserved. Installer may erase your data.\n'
        'Upstream signature verifies only the original Mint ISO, NOT the remastered EroDist ISO.\n')
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (folder / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in files))
    return parts


if __name__ == '__main__':
    package_iso(sys.argv[1])
