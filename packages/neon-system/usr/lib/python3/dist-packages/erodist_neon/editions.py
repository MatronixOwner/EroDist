"""Pure validation shared by installer UI, worker and unit tests."""
import json
from pathlib import Path
import re

CATALOG = Path('/usr/share/erodist-neon/editions.json')


def catalog(path=CATALOG):
    data = json.loads(Path(path).read_text())
    if set(data) != {'home', 'pro', 'program'}:
        raise ValueError('Invalid edition catalog')
    for entry in data.values():
        if not all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::i386)?', p) for p in entry['packages']):
            raise ValueError('Invalid package identifier')
    return data


def validate_selection(data):
    if not isinstance(data, dict) or set(data) != {'edition', 'steam_terms'}:
        raise ValueError('Choose an edition in the installer')
    if data['edition'] not in ('home', 'pro', 'program') or type(data['steam_terms']) is not bool:
        raise ValueError('Invalid edition selection')
    if data['edition'] == 'pro' and not data['steam_terms']:
        raise ValueError('Steam requires explicit acceptance of Valve terms')
    return data['edition']


def apt_install_command(packages):
    return ['apt-get', '-o', 'Acquire::Retries=2', '-o', 'Acquire::http::Timeout=30', '-o', 'Acquire::https::Timeout=30', '-y', '--no-remove', 'install', '--', *packages]
