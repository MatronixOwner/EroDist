"""Native edition step. Partitioning and users remain in Mint's Ubiquity modules."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from ubiquity import plugin, misc, install_misc
from erodist.editions import catalog, validate_selection

NAME = 'erodist'
AFTER = 'prepare'
BEFORE = 'partman'
WEIGHT = 15
OEM = False
STATE = Path('/run/erodist/selection.json')


class PageGtk(plugin.PluginUI):
    plugin_title = 'ubiquity/text/erodist'

    def __init__(self, controller, *args, **kwargs):
        super().__init__()
        from gi.repository import Gtk, Gdk
        self.controller = controller
        self.selected = None
        self.buttons = {}
        self.page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.page.get_style_context().add_class('erodist-editions')
        title = Gtk.Label(label='Какой EroDist установить?', xalign=0)
        title.get_style_context().add_class('title')
        self.page.pack_start(title, False, False, 0)
        intro = Gtk.Label(label='Редакция выбирается только здесь. Диск и пользователь — на следующих шагах.\nДополнительные пакеты загружаются во время установки; ISO содержит общую основу.', xalign=0)
        intro.set_line_wrap(True)
        self.page.pack_start(intro, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(220)
        choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scroll.add(choices)
        self.page.pack_start(scroll, True, True, 0)
        self.none = Gtk.RadioButton()
        self.none.set_active(True)
        for key, entry in catalog().items():
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            card.get_style_context().add_class('card')
            radio = Gtk.RadioButton.new_with_label_from_widget(self.none, entry['name'])
            radio.connect('toggled', self.choose, key)
            self.buttons[key] = radio
            card.pack_start(radio, False, False, 0)
            text = Gtk.Label(label=entry['description'] + f"\nРекомендуемый диск: от {entry['recommended_disk_gib']} ГиБ. " + ('Нужен интернет.' if entry['requires_network'] else 'Без дополнительных загрузок редакции.'), xalign=0)
            text.set_line_wrap(True)
            text.set_max_width_chars(85)
            card.pack_start(text, False, False, 0)
            choices.pack_start(card, False, False, 0)
        self.terms = Gtk.CheckButton(label='Для Pro: принимаю условия Valve и установку Steam')
        self.terms.connect('toggled', lambda *_: self.sync_navigation())
        self.page.pack_start(self.terms, False, False, 0)
        link = Gtk.LinkButton.new_with_label('https://store.steampowered.com/subscriber_agreement/', 'Условия Valve / Steam')
        link.set_halign(Gtk.Align.START)
        self.page.pack_start(link, False, False, 0)
        self.notice = Gtk.Label(label='Выберите редакцию. Pro и Program требуют интернет и дополнительное место. Ошибка загрузки остановит установку редакции.', xalign=0)
        self.notice.set_line_wrap(True)
        self.page.pack_start(self.notice, False, False, 0)
        self.plugin_widgets = self.page
        self.page.connect('map', lambda *_: self.sync_navigation())
        provider = Gtk.CssProvider()
        provider.load_from_path('/usr/share/erodist/style.css')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.page.show_all()

    def choose(self, button, key):
        if button.get_active():
            self.selected = key
            self.sync_navigation()

    def sync_navigation(self):
        valid = self.selected is not None and (self.selected != 'pro' or self.terms.get_active())
        self.terms.set_sensitive(self.selected == 'pro')
        self.controller.allow_go_forward(valid)
        if self.selected:
            self.notice.set_text(catalog()[self.selected]['name'] + ': проверьте выбор. Диск будет выбран отдельно; стирание может удалить данные.')
        top = self.page.get_toplevel()
        if hasattr(top, 'set_title'):
            top.set_title('Установка EroDist — на базе Linux Mint')
            top.get_style_context().add_class('erodist-installer')

    def selection(self):
        return {'edition': self.selected, 'steam_terms': self.terms.get_active() if self.selected == 'pro' else False}


class Page(plugin.Plugin):
    def prepare(self):
        self.ui.sync_navigation()
        return None

    def ok_handler(self):
        selection = self.ui.selection()
        try:
            validate_selection(selection)
        except ValueError:
            self.ui.sync_navigation()
            return
        if selection['edition'] in ('pro', 'program'):
            self.preseed_bool('apt-setup/universe', True)
        if selection['edition'] == 'pro':
            self.preseed_bool('apt-setup/multiverse', True)
        with misc.raised_privileges():
            STATE.parent.mkdir(mode=0o700, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='selection-', dir=STATE.parent)
            with os.fdopen(fd, 'w') as handle:
                json.dump(selection, handle)
            os.replace(name, STATE)
        return plugin.Plugin.ok_handler(self)


class Install(plugin.InstallPlugin):
    def install(self, target, progress, *args, **kwargs):
        # Ubiquity treats a non-zero result as a failed install step, not success.
        if os.path.realpath(target) != '/target' or not os.path.ismount('/target'):
            return 1
        prepared = False
        try:
            validate_selection(json.loads(STATE.read_text()))
            install_misc.chroot_setup(target)
            prepared = True
            return subprocess.call(['/usr/lib/erodist/provision-edition'])
        except (OSError, ValueError):
            return 1
        finally:
            if prepared:
                install_misc.chroot_cleanup(target)
