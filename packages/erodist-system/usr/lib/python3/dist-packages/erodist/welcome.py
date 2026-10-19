"""First-login checklist. Actions use stock, explicitly launched Mint tools."""
from pathlib import Path
import subprocess

ACTIONS = [
    ('1. Обновления', 'Проверьте обновления через штатный менеджер Mint.', ['mintupdate']),
    ('2. Драйверы', 'Просмотрите рекомендации. Проприетарные драйверы автоматически не устанавливаются.', ['driver-manager']),
    ('3. Язык системы', 'Выберите язык и установите необходимые языковые пакеты.', ['mintlocale']),
    ('4. Раскладка клавиатуры', 'Добавьте языки ввода и сочетание переключения.', ['cinnamon-settings', 'keyboard']),
    ('5. Дата и часовой пояс', 'Проверьте время перед обновлениями и входом в аккаунты.', ['cinnamon-settings', 'calendar']),
    ('6. Снимки восстановления', 'Настройте Timeshift. Снимки системы не заменяют резервные копии личных файлов.', ['timeshift-launcher']),
]


def create_window():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk
    from .onboarding import finish
    window = Gtk.Window(title='Добро пожаловать в EroDist')
    window.set_default_size(850, 680)
    window.get_style_context().add_class('erodist-window')
    header = Gtk.HeaderBar(title='Первый запуск EroDist', subtitle='Настройте систему в удобном порядке')
    header.set_show_close_button(True)
    window.set_titlebar(header)
    css = Gtk.CssProvider()
    css.load_from_path('/usr/share/erodist/style.css')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.set_border_width(20)
    window.add(box)
    intro = Gtk.Label(label='Каждый инструмент открывается только по нажатию. Здесь нет скрытой установки пакетов и смены редакции.', xalign=0)
    intro.set_line_wrap(True)
    box.pack_start(intro, False, False, 0)
    scroll = Gtk.ScrolledWindow()
    box.pack_start(scroll, True, True, 0)
    steps = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    scroll.add(steps)
    status = Gtk.Label(xalign=0)
    status.set_line_wrap(True)

    def launch(_, command):
        try:
            subprocess.Popen(command)
            status.set_text('Инструмент открыт. Выполните настройку в его окне — результат автоматически не проверяется.')
        except OSError as exc:
            status.set_text('Не удалось открыть инструмент: ' + str(exc))
    for title, description, command in ACTIONS:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class('card')
        button = Gtk.Button(label=title)
        button.connect('clicked', launch, command)
        card.pack_start(button, False, False, 0)
        label = Gtk.Label(label=description, xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(85)
        card.pack_start(label, False, False, 0)
        steps.pack_start(card, False, False, 0)
    box.pack_start(status, False, False, 0)
    row = Gtk.Box(spacing=12)
    later = Gtk.Button(label='Напомнить при следующем входе')
    later.connect('clicked', lambda *_: window.destroy())
    done = Gtk.Button(label='Больше не показывать')
    done.get_style_context().add_class('suggested-action')
    def complete(_):
        try:
            finish()
            window.destroy()
        except OSError as exc:
            status.set_text('Не удалось сохранить выбор: ' + str(exc))
    done.connect('clicked', complete)
    row.pack_start(later, True, True, 0)
    row.pack_start(done, True, True, 0)
    box.pack_start(row, False, False, 0)
    return window


def main(autostart=False):
    from .info import identity
    from .onboarding import marker_path, should_show
    if autostart:
        try:
            if not should_show(identity(), Path('/proc/cmdline').read_text(), marker_path()):
                return
        except (OSError, ValueError):
            return
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    window = create_window()
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    Gtk.main()
