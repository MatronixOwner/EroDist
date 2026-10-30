"""Non-privileged local model. No network, logs, account or storage identifiers."""
import os
from pathlib import Path
import platform
import tempfile

VERSION = '0.2.0'
# title, subtitle, icon name, native KDE command
SECTIONS = {
    'Оформление': [
        ('Иконки EroDist', 'Применить новую тему значков для текущего пользователя', 'erodist-appearance', ('plasma-changeicons', 'EroDist')),
        ('Общий стиль', 'Темы рабочего стола и оформление окон', 'erodist-appearance', ('systemsettings', 'kcm_lookandfeel')),
        ('Цвета', 'Цветовая схема приложений', 'erodist-appearance', ('systemsettings', 'kcm_colors')),
        ('Шрифты', 'Размер и сглаживание текста', 'erodist-editor', ('systemsettings', 'kcm_fonts')),
    ],
    'Устройства': [
        ('Экран', 'Разрешение, масштаб и расположение мониторов', 'erodist-display', ('systemsettings', 'kcm_kscreen')),
        ('Звук', 'Вывод, микрофон и громкость приложений', 'erodist-terminal', ('systemsettings', 'kcm_pulseaudio')),
        ('Клавиатура', 'Раскладки и поведение клавиш', 'erodist-terminal', ('systemsettings', 'kcm_keyboard')),
        ('Мышь', 'Скорость указателя и кнопки', 'erodist-display', ('systemsettings', 'kcm_mouse')),
    ],
    'Сеть': [
        ('Подключения', 'Wi-Fi, Ethernet и параметры соединений', 'erodist-network', ('systemsettings', 'kcm_networkmanagement')),
        ('Дата и время', 'Часовой пояс и синхронизация часов', 'erodist-browser', ('systemsettings', 'kcm_clock')),
    ],
    'Приложения': [
        ('Программы и обновления', 'Открыть штатный магазин KDE Discover', 'erodist-software', ('plasma-discover',)),
        ('Все настройки KDE', 'Дополнительные параметры штатной системы', 'erodist-control-center', ('systemsettings',)),
    ],
}


def system_report():
    try:
        release = platform.freedesktop_os_release()
        name = release.get('PRETTY_NAME', 'Linux')
    except OSError:
        name = 'Linux'
    try:
        ram = next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))
        memory = f'{int(ram) / 1048576:.1f} ГиБ'
    except (OSError, StopIteration, ValueError):
        memory = 'Не определено'
    return '\n'.join([
        f'Центр настроек EroDist · {VERSION}',
        f'Система: {name}',
        f'Ядро: {platform.release()}',
        f'Архитектура: {platform.machine()}',
        f'Оперативная память: {memory}',
        'Приложение не проверяет, выполнены ли настройки во внешних модулях KDE.',
    ])


def save_report(path, text):
    """Explicit export only; mode 0600, atomic replacement, no symlink traversal."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.erodist-report-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
