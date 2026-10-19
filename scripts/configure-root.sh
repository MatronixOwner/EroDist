#!/usr/bin/env bash
set -euo pipefail
ROOTFS=$(realpath "$1")
WORK=$(realpath "$2")
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$ROOTFS" == "$WORK/rootfs" ]] || exit 1
# Do not let apt services start inside the image build environment.
if [[ -e "$ROOTFS/usr/sbin/policy-rc.d" ]]; then
  cp -a "$ROOTFS/usr/sbin/policy-rc.d" "$WORK/original-policy-rc.d"
fi
printf '#!/bin/sh\nexit 101\n' > "$ROOTFS/usr/sbin/policy-rc.d"
chmod 755 "$ROOTFS/usr/sbin/policy-rc.d"
cp -a "$ROOTFS/etc/resolv.conf" "$WORK/original-resolv.conf" 2>/dev/null || true
rm -f "$ROOTFS/etc/resolv.conf"
cp -L /etc/resolv.conf "$ROOTFS/etc/resolv.conf"
mkdir -p "$ROOTFS/dev" "$ROOTFS/proc" "$ROOTFS/tmp/.X11-unix" /tmp/.X11-unix
cleanup() {
  umount "$ROOTFS/tmp/.X11-unix" 2>/dev/null || true
  umount "$ROOTFS/proc" 2>/dev/null || true
  umount "$ROOTFS/dev" 2>/dev/null || true
  rm -f "$ROOTFS/etc/resolv.conf" "$ROOTFS/usr/sbin/policy-rc.d"
  if [[ -e "$WORK/original-resolv.conf" || -L "$WORK/original-resolv.conf" ]]; then cp -a "$WORK/original-resolv.conf" "$ROOTFS/etc/resolv.conf"; fi
  if [[ -e "$WORK/original-policy-rc.d" ]]; then cp -a "$WORK/original-policy-rc.d" "$ROOTFS/usr/sbin/policy-rc.d"; fi
}
trap cleanup EXIT
mount --bind /dev "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"
mount --bind /tmp/.X11-unix "$ROOTFS/tmp/.X11-unix"
chroot "$ROOTFS" dpkg --add-architecture i386
chroot "$ROOTFS" apt-get -o APT::Update::Error-Mode=any -o Acquire::Retries=2 update
chroot "$ROOTFS" apt-get -y --no-remove install /tmp/erodist-system.deb /tmp/erodist-installer.deb
cp "$ROOT/scripts/check-editions.py" "$ROOTFS/tmp/check-editions.py"
chroot "$ROOTFS" python3 /tmp/check-editions.py
cp "$ROOT/scripts/gui-smoke.py" "$ROOTFS/tmp/gui-smoke.py"
xvfb-run -a -s '-screen 0 1280x800x24 -ac' chroot "$ROOTFS" env XAUTHORITY=/dev/null python3 /tmp/gui-smoke.py
chroot "$ROOTFS" dpkg --remove-architecture i386
find "$ROOTFS/var/lib/apt/lists" -type f -name '*binary-i386*' -delete
rm -f "$ROOTFS/tmp/erodist-system.deb" "$ROOTFS/tmp/erodist-installer.deb" "$ROOTFS/tmp/check-editions.py" "$ROOTFS/tmp/gui-smoke.py"
