#!/usr/bin/env python3
"""Reproducible, independently editable original SVG application icon assets."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
THEME=ROOT/'packages/erodist-icons/usr/share/icons/EroDist'
GLYPHS={
'files':'<path d="M65 99V83q0-10 10-10h36l16 17h53q11 0 11 11v66q0 13-13 13H78q-13 0-13-13z" fill="url(#silver)"/><path d="M65 111h126v51q0 18-18 18H83q-18 0-18-18z" fill="#a5acb7"/><path d="M80 121h96" stroke="#f8faff" stroke-opacity=".45"/>',
 'terminal':'<rect x="63" y="75" width="130" height="106" rx="16" fill="#14171c" stroke="url(#silver)" stroke-width="7"/><path d="m86 106 22 20-22 20m37 1h31" fill="none" stroke="#eef1f5" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>',
 'browser':'<circle cx="128" cy="128" r="60" fill="none" stroke="url(#silver)" stroke-width="8"/><ellipse cx="128" cy="128" rx="27" ry="60" fill="none" stroke="#c3c9d3" stroke-width="6"/><path d="M71 110h114M71 146h114M128 69v118" stroke="#c3c9d3" stroke-width="6"/>',
 'software':'<path d="M80 103h96l9 78H71z" fill="url(#silver)"/><path d="M104 102V87a24 24 0 0 1 48 0v15" fill="none" stroke="#e3e7ee" stroke-width="8"/><path d="M111 132h34m-17-17v34" stroke="#292e37" stroke-width="9" stroke-linecap="round"/>',
 'editor':'<rect x="82" y="63" width="94" height="128" rx="13" fill="url(#silver)"/><path d="M102 94h50m-50 23h50m-50 23h36m-36 23h25" stroke="#414854" stroke-width="7" stroke-linecap="round"/>',
 'appearance':'<circle cx="128" cy="128" r="60" fill="url(#silver)"/><path d="M128 68a60 60 0 0 1 0 120z" fill="#303640"/><circle cx="128" cy="128" r="60" fill="none" stroke="#e2e7ef" stroke-width="5"/>',
 'display':'<rect x="63" y="74" width="130" height="90" rx="12" fill="#262c35" stroke="url(#silver)" stroke-width="8"/><path d="M128 166v22m-30 0h60" stroke="#d9dee7" stroke-width="8" stroke-linecap="round"/>',
 'network':'<path d="M68 105q60-53 120 0m-100 23q40-35 80 0m-59 23q19-17 38 0" fill="none" stroke="url(#silver)" stroke-width="10" stroke-linecap="round"/><circle cx="128" cy="175" r="8" fill="#edf1f6"/>',
}
HEADER='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><defs><linearGradient id="tile" x2=".2" y2="1"><stop stop-color="#353b46"/><stop offset="1" stop-color="#101217"/></linearGradient><linearGradient id="silver" x2=".3" y2="1"><stop stop-color="#f6f8fb"/><stop offset="1" stop-color="#9da6b5"/></linearGradient></defs><rect x="15" y="19" width="226" height="226" rx="58" fill="#000" opacity=".25"/><rect x="16" y="13" width="224" height="224" rx="56" fill="url(#tile)" stroke="#555d6a" stroke-width="2"/><path d="M72 23h112" stroke="#dfe6f2" stroke-opacity=".15" stroke-width="2"/>'''
for name,glyph in GLYPHS.items():
 p=THEME/'scalable/apps'/f'erodist-{name}.svg';p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(HEADER+glyph+'</svg>\n')
aliases={'org.kde.dolphin':'files','system-file-manager':'files','org.kde.konsole':'terminal','utilities-terminal':'terminal','firefox':'browser','web-browser':'browser','org.kde.discover':'software','plasmadiscover':'software','org.kde.kate':'editor','accessories-text-editor':'editor','preferences-desktop-theme':'appearance','preferences-desktop-display':'display','preferences-system-network':'network'}
for name,original in aliases.items():
 p=THEME/'scalable/apps'/f'{name}.svg';p.write_text((THEME/'scalable/apps'/f'erodist-{original}.svg').read_text())
(THEME/'index.theme').write_text('''[Icon Theme]
Name=EroDist Graphite
Comment=Original graphite application icons with Breeze fallback
Inherits=breeze-dark,breeze,hicolor
Directories=scalable/apps,256x256/apps

[scalable/apps]
Size=128
Type=Scalable
MinSize=16
MaxSize=512
Context=Applications

[256x256/apps]
Size=256
Type=Fixed
Context=Applications
''')
