#!/usr/bin/env bash
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
bash scripts/desktop-package.sh
if [ -n "${ERODIST_BASE_ISO:-}" ]; then
    python3 - "$ERODIST_BASE_ISO" <<'BASE'
import hashlib,json,sys
from pathlib import Path
c=json.load(open('neon/parent-image.json'));p=Path(sys.argv[1])
assert p.name==c['filename']
h=hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
assert h.hexdigest()==c['sha256'],'Parent ISO hash mismatch'
print('PASS approved parent ISO SHA256; original upstream provenance retained:',c['source_commit'])
BASE
else
    bash scripts/neon-clean-iso.sh
fi
WORK="$REPO/build/desktop-native"
mkdir -p "$WORK"
[ ! -e "$WORK/root" ] || { echo 'Fresh native build directory required'; exit 1; }
ISO=$(find "$REPO/artifacts/neon-clean" -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.squashfs "$WORK/base.squashfs"
sudo unsquashfs -no-progress -d "$WORK/root" "$WORK/base.squashfs"
ROOT="$WORK/root"
sudo cp -a "$ROOT/etc/resolv.conf" "$WORK/resolv.original"
if sudo test -e "$ROOT/usr/sbin/policy-rc.d"; then
    sudo cp -a "$ROOT/usr/sbin/policy-rc.d" "$WORK/policy.original"
fi
cleanup() {
    for mount in proc sys dev; do sudo umount -R "$ROOT/$mount" || true; done
    sudo rm -f "$ROOT/etc/resolv.conf"
    sudo cp -a "$WORK/resolv.original" "$ROOT/etc/resolv.conf"
    sudo rm -f "$ROOT/usr/sbin/policy-rc.d"
    if [ -e "$WORK/policy.original" ]; then sudo cp -a "$WORK/policy.original" "$ROOT/usr/sbin/policy-rc.d"; fi
}
trap cleanup EXIT
for mount in dev sys; do sudo mount --rbind "/$mount" "$ROOT/$mount";sudo mount --make-rslave "$ROOT/$mount";done
sudo mount -t proc proc "$ROOT/proc"
sudo rm -f "$ROOT/etc/resolv.conf";sudo cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
sudo cp artifacts/desktop/*.deb "$ROOT/tmp/"
sudo cp scripts/desktop-smoke.py "$ROOT/tmp/"
printf '#!/bin/sh
exit 101
' | sudo tee "$ROOT/usr/sbin/policy-rc.d" >/dev/null
sudo chmod 755 "$ROOT/usr/sbin/policy-rc.d"
sudo chroot "$ROOT" dpkg-query -W -f='${binary:Package} ${Version}\n' 'linux-image*' 'linux-modules*' | sort > "$WORK/kernel-before.txt"
if [ "${ERODIST_WITH_WINE:-0}" = 1 ]; then
    sudo chroot "$ROOT" dpkg --add-architecture i386
fi
if [ -n "${ERODIST_BASE_ISO:-}" ]; then
    sudo chroot "$ROOT" dpkg -i /tmp/erodist-icons.deb /tmp/erodist-control-center.deb /tmp/erodist-desktop.deb
else
if ! sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 update; then
    # The upstream HTTP mirror occasionally responds 502; retain keys/pins and retry HTTPS.
    sudo python3 - "$ROOT" <<'APT'
from pathlib import Path
import sys
for p in (Path(sys.argv[1])/'etc/apt').rglob('*'):
    if p.is_file() and p.suffix in ('.list','.sources'):
        old=p.read_text();new=old.replace('http://archive.neon.kde.org/','https://archive.neon.kde.org/')
        if new!=old:p.write_text(new)
APT
    sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 update
fi
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/erodist-icons.deb /tmp/erodist-control-center.deb /tmp/erodist-desktop.deb python3-pyside6.qttest
fi
if [ "${ERODIST_WITH_WINE:-0}" = 1 ]; then
    if [ -z "${ERODIST_BASE_ISO:-}" ]; then
        sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wine wine64 wine32:i386 fonts-wine
    fi
    sudo cp scripts/wine-smoke.py "$ROOT/tmp/"
    sudo chroot "$ROOT" /usr/bin/python3 -u /tmp/wine-smoke.py
fi
sudo chroot "$ROOT" dpkg-query -W -f='${binary:Package} ${Version}\n' 'linux-image*' 'linux-modules*' | sort > "$WORK/kernel-after.txt"
diff -u "$WORK/kernel-before.txt" "$WORK/kernel-after.txt"
if [ "${ERODIST_WITH_WINE:-0}" = 1 ]; then
    sudo python3 scripts/desktop-theme-configure.py "$ROOT"
    sudo chroot "$ROOT" update-alternatives --set default.plymouth /usr/share/plymouth/themes/erodist/erodist.plymouth
fi
echo '=== Native KCM inventory'
sudo chroot "$ROOT" /usr/bin/env QT_QPA_PLATFORM=offscreen /usr/bin/timeout 30 kcmshell6 --list > "$WORK/kcms.txt"
cat "$WORK/kcms.txt"
sudo cp "$WORK/kcms.txt" "$ROOT/tmp/erodist-kcms.txt"
sudo chroot "$ROOT" /usr/bin/python3 -X faulthandler -u /tmp/desktop-smoke.py
mkdir -p artifacts/desktop/captures
sudo cp "$ROOT"/tmp/desktop-captures/*.png artifacts/desktop/captures/
sudo chown -R "$(id -u):$(id -g)" artifacts/desktop
(cd artifacts/desktop && sha256sum *.deb captures/icons.png captures/settings-home.png > SHA256SUMS)
