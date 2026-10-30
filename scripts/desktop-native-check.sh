#!/usr/bin/env bash
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
bash scripts/desktop-package.sh
bash scripts/neon-clean-iso.sh
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
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get update
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/erodist-icons.deb /tmp/erodist-control-center.deb python3-pyside6.qttest
if [ "${ERODIST_WITH_WINE:-0}" = 1 ]; then
    sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wine wine64 wine32:i386 fonts-wine
    sudo cp scripts/wine-smoke.py "$ROOT/tmp/"
    sudo chroot "$ROOT" /usr/bin/python3 -u /tmp/wine-smoke.py
fi
sudo chroot "$ROOT" dpkg-query -W -f='${binary:Package} ${Version}\n' 'linux-image*' 'linux-modules*' | sort > "$WORK/kernel-after.txt"
diff -u "$WORK/kernel-before.txt" "$WORK/kernel-after.txt"
echo '=== Native KCM inventory'
sudo chroot "$ROOT" /usr/bin/env QT_QPA_PLATFORM=offscreen /usr/bin/timeout 30 kcmshell6 --list > "$WORK/kcms.txt"
cat "$WORK/kcms.txt"
sudo cp "$WORK/kcms.txt" "$ROOT/tmp/erodist-kcms.txt"
sudo chroot "$ROOT" /usr/bin/python3 -X faulthandler -u /tmp/desktop-smoke.py
mkdir -p artifacts/desktop/captures
sudo cp "$ROOT"/tmp/desktop-captures/*.png artifacts/desktop/captures/
sudo chown -R "$(id -u):$(id -g)" artifacts/desktop
(cd artifacts/desktop && sha256sum *.deb captures/icons.png captures/settings-home.png > SHA256SUMS)
