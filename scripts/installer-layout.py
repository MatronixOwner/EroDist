"""Real GTK geometry tests, not an OS install. --stub-backend is for the fast host job."""
import importlib.util
from pathlib import Path
import sys
import types
import os
import json
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

ROOT = Path(__file__).resolve().parents[1]
if '--stub-backend' in sys.argv:
    sys.path.insert(0, str(ROOT / 'packages/erodist-system/usr/lib/python3/dist-packages'))
    backend = types.ModuleType('ubiquity')
    backend.plugin = types.SimpleNamespace(PluginUI=object, Plugin=object, InstallPlugin=object)
    backend.misc = types.SimpleNamespace()
    backend.install_misc = types.SimpleNamespace()
    sys.modules['ubiquity'] = backend
    source = ROOT / 'packages/erodist-installer/usr/lib/ubiquity/plugins/ubi-erodist.py'
else:
    sys.path.insert(0, '/usr/lib/ubiquity')
    source = Path('/usr/lib/ubiquity/plugins/ubi-erodist.py')
    # Actual package template transport, not source-string decoding alone.
    value = subprocess.run(['debconf-communicate', 'erodist-installer'], input='METAGET ubiquity/text/erodist description\n',
                           capture_output=True, text=True, check=True).stdout.strip()
    assert value == '0 EroDist edition', value
spec = importlib.util.spec_from_file_location('layout_edition', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.network_check = lambda: (False, 'Нет подтверждённого доступа к архиву Ubuntu. Подключите интернет и повторите проверку.')

class Controller:
    allowed = None
    def allow_go_forward(self, value):
        self.allowed = value
        if hasattr(self, 'next'):
            self.next.set_sensitive(value)


def settle():
    loop = GLib.MainLoop()
    GLib.timeout_add(180, lambda: (loop.quit(), False)[1])
    loop.run()


def assert_bounds(child, parent):
    x, y = child.translate_coordinates(parent, 0, 0)
    assert x >= 0 and y >= 0, (child.get_text() if isinstance(child, Gtk.Label) else str(child), x, y, str(child.get_allocation()), str(parent.get_allocation()))
    assert x + child.get_allocated_width() <= parent.get_allocated_width() + 2, (child, x, child.get_allocated_width(), parent.get_allocated_width())


def visible_label(label):
    # GTK may keep a collapsed expander's child mapped with its unallocated
    # 1x1 placeholder. It has no displayed geometry until expansion.
    ancestor = label.get_parent()
    while ancestor is not None:
        if isinstance(ancestor, Gtk.Expander) and not ancestor.get_expanded():
            return False
        ancestor = ancestor.get_parent()
    return label.get_mapped()


def run_case(width, height, font_scale):
    settings = Gtk.Settings.get_default()
    settings.set_property('gtk-font-name', f'Sans {font_scale}')
    controller = Controller()
    page = module.PageGtk(controller)
    window = Gtk.Window(title='EroDist installer — layout regression test')
    window.set_default_size(width, height)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    window.add(box)
    # Reserve space for the native wizard chrome and navigation, outside our page.
    chrome = Gtk.Label(label='EroDist installer')
    chrome.set_size_request(-1, 52)
    box.pack_start(chrome, False, False, 0)
    box.pack_start(page.page, True, True, 0)
    navigation = Gtk.Box(spacing=12)
    navigation.set_border_width(12)
    back = Gtk.Button(label='Назад')
    controller.next = Gtk.Button(label='Продолжить')
    navigation.pack_start(back, False, False, 0)
    navigation.pack_end(controller.next, False, False, 0)
    box.pack_end(navigation, False, False, 0)
    window.show_all()
    page.sync_navigation()
    settle()
    assert window.get_allocated_width() <= width, (width, window.get_size())
    assert window.get_allocated_height() <= height, (height, window.get_size())
    assert page.selected is None and controller.allowed is False
    assert page.plugin_title is None
    assert abs(page.page.get_vadjustment().get_value()) < 1
    x, y = page.buttons['home'].translate_coordinates(page.page, 0, 0)
    assert 0 <= y < page.page.get_allocated_height(), ('Home hidden at startup', y)
    for label in page.description_labels:
        if visible_label(label):
            assert_bounds(label, page.content)
    assert_bounds(controller.next, window)
    assert_bounds(back, window)
    assert navigation.get_allocation().y + navigation.get_allocated_height() <= height
    output = Path(os.environ.get('ERODIST_LAYOUT_OUTPUT', '/tmp/erodist-layout'))
    output.mkdir(parents=True, exist_ok=True)
    screenshot = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0, width, height)
    assert screenshot
    screenshot.savev(str(output / f'installer-{width}x{height}-font{font_scale}.png'), 'png', [], [])
    page.buttons['pro'].set_active(True)
    settle()
    assert page.terms.get_visible() and page.link.get_visible() and page.retry.get_visible()
    assert controller.allowed is False
    page.terms.set_active(True)
    assert controller.allowed is False  # no internet; consent alone must not enable Next
    module.network_check = lambda: (True, 'Архив Ubuntu доступен.')
    page.start_check()
    settle()
    assert controller.allowed is True
    # Everything below the fold must be reachable via a visible scrollbar.
    adjustment = page.page.get_vadjustment()
    adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size())
    settle()
    retry_y = page.retry.translate_coordinates(page.page, 0, 0)[1]
    assert 0 <= retry_y and retry_y + page.retry.get_allocated_height() <= page.page.get_allocated_height() + 1, retry_y
    screenshot = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0, width, height)
    screenshot.savev(str(output / f'installer-pro-{width}x{height}-font{font_scale}.png'), 'png', [], [])
    # Full package lists must wrap too, not enlarge the native wizard.
    def expand_all(widget):
        if isinstance(widget, Gtk.Expander):
            widget.set_expanded(True)
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                expand_all(child)
    expand_all(page.content)
    settle()
    assert window.get_allocated_width() <= width and window.get_allocated_height() <= height
    for label in page.description_labels:
        if visible_label(label):
            assert_bounds(label, page.content)
    page.buttons['home'].set_active(True)
    assert not page.terms.get_visible() and not page.retry.get_visible()
    assert controller.allowed is True
    print(json.dumps({'viewport':[width,height], 'font':font_scale, 'page_minimum':page.page.get_preferred_size()[0].width, 'result':'passed'}), flush=True)
    window.destroy()
    settle()
    module.network_check = lambda: (False, 'Нет связи с архивом Ubuntu.')


for dimensions in [(800,600,10),(1024,768,10),(800,600,13)]:
    run_case(*dimensions)
print('Installer layout checks passed; screenshots are test harnesses, not a full disk-install test.')
