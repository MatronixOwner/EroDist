"""Native edition step. Partitioning and users remain in Mint's Ubiquity modules."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from ubiquity import plugin, misc, install_misc
from erodist.editions import catalog, validate_selection
from erodist.preflight import network_check

NAME = 'erodist'
AFTER = 'prepare'
BEFORE = 'partman'
WEIGHT = 15
OEM = False
STATE = Path('/run/erodist/selection.json')


class PageGtk(plugin.PluginUI):
    # The native debconf title path corrupted Cyrillic and duplicated our heading.
    plugin_title = None

    def __init__(self, controller, *args, **kwargs):
        super().__init__()
        from gi.repository import Gtk, Gdk, Pango, GLib
        self.controller = controller
        self.network_state = None
        self.network_pending = False
        self.check_generation = 0
        self.selected = None
        self.buttons = {}
        self.description_labels = []
        self.first_map = True
        # Only this viewport scrolls. Never impose the content's natural size
        # on Ubiquity's notebook or its separate navigation buttons.
        self.page = Gtk.ScrolledWindow()
        self.page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.page.set_overlay_scrolling(False)
        self.page.set_shadow_type(Gtk.ShadowType.NONE)
        self.page.set_min_content_width(0)
        self.page.set_min_content_height(0)
        self.page.set_hexpand(True)
        self.page.set_vexpand(True)
        self.page.set_can_focus(True)
        self.page.get_style_context().add_class('erodist-editions')
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(12)
        self.content = content
        self.page.add(content)

        def text_label(text, style=None):
            label = Gtk.Label(label=text, xalign=0)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_width_chars(1)
            label.set_max_width_chars(64)
            label.set_hexpand(True)
            if style:
                label.get_style_context().add_class(style)
            self.description_labels.append(label)
            return label

        content.pack_start(text_label('Какой EroDist установить?', 'title'), False, False, 0)
        content.pack_start(text_label('Выберите редакцию. Диск и пользователь — на следующих шагах.'), False, False, 0)
        choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.pack_start(choices, False, False, 0)
        self.none = Gtk.RadioButton()
        self.none.set_active(True)
        summaries = {
            'home': 'Браузер, видео, общение и офис. Стандартный набор Mint.',
            'pro': 'Home + Steam, GameMode, MangoHud и Mesa/Vulkan.',
            'program': 'Разработка приложений и игр: инструменты, Godot 3 и Blender.',
        }
        for key, entry in catalog().items():
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.get_style_context().add_class('card')
            radio = Gtk.RadioButton.new_with_label_from_widget(self.none, entry['name'])
            radio.connect('toggled', self.choose, key)
            self.buttons[key] = radio
            card.pack_start(radio, False, False, 0)
            card.pack_start(text_label(summaries[key]), False, False, 0)
            card.pack_start(text_label(f"Диск: от {entry['recommended_disk_gib']} ГиБ. " + ('Нужен интернет.' if entry['requires_network'] else 'Без загрузок редакции.')), False, False, 0)
            details = Gtk.Expander(label='Полный состав и ограничения')
            details.add(text_label(entry['description']))
            card.pack_start(details, False, False, 0)
            choices.pack_start(card, False, False, 0)
        self.terms = Gtk.CheckButton(label='Принимаю условия Valve и установку Steam')
        terms_label = self.terms.get_child()
        terms_label.set_line_wrap(True)
        terms_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        terms_label.set_width_chars(1)
        self.terms.set_no_show_all(True)
        self.terms.connect('toggled', lambda *_: self.sync_navigation())
        content.pack_start(self.terms, False, False, 0)
        self.link = Gtk.LinkButton.new_with_label('https://store.steampowered.com/subscriber_agreement/', 'Условия Valve / Steam')
        self.link.set_halign(Gtk.Align.START)
        self.link.set_no_show_all(True)
        content.pack_start(self.link, False, False, 0)
        self.notice = text_label('Сначала выберите редакцию. Изменение диска потребует отдельного подтверждения.')
        content.pack_start(self.notice, False, False, 0)
        self.network_label = text_label('Home — без загрузок редакции. Pro и Program требуют интернет.')
        content.pack_start(self.network_label, False, False, 0)
        self.retry = Gtk.Button(label='Проверить подключение ещё раз')
        self.retry.set_halign(Gtk.Align.START)
        self.retry.set_no_show_all(True)
        self.retry.connect('clicked', lambda *_: self.start_check())
        content.pack_start(self.retry, False, False, 0)
        self.plugin_widgets = self.page
        def on_map(*_):
            self.sync_navigation()
            if self.first_map:
                self.first_map = False
                def reset_scroll():
                    self.page.grab_focus()
                    self.page.get_vadjustment().set_value(0)
                    return False
                GLib.idle_add(reset_scroll)
        self.page.connect('map', on_map)
        provider = Gtk.CssProvider()
        provider.load_from_path('/usr/share/erodist/style.css')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.page.show_all()
        self.sync_navigation()

    def choose(self, button, key):
        if button.get_active():
            self.selected = key
            self.check_generation += 1
            self.network_state = None
            self.network_pending = False
            if catalog()[key]['requires_network']:
                self.start_check()
            else:
                self.network_label.set_text('Home: загрузки редакции не нужны. Дополнительные опции Mint могут потребовать сеть.')
                self.sync_navigation()

    def start_check(self):
        if self.selected is None or not catalog()[self.selected]['requires_network']:
            return
        from gi.repository import GLib
        self.check_generation += 1
        generation = self.check_generation
        self.network_pending = True
        self.network_state = None
        self.network_label.set_text('Проверяем доступ к архиву Ubuntu… Диск пока не изменяется.')
        self.sync_navigation()
        def ready(ok, message):
            if generation == self.check_generation:
                self.network_pending = False
                self.network_state = ok
                self.network_label.set_text(message)
                self.sync_navigation()
            return False
        def work():
            ok, message = network_check()
            GLib.idle_add(ready, ok, message)
        threading.Thread(target=work, daemon=True).start()

    def can_continue(self):
        return (self.selected is not None
                and (self.selected != 'pro' or self.terms.get_active())
                and (not catalog()[self.selected]['requires_network'] or self.network_state is True))

    def sync_navigation(self):
        valid = self.can_continue()
        self.retry.set_sensitive(self.selected in ('pro', 'program') and not self.network_pending)
        self.terms.set_visible(self.selected == 'pro')
        self.link.set_visible(self.selected == 'pro')
        self.retry.set_visible(self.selected in ('pro', 'program'))
        self.terms.set_sensitive(self.selected == 'pro')
        self.controller.allow_go_forward(valid)
        if self.selected:
            self.notice.set_text(catalog()[self.selected]['name'] + ': диск выбирается отдельно. Стирание удалит данные — проверьте подтверждение.')
        top = self.page.get_toplevel()
        if hasattr(top, 'set_title'):
            top.set_title('Установка EroDist — на базе Linux Mint')
            top.get_style_context().add_class('erodist-installer')

    def selection(self):
        return {'edition': self.selected, 'steam_terms': self.terms.get_active() if self.selected == 'pro' else False}


class Page(plugin.Plugin):
    def prepare(self):
        self.ui.start_check()
        self.ui.sync_navigation()
        return None

    def ok_handler(self):
        selection = self.ui.selection()
        if not self.ui.can_continue():
            self.ui.sync_navigation()
            return
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
            key = validate_selection(json.loads(STATE.read_text()))
            progress.info('erodist/install/' + key)
            install_misc.chroot_setup(target)
            prepared = True
            return subprocess.call(['/usr/lib/erodist/provision-edition'])
        except (OSError, ValueError):
            return 1
        finally:
            if prepared:
                install_misc.chroot_cleanup(target)
