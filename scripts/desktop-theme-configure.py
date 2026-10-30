#!/usr/bin/env python3
"""Configure only the image template and native greeter appearance, not user homes."""
import configparser
from pathlib import Path
import sys
import os
root=Path(sys.argv[1]).resolve()
assert root != Path('/') and (root/'usr/share/erodist-desktop/desktop.png').is_file()
def merge(relative, groups):
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    c=configparser.ConfigParser(interpolation=None,strict=False);c.optionxform=str
    if path.exists():c.read(path)
    for section,values in groups.items():
        if not c.has_section(section):c.add_section(section)
        for key,value in values.items():c.set(section,key,value)
    with path.open('w') as file:c.write(file,space_around_delimiters=False)
# Derive from the installed Breeze palette to retain complete accessibility roles.
colors=root/'usr/share/color-schemes/EroDistGraphite.colors'
base=root/'usr/share/color-schemes/BreezeDark.colors'
assert base.is_file(), 'Native Breeze Dark color scheme missing'
colors.write_text(base.read_text())
merge('usr/share/color-schemes/EroDistGraphite.colors',{
    'General':{'Name':'EroDist Graphite'},
    'Colors:Window':{'BackgroundNormal':'19,21,26','ForegroundNormal':'237,240,245'},
    'Colors:View':{'BackgroundNormal':'14,16,21','BackgroundAlternate':'24,28,35'},
    'Colors:Button':{'BackgroundNormal':'35,41,51'},
    'Colors:Selection':{'BackgroundNormal':'75,86,103','ForegroundNormal':'255,255,255'},
    'Colors:Complementary':{'BackgroundNormal':'20,23,29'},
})
palette={'General':{'ColorScheme':'EroDistGraphite'},'KDE':{'LookAndFeelPackage':'org.erodist.graphite','widgetStyle':'Breeze'},'Icons':{'Theme':'EroDist'}}
c=configparser.ConfigParser(interpolation=None,strict=False);c.optionxform=str;c.read(colors)
for section in c.sections():
    if section.startswith('Colors:'):
        for key,value in {'DecorationFocus':'180,190,205','DecorationHover':'140,152,170','ForegroundActive':'215,222,234','ForegroundLink':'193,205,224','ForegroundVisited':'175,184,201'}.items():c.set(section,key,value)
with colors.open('w') as file:c.write(file,space_around_delimiters=False)
merge('etc/skel/.config/kdeglobals',palette)
layout=root/'etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc'
if layout.exists():layout.unlink()  # Only the stock new-user template, never a user's profile.
merge('etc/skel/.config/plasmarc',{'Theme':{'name':'breeze-dark'}})
merge('etc/skel/.config/ksplashrc',{'KSplash':{'Engine':'none'}})
merge('etc/skel/.config/kwinrc',{'org.kde.kdecoration2':{'library':'org.kde.breeze','BorderSize':'Normal'}})
# Plasma Login Manager is the actual neon greeter. Keep PAM, autologin and services intact.
assert 'plasmalogin' in (root/'etc/X11/default-display-manager').read_text()
merge('etc/plasmalogin.conf.d/90-erodist.conf',{
    'Greeter':{'ShowClock':'true','WallpaperPluginId':'org.kde.image'},
    'Greeter][Wallpaper][org.kde.image':{'Image':'file:///usr/share/erodist-desktop/login.png'},
})
merge('var/lib/plasmalogin/.config/kdeglobals',palette)
account=next(line.split(':') for line in (root/'etc/passwd').read_text().splitlines() if line.startswith('plasmalogin:'))
for path in (root/'var/lib/plasmalogin/.config',root/'var/lib/plasmalogin/.config/kdeglobals'):
    os.chown(path,int(account[2]),int(account[3]))
merge('etc/plymouth/plymouthd.conf',{'Daemon':{'Theme':'erodist'}})
print('Configured fresh-profile desktop and native Plasma Login; authentication unchanged.')
