#!/usr/bin/env bash
# A reproducible clean starting point: upstream bytes, no previous EroDist overlay.
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORK="$REPO/build/neon-clean"
OUT="$REPO/artifacts/neon-clean"
mkdir -p "$WORK" "$OUT"
readarray -t SOURCE < <(python3 - "$REPO/neon/source.json" <<'PY'
import json,sys
from urllib.parse import urlparse
s=json.load(open(sys.argv[1]))
u=urlparse(s['url'])
assert u.scheme=='https' and u.hostname=='files.kde.org'
assert u.path.endswith('.iso')
assert len(s['sha256'])==64 and all(c in '0123456789abcdef' for c in s['sha256'])
assert len(s['signing_fingerprint'])==40
for value in (s['url'],s['sha256'],s['signing_fingerprint'],u.path.rsplit('/',1)[1]):print(value)
PY
)
[ "${#SOURCE[@]}" -eq 4 ]
URL=${SOURCE[0]}; HASH=${SOURCE[1]}; FINGERPRINT=${SOURCE[2]}; NAME=${SOURCE[3]}
ISO="$OUT/$NAME"
curl --fail --location --retry 3 --connect-timeout 30 --max-time 1200 -o "$ISO" "$URL"
printf '%s  %s\n' "$HASH" "$ISO" | sha256sum -c -
curl --fail --location --retry 3 --max-time 120 -o "$WORK/upstream.sig" "$URL.sig"
curl --fail --location --retry 3 --max-time 120 -o "$WORK/key.asc" \
  "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$FINGERPRINT"
export GNUPGHOME
GNUPGHOME=$(mktemp -d "$WORK/gnupg.XXXXXX")
chmod 700 "$GNUPGHOME"
gpg --batch --import "$WORK/key.asc"
ACTUAL=$(gpg --batch --with-colons --fingerprint | awk -F: '$1=="fpr" {print $10; exit}')
[ "$ACTUAL" = "$FINGERPRINT" ]
gpg --batch --status-fd 1 --verify "$WORK/upstream.sig" "$ISO" > "$WORK/signature-status.txt"
grep -q '^\[GNUPG:\] VALIDSIG ' "$WORK/signature-status.txt"
# Inspect the unchanged upstream BIOS/UEFI boot records and filesystem manifest.
xorriso -indev "$ISO" -report_el_torito plain > "$WORK/boot.txt" 2>&1
cat "$WORK/boot.txt"
grep -Eq 'El Torito boot img.*BIOS' "$WORK/boot.txt"
grep -Eq 'El Torito boot img.*UEFI' "$WORK/boot.txt"
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.manifest "$WORK/filesystem.manifest"
python3 - "$WORK/filesystem.manifest" <<'PY'
from pathlib import Path
import sys
packages={line.split()[0] for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()}
assert {'plasma-workspace','calamares'} <= packages
assert not {'erodist-system','erodist-installer','erodist-neon-system','cinnamon'} & packages
print('PASS: stock Plasma and Calamares; no old EroDist packages or Cinnamon')
PY
(cd "$OUT" && sha256sum "$NAME") > "$WORK/SHA256SUMS"
python3 - "$REPO/neon/source.json" "$WORK/verification.json" <<'PY'
import json,sys
from pathlib import Path
s=json.load(open(sys.argv[1]))
s.update(kind='clean-upstream-base',modified=False,old_erodist_packages=False,
         validation='Pinned SHA256 and GPG verified; BIOS/UEFI boot records inspected. VM boot, installation and Hyper-V not tested.')
Path(sys.argv[2]).write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
PY
cat "$WORK/SHA256SUMS"
echo 'SUCCESS: one full, unchanged official neon ISO ready for ZIP upload.'
