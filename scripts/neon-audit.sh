#!/usr/bin/env bash
set -euo pipefail
WORK="$PWD/build/neon-audit"
mkdir -p "$WORK"
cd "$WORK"
URL=https://files.kde.org/neon/images/desk/user/20261025-1825/neon-user-desk-20261025-1825.iso
curl -fL --retry 3 --connect-timeout 30 -o base.iso "$URL"
curl -fL --retry 3 -o base.iso.sig "$URL.sig"
curl -fsSL --retry 3 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x45F4C354638D1F29' -o neon-key.asc
export GNUPGHOME="$WORK/gnupg"
mkdir -m 700 "$GNUPGHOME"
gpg --batch --import neon-key.asc
echo '=== SIGNING KEY FINGERPRINTS'
gpg --batch --with-colons --fingerprint
# Key identity is taken from the official download page; full fingerprint will be pinned after audit.
gpg --batch --verify base.iso.sig base.iso
echo '=== UPSTREAM SHA256'
sha256sum base.iso
xorriso -indev base.iso -ls /casper
xorriso -osirrox on -indev base.iso -extract /casper/filesystem.squashfs base.squashfs
unsquashfs -d root base.squashfs etc/os-release etc/lsb-release etc/calamares usr/share/calamares var/lib/dpkg/status etc/apt/sources.list.d usr/share/xsessions usr/share/wayland-sessions
python3 - <<'PY'
from pathlib import Path
print('=== OS RELEASE')
for p in [Path('root/etc/os-release'),Path('root/etc/lsb-release')]:
 if p.exists(): print(p, p.read_text())
print('=== PACKAGE VERSIONS')
for paragraph in Path('root/var/lib/dpkg/status').read_text().split('\n\n'):
 lines=dict(line.split(': ',1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
 if lines.get('Package','').startswith(('plasma-workspace','plasma-desktop','calamares','neon-settings','python3-pyqt6','python3-pyside6','libreoffice','firefox','linux-image')):
  print(lines.get('Package'),lines.get('Version'))
print('=== CALAMARES FILES')
for root in [Path('root/etc/calamares'),Path('root/usr/share/calamares')]:
 if not root.exists(): continue
 for p in sorted(root.rglob('*')):
  if p.is_file() and p.suffix in ('.conf','.yaml','.yml'):
   if p.name=='settings.conf' or p.name.startswith(('shellprocess','packages','unpackfs','welcome','branding','mount','users')):
    print('\n===',p,'\n',p.read_text(errors='replace')[:14000])
PY
