"""Run in the actual remastered Mint root after dpkg triggers."""
import json
from pathlib import Path
import subprocess
from erodist.branding import candidates, STATE

managed = json.loads(STATE.read_text())
assert managed, 'No vendor artwork was discovered; audit the upstream layout'
assert not (set(candidates()) - set(managed)), 'Unmanaged known vendor artwork'
assert Path('/usr/share/plymouth/themes/default.plymouth').resolve() == Path('/usr/share/plymouth/themes/erodist/erodist.plymouth')
for schema, key, expected in [('org.cinnamon', 'app-menu-icon-name', "'erodist'"),
                              ('x.dm.slick-greeter', 'logo', "'/usr/share/erodist/branding/erodist.svg'")]:
    value = subprocess.check_output(['gsettings', 'get', schema, key], text=True).strip()
    assert value == expected, (schema, key, value)
for name in managed:
    path = Path(name)
    assert path.is_file() and not path.is_symlink(), name
    if path.suffix == '.svg':
        assert path.read_bytes() == Path('/usr/share/erodist/branding/erodist.svg').read_bytes(), name
slideshow = Path('/usr/share/ubiquity-slideshow/slides/index.html')
assert slideshow.read_bytes() == Path('/usr/share/erodist/branding/slideshow.html').read_bytes()
print('Branding assertions passed:', len(managed), 'managed resources')
