"""Change only boot artwork; preserve boot configs/binaries and kernel paths."""
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
from PIL import Image


def boot_image(path):
    path = PurePosixPath(path)
    return (path.parts[1:2] in [('boot',), ('isolinux',)]
            and path.suffix.lower() in ('.png', '.jpg', '.jpeg'))


def main(iso, destination):
    result = subprocess.run(['xorriso', '-indev', iso, '-find', '/', '-type', 'f', '-exec', 'echo'],
                            capture_output=True, text=True, check=True)
    replaced = []
    for line in result.stdout.splitlines():
        tokens = shlex.split(line)
        if len(tokens) != 1 or not boot_image(tokens[0]):
            continue
        name = tokens[0]
        target = Path(destination) / name.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['xorriso', '-osirrox', 'on', '-indev', iso, '-extract', name, str(target)], check=True)
        with Image.open(target) as original:
            size = original.size
        with Image.open(Path(__file__).resolve().parents[1] / 'packages/erodist-system/usr/share/backgrounds/erodist/black-gradient.png') as background:
            background.convert('RGB').resize(size).save(target)
        replaced.append(name)
    print('ISO boot backgrounds replaced:', json.dumps(replaced))


if __name__ == '__main__':
    main(*sys.argv[1:])
