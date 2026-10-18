#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${ERODIST_VERSION:-0.1.0}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid ERODIST_VERSION' >&2; exit 1; }
[[ $EUID -eq 0 ]] || { echo 'Run as root inside Debian 12 (see README).' >&2; exit 1; }
command -v lb >/dev/null
mkdir -p "$ROOT/build" "$ROOT/artifacts"
cd "$ROOT/build"
if [[ -f config/common ]]; then lb clean --purge; fi
lb config \
  --mode debian --distribution bookworm --architectures amd64 \
  --binary-images iso-hybrid --bootloaders 'syslinux,grub-efi' \
  --archive-areas 'main contrib non-free non-free-firmware' \
  --debian-installer live --debian-installer-gui true \
  --bootappend-live 'boot=live components username=tester hostname=erodist locales=ru_RU.UTF-8 keyboard-layouts=us,ru' \
  --iso-application EroDist --iso-publisher EroDist \
  --iso-volume "EroDist $VERSION amd64" \
  --memtest none
cp -a "$ROOT/live/." config/
lb build
install -m 0644 live-image-amd64.hybrid.iso "$ROOT/artifacts/erodist-$VERSION-amd64.iso"
cd "$ROOT/artifacts"
sha256sum "erodist-$VERSION-amd64.iso" > SHA256SUMS
