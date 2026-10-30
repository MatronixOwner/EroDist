#!/usr/bin/env bash
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
bash scripts/desktop-package.sh
bash scripts/neon-clean-iso.sh
WORK="$REPO/build/desktop-native"
mkdir -p "$WORK"
ISO=$(find "$REPO/artifacts/neon-clean" -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.squashfs "$WORK/base.squashfs"
sudo unsquashfs -no-progress -d "$WORK/root" "$WORK/base.squashfs"
ROOT="$WORK/root"
cleanup() { for mount in proc sys dev; do sudo umount -R "$ROOT/$mount" || true; done; }
trap cleanup EXIT
for mount in dev sys; do sudo mount --rbind "/$mount" "$ROOT/$mount";sudo mount --make-rslave "$ROOT/$mount";done
sudo mount -t proc proc "$ROOT/proc"
sudo rm -f "$ROOT/etc/resolv.conf";sudo cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
sudo cp artifacts/desktop/*.deb "$ROOT/tmp/"
sudo cp scripts/desktop-smoke.py "$ROOT/tmp/"
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get update
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/erodist-icons.deb /tmp/erodist-control-center.deb python3-pyside6.qttest
echo '=== Native KCM inventory'
sudo chroot "$ROOT" /usr/bin/env QT_QPA_PLATFORM=offscreen /usr/bin/timeout 30 kcmshell6 --list > "$WORK/kcms.txt"
cat "$WORK/kcms.txt"
sudo cp "$WORK/kcms.txt" "$ROOT/tmp/erodist-kcms.txt"
sudo chroot "$ROOT" /usr/bin/python3 -X faulthandler -u /tmp/desktop-smoke.py
mkdir -p artifacts/desktop/captures
sudo cp "$ROOT"/tmp/desktop-captures/*.png artifacts/desktop/captures/
sudo chown -R "$(id -u):$(id -g)" artifacts/desktop
(cd artifacts/desktop && sha256sum *.deb captures/icons.png captures/settings-home.png > SHA256SUMS)
