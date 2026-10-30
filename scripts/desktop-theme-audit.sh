#!/usr/bin/env bash
set -euo pipefail
bash scripts/neon-clean-iso.sh
mkdir -p build/theme-audit
ISO=$(find artifacts/neon-clean -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$ISO" -extract /casper/filesystem.squashfs build/theme-audit/base.squashfs
unsquashfs -ll build/theme-audit/base.squashfs | grep -E '(plasmalogin|sddm|plymouth.*(conf|plymouth|script)$|display-manager.service|kwinrc)' | head -250 || true
unsquashfs -d build/theme-audit/root build/theme-audit/base.squashfs etc/X11/default-display-manager etc/sddm.conf etc/sddm.conf.d etc/plasmalogin.conf.d usr/share/sddm/themes/breeze usr/share/plasmalogin usr/share/plymouth/themes etc/plymouth calamares/desktop/modules/displaymanager.conf etc/systemd/system/display-manager.service
python3 - <<'PY'
from pathlib import Path
root=Path('build/theme-audit/root')
for p in root.rglob('*'):
 if p.is_file() and (p.name in ('default-display-manager','theme.conf','metadata.desktop','displaymanager.conf','plymouthd.conf') or p.suffix=='.plymouth'):
  print('\n===',p,'\n',p.read_text(errors='replace')[:8000])
PY
