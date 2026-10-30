"""Explicit, non-privileged Wine launch requests. No file association or daemon."""
import os
from pathlib import Path
import shutil

class WineActionError(ValueError):
    pass


def command_for(action, filename=None):
    if os.geteuid() == 0:
        raise WineActionError('Не запускайте Windows-программы от имени администратора. Войдите обычным пользователем.')
    binary = shutil.which('wine')
    if not binary:
        raise WineActionError('Wine не найден. В образе EroDist с Wine он предустановлен; проверьте, что загружен новый ISO.')
    if action == 'configure':
        return binary, ['winecfg']
    if action == 'uninstall':
        return binary, ['uninstaller']
    if action != 'run':
        raise WineActionError('Неизвестное действие Wine.')
    try:
        path = Path(filename).resolve(strict=True)
        if path.suffix.casefold() != '.exe' or not path.is_file():
            raise WineActionError('Выберите существующий файл EXE, а не папку, архив или установочный ISO.')
        with path.open('rb') as stream:
            if stream.read(2) != b'MZ':
                raise WineActionError('Файл не похож на исполняемый EXE. Возможно, загрузка повреждена.')
    except (OSError, TypeError, RuntimeError) as exc:
        raise WineActionError('Не удалось прочитать выбранный файл: ' + str(exc)) from exc
    return binary, [str(path)]
