"""Real GTK/Ubiquity page smoke test under Xvfb; no installer/disk operations."""
import importlib.util
from gi.repository import Gtk, GLib
from erodist import settings

spec = importlib.util.spec_from_file_location('ubi_erodist', '/usr/lib/ubiquity/plugins/ubi-erodist.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Controller:
    allowed = None
    def allow_go_forward(self, value):
        self.allowed = value

controller = Controller()
page = module.PageGtk(controller)
page.sync_navigation()
assert controller.allowed is False
page.buttons['pro'].set_active(True)
assert controller.allowed is False
page.terms.set_active(True)
assert controller.allowed is True
assert page.selection() == {'edition': 'pro', 'steam_terms': True}
page.buttons['program'].set_active(True)
assert controller.allowed is True
assert page.selection() == {'edition': 'program', 'steam_terms': False}
page.buttons['home'].set_active(True)
assert controller.allowed is True
page.page.destroy()
GLib.timeout_add(1200, lambda: (Gtk.main_quit(), False)[1])
settings.main()
print('EroDist settings and native Ubiquity edition page GUI smoke passed.')
