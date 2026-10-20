#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $EUID -eq 0 ]] || { echo 'Run as root on Ubuntu 24.04 build runner.' >&2; exit 1; }
WORK="$ROOT/build/mint"
[[ ! -e "$WORK" ]] || { echo 'Fresh build directory required.' >&2; exit 1; }
mkdir -p "$WORK/source" "$WORK/changed/casper" "$ROOT/artifacts"
mapfile -t CONFIG < <(python3 - "$ROOT/mint/source.json" <<'PY'
import json, sys
c=json.load(open(sys.argv[1]))
for key in ['filename','mirror','signing_fingerprint','output']: print(c[key])
PY
)
SOURCE="${CONFIG[0]}"; MIRROR="${CONFIG[1]}"; FINGERPRINT="${CONFIG[2]}"; OUTPUT="${CONFIG[3]}"
cd "$WORK/source"
for filename in sha256sum.txt sha256sum.txt.gpg "$SOURCE"; do
  curl --fail --location --retry 3 --connect-timeout 30 --output "$filename" "$MIRROR/$filename"
done
# Authenticate upstream before extracting anything. Never accept an unpinned signing key.
export GNUPGHOME="$WORK/gnupg"
mkdir -m 700 "$GNUPGHOME"
curl --fail --location --retry 3 --output "$WORK/mint-key.asc" "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$FINGERPRINT"
gpg --batch --import "$WORK/mint-key.asc"
actual=$(gpg --batch --with-colons --fingerprint "$FINGERPRINT" | awk -F: '$1=="fpr" {print $10; exit}')
[[ "$actual" == "$FINGERPRINT" ]]
gpg --batch --verify sha256sum.txt.gpg sha256sum.txt
PYTHONPATH="$ROOT/scripts" python3 - "$SOURCE" <<'PY'
import sys
from pathlib import Path
from mint_common import checksum_for, sha256
expected=checksum_for(Path('sha256sum.txt').read_text(),sys.argv[1])
assert sha256(sys.argv[1]) == expected, 'Upstream ISO checksum mismatch'
print('Verified signed upstream ISO SHA256:', expected)
PY
ISO="$WORK/source/$SOURCE"
xorriso -indev "$ISO" -report_el_torito plain -report_system_area plain > "$WORK/upstream-boot.txt" 2>&1
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.squashfs "$WORK/original.squashfs" -extract /md5sum.txt "$WORK/original-md5sum.txt"
unsquashfs -d "$WORK/rootfs" "$WORK/original.squashfs"
rm "$WORK/original.squashfs"
bash "$ROOT/scripts/build-packages.sh"
cp "$ROOT/artifacts/erodist-system.deb" "$WORK/rootfs/tmp/erodist-system.deb"
cp "$ROOT/artifacts/erodist-installer.deb" "$WORK/rootfs/tmp/erodist-installer.deb"
# Package registration, plugin checks and dependency simulation inside the actual Mint root.
xorriso -osirrox on -indev "$ISO" -extract /casper/vmlinuz "$WORK/upstream-vmlinuz"
KERNEL=$(file "$WORK/upstream-vmlinuz" | sed -n 's/.*version \([^ ,]*\).*/\1/p')
[[ -n "$KERNEL" ]] || { echo 'Cannot identify upstream kernel'; exit 1; }
if xorriso -indev "$ISO" -ls /casper/initrd.lz >/dev/null 2>&1; then INITRD=initrd.lz; else INITRD=initrd; fi
bash "$ROOT/scripts/configure-root.sh" "$WORK/rootfs" "$WORK" "$KERNEL" "$INITRD"
python3 "$ROOT/scripts/brand-iso.py" "$ISO" "$WORK/changed"
chroot "$WORK/rootfs" dpkg-query -W -f='${Package} ${Version}\n' > "$WORK/changed/casper/filesystem.manifest"
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.manifest-remove "$WORK/changed/casper/filesystem.manifest-remove"
printf '\nerodist-installer\n' >> "$WORK/changed/casper/filesystem.manifest-remove"
# Preserve Mint's base identity and storage modules; add registered EroDist packages.
test -d "$WORK/rootfs/usr/share/cinnamon"
test -d "$WORK/rootfs/usr/share/themes/Mint-Y-Dark"
python3 - "$WORK/rootfs" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
assert (root/'etc/linuxmint/info').is_file(), 'Not a Linux Mint filesystem'
assert 'Cinnamon' in (root/'etc/linuxmint/info').read_text()
assert (root/'usr/bin/erodist-settings').is_file()
assert (root/'usr/lib/ubiquity/plugins/ubi-erodist.py').is_file()
PY
# Zstd improves decompression relative to XZ; actual Hyper-V performance is untested.
mksquashfs "$WORK/rootfs" "$WORK/changed/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 15 -b 1M
size=$(du -sx --block-size=1 "$WORK/rootfs" | cut -f1)
printf '%s\n' "$size" > "$WORK/changed/casper/filesystem.size"
PYTHONPATH="$ROOT/scripts" python3 - "$WORK" <<'PY'
from pathlib import Path
import sys
from mint_common import update_md5
work=Path(sys.argv[1])
changed={p.relative_to(work/'changed').as_posix():p for p in (work/'changed').rglob('*') if p.is_file()}
(work/'changed/md5sum.txt').write_text(update_md5((work/'original-md5sum.txt').read_text(),changed))
PY
# Replay original hybrid BIOS/UEFI boot equipment, including appended EFI partitions.
BOOT_MAP=()
while IFS= read -r -d '' image; do
  BOOT_MAP+=(-map "$image" "/${image#"$WORK/changed/"}")
done < <(find "$WORK/changed" -type f ! -path "$WORK/changed/casper/*" ! -name md5sum.txt -print0)
xorriso -indev "$ISO" -outdev "$ROOT/artifacts/$OUTPUT" \
  -boot_image any replay \
  -map "$WORK/changed/casper/filesystem.squashfs" /casper/filesystem.squashfs \
  -map "$WORK/changed/casper/$INITRD" "/casper/$INITRD" \
  -map "$WORK/changed/casper/filesystem.size" /casper/filesystem.size \
  -map "$WORK/changed/casper/filesystem.manifest" /casper/filesystem.manifest \
  -map "$WORK/changed/casper/filesystem.manifest-remove" /casper/filesystem.manifest-remove \
  -map "$WORK/changed/md5sum.txt" /md5sum.txt "${BOOT_MAP[@]}"
xorriso -indev "$ROOT/artifacts/$OUTPUT" -report_el_torito plain -report_system_area plain > "$ROOT/artifacts/BOOT-REPORT.txt" 2>&1
python3 - "$WORK/upstream-boot.txt" "$ROOT/artifacts/BOOT-REPORT.txt" <<'PY'
from pathlib import Path
import sys
old,new=map(lambda p:Path(p).read_text(),sys.argv[1:])
for platform in ['BIOS','UEFI']:
    assert platform in old and platform in new, f'Missing boot platform: {platform}'
PY
cp "$WORK/source/sha256sum.txt" "$ROOT/artifacts/UPSTREAM-SHA256SUMS.txt"
# Keep the same verified ISO inode for a one-file Actions ZIP; Releases keep the split fallback.
mkdir -p "$ROOT/archive"
ln "$ROOT/artifacts/$OUTPUT" "$ROOT/archive/$OUTPUT"
python3 "$ROOT/scripts/package-release.py" "$ROOT/artifacts/$OUTPUT"

(cd "$ROOT/artifacts" && sha256sum ./*.deb >> SHA256SUMS)
