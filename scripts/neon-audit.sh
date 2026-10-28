#!/usr/bin/env bash
set -euo pipefail
WORK="$PWD/build/neon-audit"
mkdir -p "$WORK"
cd "$WORK"
REPO="$(cd ../.. && pwd)"
URL=$(python3 -c 'import json; print(json.load(open("'"$REPO"'/neon/source.json"))["url"])')
curl -fL --retry 3 --connect-timeout 30 -o base.iso "$URL"
curl -fL --retry 3 -o base.iso.sig "$URL.sig"
curl -fsSL --retry 3 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x45F4C354638D1F29' -o neon-key.asc
export GNUPGHOME="$WORK/gnupg"
mkdir -m 700 "$GNUPGHOME"
gpg --batch --import neon-key.asc
echo '=== SIGNING KEY FINGERPRINTS'
gpg --batch --with-colons --fingerprint
# Exact signing-key fingerprint and image hash are pinned after the initial signed audit.
EXPECTED=$(python3 -c 'import json; print(json.load(open("'"$REPO"'/neon/source.json"))["signing_fingerprint"])')
ACTUAL=$(gpg --batch --with-colons --fingerprint | awk -F: '$1=="fpr" {print $10; exit}')
[ "$ACTUAL" = "$EXPECTED" ]
gpg --batch --verify base.iso.sig base.iso
HASH=$(python3 -c 'import json; print(json.load(open("'"$REPO"'/neon/source.json"))["sha256"])')
echo "$HASH  base.iso" | sha256sum -c -
echo '=== UPSTREAM SHA256'
sha256sum base.iso
xorriso -indev base.iso -ls /casper
xorriso -osirrox on -indev base.iso -extract /casper/filesystem.squashfs base.squashfs
unsquashfs -d root base.squashfs calamares/desktop usr/bin/calamares usr/share/applications/calamares.desktop usr/lib/os-release usr/etc/calamares var/lib/dpkg/info/calamares-settings.list etc/os-release etc/lsb-release etc/calamares usr/share/calamares var/lib/dpkg/status etc/apt/sources.list.d usr/share/xsessions usr/share/wayland-sessions
python3 - <<'PY'
from pathlib import Path
print('=== OS RELEASE')
for p in [Path('root/usr/lib/os-release'),Path('root/etc/lsb-release')]:
 if p.exists(): print(p, p.read_text())
print('=== PACKAGE VERSIONS')
for paragraph in Path('root/var/lib/dpkg/status').read_text().split('\n\n'):
 lines=dict(line.split(': ',1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
 if lines.get('Package','').startswith(('plasma-workspace','plasma-desktop','calamares','neon-settings','python3-pyqt6','python3-pyside6','libreoffice','firefox','linux-image')):
  print(lines.get('Package'),lines.get('Version'))
print('=== CALAMARES PACKAGE FILE LIST')
p=Path('root/var/lib/dpkg/info/calamares-settings.list')
if p.exists(): print(p.read_text())
print('=== CALAMARES FILES')
for root in [Path('root/calamares/desktop'),Path('root/etc/calamares'),Path('root/usr/share/calamares'),Path('root/usr/etc/calamares')]:
 if not root.exists(): continue
 for p in sorted(root.rglob('*')):
  if p.is_file() and p.suffix in ('.conf','.yaml','.yml'):
   if p.name=='settings.conf' or p.name.startswith(('shellprocess','packages','unpackfs','welcome','branding','mount','users')):
    print('\n===',p,'\n',p.read_text(errors='replace')[:14000])
PY

echo '=== NATIVE QT PACKAGE CHECK'
cd "$REPO"
bash scripts/neon-package.sh
cd "$WORK"
sudo unsquashfs -no-progress -d fullroot base.squashfs
ROOT="$WORK/fullroot"
cleanup() {
  for mount in proc sys dev; do sudo umount -R "$ROOT/$mount" || true; done
}
trap cleanup EXIT
for mount in dev sys; do sudo mount --rbind "/$mount" "$ROOT/$mount"; sudo mount --make-rslave "$ROOT/$mount"; done
sudo mount -t proc proc "$ROOT/proc"
sudo rm -f "$ROOT/etc/resolv.conf"
sudo cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
sudo cp "$REPO/artifacts/erodist-neon-system.deb" "$ROOT/tmp/"
sudo cp "$REPO/scripts/neon-qt-smoke.py" "$ROOT/tmp/"
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get update
sudo chroot "$ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/erodist-neon-system.deb
sudo chroot "$ROOT" /usr/bin/python3 -X faulthandler -u /tmp/neon-qt-smoke.py
mkdir -p "$REPO/artifacts/neon-qt-captures"
sudo cp "$ROOT"/tmp/neon-qt-captures/*.png "$REPO/artifacts/neon-qt-captures/"
sudo chown -R "$(id -u):$(id -g)" "$REPO/artifacts"
