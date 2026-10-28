#!/usr/bin/env bash
set -euo pipefail
mkdir -p audit
for host in files.kde.org distro.kde.org; do
  for file in '' neon-user-current.iso.sha256sum neon-user-current.iso.sig; do
    echo "=== https://$host/neon/images/user/current/$file"
    curl -fsSL --max-time 30 "https://$host/neon/images/user/current/$file" | head -c 18000 || true
    printf '\n'
  done
done
