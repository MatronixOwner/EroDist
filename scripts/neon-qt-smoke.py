#!/usr/bin/python3
"""Native Qt smoke and scroll geometry; not a complete desktop or installer test."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QListWidget, QLabel, QPushButton, QScrollArea
from erodist_neon.settings import create_window

app=QApplication([])
window=create_window()
window.show()
output=Path('/tmp/neon-qt-captures')
output.mkdir(exist_ok=True)

def settle():
    loop=QEventLoop()
    QTimer.singleShot(250,loop.quit)
    loop.exec()

for width,height,font_size in [(800,600,10),(1024,768,10),(800,600,13)]:
    font=app.font(); font.setPointSize(font_size); app.setFont(font)
    # Font from a fixed stylesheet must not override accessibility scaling.
    window.resize(width,height)
    settle()
    nav=window.findChild(QListWidget)
    for index in range(nav.count()):
        nav.setCurrentRow(index); settle()
        visible=[a for a in window.findChildren(QScrollArea) if a.isVisible()]
        assert len(visible)==1
        scroll=visible[0]; content=scroll.widget()
        for widget in content.findChildren(QPushButton)+content.findChildren(QLabel):
            if not widget.isVisible(): continue
            assert widget.x()>=0 and widget.y()>=0
            assert widget.x()+widget.width()<=content.width(),widget.text()
            assert widget.y()+widget.height()<=content.height(),widget.text()
        image=window.grab()
        assert image.save(str(output/f'settings-{index}-{width}x{height}-font{font_size}.png'))
    print(f'PASS Qt page geometry {width}x{height}, font {font_size}',flush=True)
# Let the hardware reader complete before closing the Qt-owned thread.
loop=QEventLoop()
QTimer.singleShot(10000,loop.quit)
window._reader[0].finished.connect(loop.quit)
if window._reader[0].isRunning(): loop.exec()
assert not window._reader[0].isRunning()
window.close()
print('PASS native Qt window and worker lifecycle',flush=True)
