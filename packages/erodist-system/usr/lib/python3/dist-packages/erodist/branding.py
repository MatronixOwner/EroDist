"""Replace distro artwork, not package names/trust/credits. Reversible dpkg diversions."""
import json
import os
from pathlib import Path
import re
import subprocess

ASSETS = Path('/usr/share/erodist/branding')
STATE = Path('/var/lib/erodist/branding.json')
ROOTS = ('usr/share/icons', 'usr/share/pixmaps', 'usr/share/linuxmint',
         'usr/lib/linuxmint', 'usr/share/cinnamon', 'usr/share/ubiquity',
         'usr/share/ubiquity-slideshow', 'usr/share/backgrounds/linuxmint',
         'usr/share/plymouth/themes')
EXTENSIONS = {'.png', '.svg', '.jpg', '.jpeg', '.xpm', '.gif'}


def is_vendor_art(path):
    path = Path(path)
    if path.suffix.lower() not in EXTENSIONS:
        return False
    name = path.name.lower()
    parts = path.as_posix().lower()
    return (name.startswith(('mint', 'linuxmint', 'lm-logo', 'ubiquity'))
            or path.stem.lower() in ('distributor-logo', 'distributor-logo-symbolic', 'start-here', 'start-here-symbolic')
            or re.search(r'(^|[-_])linuxmint', name) is not None
            or '/backgrounds/linuxmint/' in '/' + parts
            or ('/linuxmint/common/artwork/' in '/' + parts)
            or ('/plymouth/themes/' in '/' + parts and 'mint' in parts)
            or ('logo' in name and '/linuxmint/' in '/' + parts))


def candidates(root=Path('/')):
    root = Path(root)
    found = set()
    for directory in ROOTS:
        base = root / directory
        if base.exists():
            for path in base.rglob('*'):
                if (path.is_file() or path.is_symlink()) and is_vendor_art(path.relative_to(root)):
                    found.add('/' + path.relative_to(root).as_posix())
    return sorted(found)


def render(path, background=False):
    from PIL import Image, ImageDraw
    suffix = path.suffix.lower()
    if suffix == '.svg':
        path.write_bytes((ASSETS / 'erodist.svg').read_bytes())
        return
    size = (256, 256)
    try:
        with Image.open(path) as source:
            size = source.size
    except (OSError, ValueError):
        pass
    if max(size) > 512 or background:
        with Image.open('/usr/share/backgrounds/erodist/black-gradient.png') as source:
            image = source.convert('RGB').resize(size)
    else:
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x, y = size
        draw.rounded_rectangle((0, 0, x-1, y-1), radius=min(x,y)*0.2, fill='#17181c')
        for box in ((.25,.22,.375,.78),(.25,.22,.75,.33),(.25,.445,.69,.555),(.25,.67,.75,.78)):
            draw.rectangle(tuple(round(n * (x if i % 2 == 0 else y)) for i,n in enumerate(box)), fill='#eeeeef')
    # XPM output is optional in Pillow; GTK accepts PNG by signature under this name.
    fmt = {'.jpg':'JPEG', '.jpeg':'JPEG', '.gif':'GIF'}.get(suffix, 'PNG')
    if fmt == 'JPEG':
        image = image.convert('RGB')
    image.save(path, format=fmt)


def divert(path, managed):
    if path not in managed:
        subprocess.run(['dpkg-divert', '--package', 'erodist-system', '--add', '--rename',
                        '--divert', path + '.erodist-original', path], check=True)
        managed.append(path)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(managed, indent=2) + '\n')


def apply():
    if os.geteuid() != 0:
        raise SystemExit('Branding requires root')
    managed = json.loads(STATE.read_text()) if STATE.exists() else []
    for filename in candidates():
        path = Path(filename)
        # Read dimensions before diverting the upstream resource.
        from PIL import Image
        dimensions = None
        try:
            with Image.open(path) as source:
                dimensions = source.size
        except (OSError, ValueError):
            pass
        divert(filename, managed)
        if path.is_symlink():
            path.unlink()
        if dimensions and not path.exists() and path.suffix.lower() != '.svg':
            Image.new('RGB', dimensions).save(path, format='PNG')
        render(path, '/backgrounds/' in filename)
    slideshow = Path('/usr/share/ubiquity-slideshow/slides/index.html')
    if slideshow.exists():
        divert(str(slideshow), managed)
        if slideshow.is_symlink():
            slideshow.unlink()
        slideshow.write_bytes((ASSETS / 'slideshow.html').read_bytes())
    print('EroDist branding: managed', len(managed), 'upstream resources')


def restore():
    if not STATE.exists():
        return
    for filename in reversed(json.loads(STATE.read_text())):
        path = Path(filename)
        if path.is_file() or path.is_symlink():
            path.unlink()
        subprocess.run(['dpkg-divert', '--package', 'erodist-system', '--remove', '--rename',
                        '--divert', filename + '.erodist-original', filename], check=True)
    STATE.unlink()


if __name__ == '__main__':
    import sys
    restore() if sys.argv[1:] == ['restore'] else apply()
