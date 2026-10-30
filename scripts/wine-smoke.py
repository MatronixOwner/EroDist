#!/usr/bin/python3
"""Exercise both Wine architectures using built-in cmd, never a user EXE."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

for package in ('wine', 'wine64', 'wine32:i386', 'fonts-wine'):
    state = subprocess.check_output(['dpkg-query', '-W', '-f=${Status}', package], text=True)
    assert state.strip() == 'install ok installed', (package, state)
assert shutil.which('wine') and shutil.which('wineserver')
print(subprocess.check_output(['wine', '--version'], text=True).strip(), flush=True)
# Stop wineserver before removing each prefix or squashing the root filesystem.
for arch in ('win64', 'win32'):
    with tempfile.TemporaryDirectory(prefix='erodist-wine-') as directory:
        home=Path(directory)/'home';home.mkdir()
        env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home/'config'), XDG_DATA_HOME=str(home/'data'), XDG_CACHE_HOME=str(home/'cache'), WINEPREFIX=str(Path(directory)/'prefix'), WINEARCH=arch,
                   WINEDEBUG='-all', WINEDLLOVERRIDES='mscoree,mshtml=', DISPLAY='')
        try:
            result = subprocess.run(['wine', 'cmd', '/c', 'echo ERODIST_WINE_OK'],
                                    env=env, text=True, capture_output=True, timeout=120)
            print(result.stdout, flush=True)
            if result.returncode != 0 or 'ERODIST_WINE_OK' not in result.stdout:
                raise RuntimeError(f'{arch} Wine smoke failed: {result.returncode}\n{result.stderr[-6000:]}')
            print('PASS Wine built-in cmd:', arch, flush=True)
        finally:
            subprocess.run(['wineserver', '-k'], env=env, timeout=20, check=False)
            subprocess.run(['wineserver', '-w'], env=env, timeout=30, check=True)
# No shared/root prefix may accidentally be baked into the image.
assert not Path('/root/.wine').exists(), 'A root Wine prefix must not be shipped'
