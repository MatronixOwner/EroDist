#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/artifacts" "$ROOT/build"
STAGE=$(mktemp -d "$ROOT/build/packages.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT
for package in erodist-system erodist-installer; do
    mkdir "$STAGE/$package"
    tar -C "$ROOT/packages/$package" --exclude=__pycache__ --exclude='*.pyc' -cf - . | tar -C "$STAGE/$package" -xf -
    dpkg-deb --root-owner-group --build "$STAGE/$package" "$ROOT/artifacts/$package.deb"
done
