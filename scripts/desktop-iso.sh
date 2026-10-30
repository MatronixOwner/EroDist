#!/usr/bin/env bash
# First customized neon ISO: preserve native installer, kernel and boot equipment.
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
ERODIST_WITH_WINE=1 bash scripts/desktop-native-check.sh
WORK="$REPO/build/desktop-native"
ROOT="$WORK/root"
CHANGED="$WORK/changed"
mkdir -p "$CHANGED/casper" artifacts/desktop-iso
readarray -t CONFIG < <(python3 - <<'PY'
import json
c=json.load(open('neon/image.json'))
print(c['output']);print(c['volume_id'])
PY
)
OUTPUT="$REPO/artifacts/desktop-iso/${CONFIG[0]}"
ISO=$(find "$REPO/artifacts/neon-clean" -name '*.iso' -print -quit)
# Refuse to squash host bind mounts even if cleanup reported an error.
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys
root=sys.argv[1]
for line in Path('/proc/self/mountinfo').read_text().splitlines():
 mount=line.split()[4]
 assert mount!=root and not mount.startswith(root+'/'), f'Host mount still present: {mount}'
PY
sudo python3 - "$ROOT" <<'PY'
import configparser,json,sys
from pathlib import Path
root=Path(sys.argv[1]);p=root/'etc/skel/.config/kdeglobals';p.parent.mkdir(parents=True,exist_ok=True)
c=configparser.ConfigParser(interpolation=None,strict=False);c.optionxform=str
if p.exists():c.read(p)
if not c.has_section('Icons'):c.add_section('Icons')
c.set('Icons','Theme','EroDist')
with p.open('w') as stream:c.write(stream,space_around_delimiters=False)
meta=root/'usr/share/erodist-image/build.json';meta.parent.mkdir(parents=True,exist_ok=True)
meta.write_text(json.dumps({'image':json.load(open('neon/image.json')),'upstream':json.load(open('neon/source.json'))},indent=2)+'\n')
PY
# Remove testing-only material, with no shared Wine prefix and no root theme settings.
sudo rm -f "$ROOT/tmp/erodist-control-center.deb" "$ROOT/tmp/erodist-icons.deb" "$ROOT/tmp/desktop-smoke.py" "$ROOT/tmp/wine-smoke.py" "$ROOT/tmp/erodist-kcms.txt" "$ROOT/tmp/erodist-report-test.txt"
sudo rm -rf "$ROOT/tmp/desktop-captures"
sudo chroot "$ROOT" apt-get clean
sudo chroot "$ROOT" dpkg --audit > "$WORK/dpkg-audit.txt"
test ! -s "$WORK/dpkg-audit.txt"
sudo chroot "$ROOT" dpkg-query -W -f='${binary:Package} ${Version}\n' > "$CHANGED/casper/filesystem.manifest"
sudo du -sx --block-size=1 "$ROOT" | cut -f1 > "$CHANGED/casper/filesystem.size"
xorriso -indev "$ISO" -report_el_torito plain -report_system_area plain > "$WORK/upstream-boot.txt" 2>&1
xorriso -osirrox on -indev "$ISO" -extract /md5sum.txt "$WORK/original-md5sum.txt" -extract /casper/vmlinuz "$WORK/upstream-vmlinuz" -extract /casper/initrd "$WORK/upstream-initrd"
# XZ keeps the complete 32/64-bit Wine image reasonably small; no split ISO.
sudo mksquashfs "$ROOT" "$CHANGED/casper/filesystem.squashfs" -noappend -comp xz -b 1M -processors 2
python3 - "$WORK" <<'PY'
from pathlib import Path
import hashlib,re,sys
work=Path(sys.argv[1]);changed=work/'changed'
exclude=set(re.findall(r'El Torito (?:img|cat) path\s*:\s*(?:\d+\s+)?(/\S+)',(work/'upstream-boot.txt').read_text()))
files={p.relative_to(changed).as_posix():p for p in changed.rglob('*') if p.is_file()}
def digest(path):
 h=hashlib.md5()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
lines=[];seen=set()
for line in (work/'original-md5sum.txt').read_text().splitlines():
 if not line.strip():continue
 match=re.match(r'^([a-fA-F0-9]{32})\s+\*?(.*)$',line)
 assert match,repr(line)
 name=match[2].removeprefix('./').lstrip('/')
 if '/'+name in exclude or name=='md5sum.txt':continue
 lines.append(f'{digest(files[name]) if name in files else match[1]}  ./{name}');seen.add(name)
for name,path in files.items():
 if name not in seen:lines.append(f'{digest(path)}  ./{name}')
(changed/'md5sum.txt').write_text('\n'.join(lines)+'\n')
print('Updated medium integrity checks; boot image/catalog checksums excluded because replay relocates them.')
PY
xorriso -indev "$ISO" -outdev "$OUTPUT" -boot_image any replay -volid "${CONFIG[1]}" \
 -map "$CHANGED/casper/filesystem.squashfs" /casper/filesystem.squashfs \
 -map "$CHANGED/casper/filesystem.manifest" /casper/filesystem.manifest \
 -map "$CHANGED/casper/filesystem.size" /casper/filesystem.size \
 -map "$CHANGED/md5sum.txt" /md5sum.txt
xorriso -indev "$OUTPUT" -report_el_torito plain -report_system_area plain > artifacts/desktop-iso/BOOT-REPORT.txt 2>&1
for platform in BIOS UEFI; do grep -q "$platform" artifacts/desktop-iso/BOOT-REPORT.txt; done
# Round-trip the actual final image; check its filesystem, integrity list and kernel.
xorriso -osirrox on -indev "$OUTPUT" -extract / "$WORK/final-iso"
(cd "$WORK/final-iso" && md5sum --quiet -c md5sum.txt)
cmp "$WORK/upstream-vmlinuz" "$WORK/final-iso/casper/vmlinuz"
cmp "$WORK/upstream-initrd" "$WORK/final-iso/casper/initrd"
cmp "$CHANGED/casper/filesystem.squashfs" "$WORK/final-iso/casper/filesystem.squashfs"
unsquashfs -cat "$WORK/final-iso/casper/filesystem.squashfs" var/lib/dpkg/status > "$WORK/final-status.txt"
python3 - "$WORK" <<'PY'
from pathlib import Path
import json,sys
work=Path(sys.argv[1]);image=json.load(open('neon/image.json'));installed={}
for block in (work/'final-status.txt').read_text().split('\n\n'):
 fields=dict(line.split(': ',1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
 if fields.get('Status')!='install ok installed':continue
 name=fields['Package'];arch=fields.get('Architecture')
 installed[name+':'+arch]=fields['Version'];installed[name]=fields['Version']
for name in image['packages']:assert name in installed, name
for name in ('erodist-system','erodist-installer','erodist-neon-system','cinnamon'):assert name not in installed,name
result={'image':image,'installed_versions':{p:installed[p] for p in image['packages']},'wine_cmd_smoke':['win32','win64'],'kernel_initrd':'byte-identical upstream','medium_checksums':'passed','boot_records':['BIOS','UEFI'],'full_vm_install_tested':False,'hyper_v_tested':False}
Path('artifacts/desktop-iso/VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS final ISO contains preinstalled EroDist app, icons and both Wine architectures.')
PY
(cd artifacts/desktop-iso && sha256sum "${CONFIG[0]}" > SHA256SUMS)
cat artifacts/desktop-iso/SHA256SUMS
