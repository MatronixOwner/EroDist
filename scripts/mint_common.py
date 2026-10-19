"""Pure helpers for verified Mint remastering and downloadable ISO parts."""
import hashlib
import re
from pathlib import Path


def checksum_for(text, filename):
    matches = []
    for line in text.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and fields[1].lstrip('*') == filename:
            if not re.fullmatch(r'[0-9a-fA-F]{64}', fields[0]):
                raise ValueError('Invalid SHA256 in signed manifest')
            matches.append(fields[0].lower())
    if len(matches) != 1:
        raise ValueError('Expected exactly one ISO entry in signed manifest')
    return matches[0]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def update_md5(text, changed):
    seen = set()
    lines = []
    for line in text.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            lines.append(line)
            continue
        name = fields[1].lstrip('*').removeprefix('./')
        if name in changed:
            digest = hashlib.md5()
            with Path(changed[name]).open('rb') as stream:
                for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(block)
            lines.append(f'{digest.hexdigest()}  ./{name}')
            seen.add(name)
        else:
            lines.append(line)
    for name in sorted(changed.keys() - seen):
        # Hash large squashfs by streaming rather than loading it into RAM.
        digest = hashlib.md5()
        with Path(changed[name]).open('rb') as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                digest.update(block)
        lines.append(f'{digest.hexdigest()}  ./{name}')
    return '\n'.join(lines) + '\n'
