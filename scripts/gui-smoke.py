"""Real GTK/Ubiquity page smoke test under Xvfb; no installer/disk operations."""
import importlib.util
import ast
from pathlib import Path
import shutil
import sys
sys.path.insert(0, '/usr/lib/ubiquity')
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from erodist import settings, welcome, diagnostics

# Every action must name a real installed command in the Mint filesystem.
tree = ast.parse(Path(settings.__file__).read_text())
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'page':
        for label, command in ast.literal_eval(node.args[2]):
            assert shutil.which(command[0]), (label, command)

spec = importlib.util.spec_from_file_location('ubi_erodist', '/usr/lib/ubiquity/plugins/ubi-erodist.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Controller:
    allowed = None
    def allow_go_forward(self, value):
        self.allowed = value

def drain_check(page):
    loop = GLib.MainLoop()
    def done():
        if not page.network_pending:
            loop.quit()
            return False
        return True
    GLib.timeout_add(10, done)
    timeout = GLib.timeout_add(2000, lambda: (loop.quit(), False)[1])
    loop.run()
    GLib.source_remove(timeout)
    assert not page.network_pending, 'Connectivity check did not finish'

for _, _, command in welcome.ACTIONS:
    assert shutil.which(command[0]), command

# Do not contact the internet during the UI test; exercise the real async callbacks.
module.network_check = lambda: (False, 'Test: network disconnected')
controller = Controller()
page = module.PageGtk(controller)
page.sync_navigation()
assert controller.allowed is False
page.buttons['pro'].set_active(True)
assert controller.allowed is False
page.terms.set_active(True)
drain_check(page)
assert controller.allowed is False
module.network_check = lambda: (True, 'Test: archive reachable')
page.start_check()
drain_check(page)
assert controller.allowed is True
assert page.selection() == {'edition': 'pro', 'steam_terms': True}
page.buttons['program'].set_active(True)
drain_check(page)
assert controller.allowed is True
assert page.selection() == {'edition': 'program', 'steam_terms': False}
page.buttons['home'].set_active(True)
assert controller.allowed is True
page.page.destroy()
# Render the new first-run and report windows without writing user state.
w = welcome.create_window()
w.show_all()
d = diagnostics.create_window(w)
d.show_all()
GLib.timeout_add(1500, lambda: (d.destroy(), w.destroy(), False)[2])
GLib.timeout_add(2000, lambda: (Gtk.main_quit(), False)[1])
settings.main()
print('EroDist settings and native Ubiquity edition page GUI smoke passed.')
