#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$ROOT/build" "$ROOT/artifacts/desktop"
STAGE=$(mktemp -d "$ROOT/build/desktop-package.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT
for package in erodist-icons erodist-control-center; do
    mkdir "$STAGE/$package"
    tar -C "$ROOT/packages/$package" --exclude=__pycache__ --exclude='*.pyc' -cf - . | tar -C "$STAGE/$package" -xf -
    dpkg-deb --root-owner-group --build "$STAGE/$package" "$ROOT/artifacts/desktop/$package.deb"
done
