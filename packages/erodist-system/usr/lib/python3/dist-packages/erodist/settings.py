"""EroDist's settings hub. Mint backends remain available for compatibility."""
from pathlib import Path
import subprocess
import threading


def main():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GLib
    from .info import collect
    window = Gtk.Window(title='Центр настроек EroDist')
    window.set_default_size(960, 650)
    window.set_border_width(18)
    window.get_style_context().add_class('erodist-window')
    window.connect('destroy', Gtk.main_quit)
    header = Gtk.HeaderBar(title='EroDist', subtitle='Настройки системы')
    header.set_show_close_button(True)
    window.set_titlebar(header)
    css = Gtk.CssProvider()
    css.load_from_path('/usr/share/erodist/style.css')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.add(outer)
    body = Gtk.Box(spacing=20)
    outer.pack_start(body, True, True, 0)
    stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
    sidebar = Gtk.StackSidebar(stack=stack)
    sidebar.get_style_context().add_class('sidebar')
    body.pack_start(sidebar, False, False, 0)
    body.pack_start(stack, True, True, 0)
    status = Gtk.Label(label='Редакция выбирается только при установке. Обновления и пакеты обслуживает Mint.', xalign=0)
    status.set_line_wrap(True)
    outer.pack_end(status, False, False, 0)

    def launch(args):
        try:
            subprocess.Popen(args)
        except OSError as exc:
            status.set_text('Не удалось открыть системный модуль: ' + str(exc))

    def page(key, title, actions):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(14)
        heading = Gtk.Label(label=title, xalign=0)
        heading.get_style_context().add_class('title')
        box.pack_start(heading, False, False, 8)
        for text, args in actions:
            button = Gtk.Button(label=text)
            button.set_halign(Gtk.Align.FILL)
            button.connect('clicked', lambda _, command=args: launch(command))
            box.pack_start(button, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.add(box)
        stack.add_titled(scroll, key, title)
        return box

    page('system', 'Система', [('Обновления', ['mintupdate']), ('Приложения', ['mintinstall']), ('Источники пакетов', ['mintsources']), ('Драйверы', ['mintdrivers'])])
    page('personal', 'Оформление', [('Темы и значки', ['cinnamon-settings', 'themes']), ('Обои', ['cinnamon-settings', 'backgrounds']), ('Панель', ['cinnamon-settings', 'panel']), ('Шрифты', ['cinnamon-settings', 'fonts'])])
    page('devices', 'Устройства', [('Дисплеи', ['cinnamon-settings', 'display']), ('Звук', ['cinnamon-settings', 'sound']), ('Клавиатура', ['cinnamon-settings', 'keyboard']), ('Мышь и тачпад', ['cinnamon-settings', 'mouse']), ('Питание', ['cinnamon-settings', 'power'])])
    page('network', 'Сеть и доступ', [('Сеть', ['cinnamon-settings', 'network']), ('Bluetooth', ['blueman-manager']), ('Пользователи', ['cinnamon-settings-users']), ('Конфиденциальность', ['cinnamon-settings', 'privacy'])])
    box = page('about', 'О системе', [])
    view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    view.set_top_margin(12)
    view.set_bottom_margin(12)
    view.get_style_context().add_class('card')
    view.get_buffer().set_text('Сбор локальных сведений…')
    box.pack_start(view, True, True, 0)
    copy = Gtk.Button(label='Скопировать сведения')
    copy.set_sensitive(False)
    def copy_info(_):
        buf = view.get_buffer()
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True), -1)
        status.set_text('Скопировано. Автоматической отправки данных нет.')
    copy.connect('clicked', copy_info)
    box.pack_start(copy, False, False, 0)
    def ready(text):
        view.get_buffer().set_text(text)
        copy.set_sensitive(True)
        return False
    def work():
        try:
            text = collect()
        except (OSError, ValueError) as exc:
            text = 'Не удалось прочитать сведения: ' + str(exc)
        GLib.idle_add(ready, text)
    threading.Thread(target=work, daemon=True).start()
    window.show_all()
    Gtk.main()
