#!/usr/bin/env bash
# Preserve original Casper/UUID/microcode and all modules: alter appearance only.
set -euo pipefail
WORK=$1
ROOT="$WORK/root"
SOURCE="$WORK/initrd-source"
OUTPUT="$WORK/changed/casper/initrd"
sudo unmkinitramfs "$WORK/upstream-initrd" "$SOURCE"
MAIN="$SOURCE/main"
[ -d "$MAIN" ] || MAIN="$SOURCE"
test -d "$MAIN/usr/share/plymouth/themes"
sudo cp -a "$ROOT/usr/share/plymouth/themes/erodist" "$MAIN/usr/share/plymouth/themes/"
sudo mkdir -p "$MAIN/etc/plymouth" "$MAIN/etc/alternatives"
sudo cp "$ROOT/etc/plymouth/plymouthd.conf" "$MAIN/etc/plymouth/plymouthd.conf"
sudo ln -sfn /usr/share/plymouth/themes/erodist/erodist.plymouth "$MAIN/etc/alternatives/default.plymouth"
sudo bash -c '
set -euo pipefail
source=$1; main=$2
if [ "$source" != "$main" ]; then
    for name in early early2 early3; do
        if [ -d "$source/$name" ]; then (cd "$source/$name"; find . -print0 | LC_ALL=C sort -z | cpio --null --quiet -o -H newc); fi
    done
fi
(cd "$main"; find . -print0 | LC_ALL=C sort -z | cpio --null --quiet -o -H newc | gzip -1)
' bash "$SOURCE" "$MAIN" > "$OUTPUT"
lsinitramfs "$OUTPUT" > "$WORK/new-initrd-files.txt"
grep -q 'scripts/casper' "$WORK/new-initrd-files.txt"
grep -q 'plymouth/themes/erodist/erodist.script' "$WORK/new-initrd-files.txt"
grep -q 'plymouth/themes/erodist/logo.png' "$WORK/new-initrd-files.txt"
# Compare the unmodified core payload against a fresh extraction of the original.
sudo unmkinitramfs "$WORK/upstream-initrd" "$WORK/initrd-original"
sudo unmkinitramfs "$OUTPUT" "$WORK/initrd-verified"
sudo python3 - "$WORK" <<'PY'
from pathlib import Path
import hashlib,sys
work=Path(sys.argv[1]);old=work/'initrd-original';new=work/'initrd-verified'
allowed={'etc/alternatives/default.plymouth','etc/plymouth/plymouthd.conf'}
def digest(path):return hashlib.sha256(path.read_bytes()).digest()
count=0
for path in old.rglob('*'):
 relative=path.relative_to(old)
 normalized=str(relative)
 if normalized.startswith('main/'):normalized=normalized[5:]
 if normalized in allowed:continue
 target=new/relative
 if path.is_symlink():
  assert target.is_symlink() and path.readlink()==target.readlink(),relative
 elif path.is_file():
  assert target.is_file() and digest(path)==digest(target),relative
  count+=1
print('PASS original initrd payload preserved except Plymouth config; files checked:',count)
PY
