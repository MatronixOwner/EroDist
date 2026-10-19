#!/usr/bin/env python3
"""Build-time validation against the actual repositories and installed archinstall API."""
import json
from pathlib import Path
import subprocess
import sys

profile = Path(sys.argv[1])
config = str(profile / 'pacman.conf')
root = profile / 'airootfs'
for app in json.loads((root / 'usr/share/erodist/apps.json').read_text()).values():
    subprocess.run(['pacman', '--config', config, '-Sp', '--print-format', '%n %v %s', '--', *app['packages']], check=True)
# Import the custom profile through the installed official API without touching disks.
import runpy
cls = runpy.run_path(str(root / 'usr/share/erodist/archinstall-profile.py'))['EroDistProfile']
assert cls().name == 'EroDist XFCE'
