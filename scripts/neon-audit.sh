#!/usr/bin/env bash
set -euo pipefail
for url in https://neon.kde.org/download https://files.kde.org/neon/images/user/ https://download.kde.org/neon/images/user/current/ https://files.kde.org/neon/images/; do
  echo "=== $url"
  curl -fsSL --max-time 30 "$url" | head -c 23000 || true
  printf '\n'
done
