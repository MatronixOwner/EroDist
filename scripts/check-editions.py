"""Run only in the build chroot; simulate bundles but never install them."""
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, '/usr/lib/ubiquity')
from erodist.editions import catalog
from ubiquity import plugin_manager

for key, entry in catalog().items():
    if entry['packages']:
        subprocess.run(['apt-get', '-s', '--no-remove', 'install', '--', *entry['packages']], check=True)
# Validate discovery/order with the actual Mint Ubiquity plugin manager.
modules = plugin_manager.load_plugins()
names = [module.NAME for module in plugin_manager.order_plugins(modules)]
assert names.index('prepare') < names.index('erodist') < names.index('partman'), names
# Ensure the distro package is installed in the image, not only an unmanaged overlay.
subprocess.run(['dpkg-query', '-W', 'erodist-system', 'erodist-installer'], check=True)
assert Path('/usr/share/erodist/base.json').is_file()
