"""Local report with preview and explicit save. No logs, identifiers or telemetry."""
import os
from pathlib import Path
import tempfile
import threading


def collect_report():
    from .info import collect
    return ('EroDist — локальный диагностический отчёт\n'
            'Содержит версию системы и основные характеристики оборудования.\n'
            'Не собирает имя пользователя, hostname, IP/MAC, серийные номера, файлы и журналы.\n'
            'Ничего автоматически не отправляется. Перед передачей проверьте текст.\n\n' + collect() + '\n')


def save_report(path, text):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.erodist-report-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create_window(parent=None):
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    window = Gtk.Window(title='Диагностика EroDist', transient_for=parent)
    window.set_default_size(800, 600)
    window.set_border_width(18)
    window.get_style_context().add_class('erodist-window')
    alive = [True]
    window.connect('destroy', lambda *_: alive.__setitem__(0, False))
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    window.add(box)
    label = Gtk.Label(label='Просмотрите отчёт перед сохранением. Автоматической отправки нет.', xalign=0)
    label.set_line_wrap(True)
    box.pack_start(label, False, False, 0)
    view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    view.set_top_margin(12)
    view.set_bottom_margin(12)
    view.get_buffer().set_text('Читаем локальные сведения…')
    scroll = Gtk.ScrolledWindow()
    scroll.add(view)
    box.pack_start(scroll, True, True, 0)
    save = Gtk.Button(label='Сохранить показанный отчёт…')
    save.set_sensitive(False)
    box.pack_start(save, False, False, 0)
    def save_clicked(_):
        dialog = Gtk.FileChooserDialog(title='Сохранить отчёт', transient_for=window,
                                       action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons('Отмена', Gtk.ResponseType.CANCEL, 'Сохранить', Gtk.ResponseType.ACCEPT)
        dialog.set_current_name('erodist-report.txt')
        dialog.set_do_overwrite_confirmation(True)
        try:
            if dialog.run() == Gtk.ResponseType.ACCEPT:
                buffer = view.get_buffer()
                save_report(dialog.get_filename(), buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True))
                label.set_text('Отчёт сохранён локально. Отправки данных не было.')
        except OSError as exc:
            label.set_text('Не удалось сохранить отчёт: ' + str(exc))
        finally:
            dialog.destroy()
    save.connect('clicked', save_clicked)
    def ready(text, success):
        if alive[0]:
            view.get_buffer().set_text(text)
            save.set_sensitive(success)
        return False
    def work():
        try:
            GLib.idle_add(ready, collect_report(), True)
        except (OSError, ValueError) as exc:
            GLib.idle_add(ready, 'Не удалось собрать отчёт: ' + str(exc), False)
    threading.Thread(target=work, daemon=True).start()
    return window
