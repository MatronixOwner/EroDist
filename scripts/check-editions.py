"""Run only in the build chroot; simulate bundles but never install them."""
from pathlib import Path
import subprocess
from erodist.editions import catalog
from ubiquity import plugin_manager

for key, entry in catalog().items():
    if entry['packages']:
        subprocess.run(['apt-get', '-s', '--no-remove', 'install', '--', *entry['packages']], check=True)
# Validate discovery/order with the actual Mint Ubiquity plugin manager.
modules = plugin_manager.load_plugins()
assert any(getattr(module, 'NAME', '') == 'erodist' for module in modules)
# Ensure the distro package is installed in the image, not only an unmanaged overlay.
subprocess.run(['dpkg-query', '-W', 'erodist-system', 'erodist-installer'], check=True)
assert Path('/usr/share/erodist/base.json').is_file()
