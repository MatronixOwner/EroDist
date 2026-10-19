"""Per-user, opt-in completion marker; no daemon and no root operations."""
import json
import os
from pathlib import Path
import tempfile


def marker_path():
    directory = os.environ.get('XDG_STATE_HOME', '')
    root = Path(directory) if directory and Path(directory).is_absolute() else Path.home() / '.local/state'
    return root / 'erodist/welcome-complete.json'


def should_show(data, cmdline, marker):
    return ('boot=casper' not in cmdline.split()
            and data.get('status') == 'complete'
            and data.get('edition') in ('home', 'pro', 'program')
            and not Path(marker).exists())


def finish(path=None):
    path = Path(path) if path is not None else marker_path()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.welcome-')
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump({'completed': True, 'schema': 1}, file)
            file.write('\n')
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
