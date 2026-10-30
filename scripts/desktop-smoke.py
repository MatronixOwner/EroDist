#!/usr/bin/python3
"""Real Qt page/keyboard/action tests; does not claim a booted Plasma session."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt,QEventLoop,QTimer,QPoint,QRect
from PySide6.QtGui import QIcon,QImage,QPainter,QColor,QFont
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from PySide6.QtTest import QTest
from erodist_control_center.app import Center
from erodist_control_center.model import SECTIONS

inventory=Path('/tmp/erodist-kcms.txt').read_text()
for actions in SECTIONS.values():
 for _,_,_,command in actions:
  if command[0]=='systemsettings' and len(command)>1:
   assert command[1] in inventory,('KDE module absent',command[1])
print('PASS native KCM module names',flush=True)
app=QApplication([])
QIcon.setThemeName('EroDist')
out=Path('/tmp/desktop-captures');out.mkdir(exist_ok=True)
window=Center();window.show()
def settle():
 loop=QEventLoop();QTimer.singleShot(60,loop.quit);loop.exec()

for size,points in [((800,600),10),((1060,740),10),((800,600),13),((640,460),13)]:
 font=app.font();font.setPointSize(points);app.setFont(font)
 window.resize(*size);settle()
 for index in range(window.navigation.count()):
  window.navigation.setCurrentRow(index);settle()
  scroll=window.pages.currentWidget();content=scroll.widget()
  assert scroll.horizontalScrollBar().maximum()==0
  for widget in content.findChildren(QLabel)+content.findChildren(QPushButton):
   if not widget.isVisible():continue
   top=widget.mapTo(content,QPoint(0,0))
   assert top.x()>=0 and top.y()>=0
   assert top.x()+widget.width()<=content.width(),(size,index,widget.objectName())
   assert top.y()+widget.height()<=content.height(),(size,index,widget.objectName())
   if isinstance(widget,QLabel) and widget.text():
    bounds=widget.fontMetrics().boundingRect(QRect(0,0,widget.contentsRect().width(),10000),Qt.TextFlag.TextWordWrap,widget.text())
    assert bounds.height()<=widget.contentsRect().height()+2,(size,index,widget.text(),bounds.height(),widget.height())
  assert window.grab().save(str(out/f'page-{index}-{size[0]}x{size[1]}-font{points}.png'))
 print('PASS page geometry',size,'font',points,flush=True)
window.navigation.setCurrentRow(0);settle()
first=window.pages.currentWidget().widget().findChildren(QPushButton)[0]
QTest.mouseClick(first,Qt.MouseButton.LeftButton);settle()
assert window.navigation.currentRow()==1
QTest.keyClick(window.navigation,Qt.Key.Key_Down);settle()
assert window.navigation.currentRow()==2
with patch('erodist_control_center.app.shutil.which',return_value=None):
 window.launch(('missing-binary',))
 assert 'не установлен' in window.status.text()
with patch('erodist_control_center.app.QProcess.startDetached',return_value=(True,123)) as launch:
 with patch('erodist_control_center.app.shutil.which',return_value='/usr/bin/systemsettings'):
  window.launch(('systemsettings','kcm_colors'))
  launch.assert_called_once_with('/usr/bin/systemsettings',['kcm_colors'])
with patch('erodist_control_center.app.QFileDialog.getSaveFileName',return_value=('','')):
 window.export()
with patch('erodist_control_center.app.QFileDialog.getSaveFileName',return_value=('/tmp/erodist-report-test.txt','Text')):
 window.export()
 assert Path('/tmp/erodist-report-test.txt').read_text()==window.report.toPlainText()
 assert Path('/tmp/erodist-report-test.txt').stat().st_mode&0o777==0o600
print('PASS navigation, keyboard, command dispatch, missing backend, save and cancel',flush=True)
# Render real installed theme assets, not an AI mockup of an application window.
icons=[('erodist-control-center','Настройки'),('erodist-files','Файлы'),('erodist-terminal','Терминал'),('erodist-browser','Браузер'),('erodist-software','Программы'),('erodist-editor','Редактор'),('erodist-display','Экран'),('erodist-network','Сеть')]
image=QImage(1000,540,QImage.Format.Format_ARGB32);image.fill(QColor('#111318'))
painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setPen(QColor('#edf0f5'));painter.setFont(QFont('Sans',20));painter.drawText(QRect(32,16,940,52),Qt.AlignmentFlag.AlignLeft,'EroDist · Graphite Icons')
for index,(name,title) in enumerate(icons):
 assert QIcon.hasThemeIcon(name),name
 icon=QIcon.fromTheme(name);assert not icon.isNull()
 x=40+(index%4)*246;y=88+(index//4)*214
 painter.drawPixmap(x+45,y,icon.pixmap(138,138))
 painter.setPen(QColor('#cbd2df'));painter.setFont(QFont('Sans',12));painter.drawText(QRect(x,y+145,224,36),Qt.AlignmentFlag.AlignCenter,title)
painter.end();assert image.save(str(out/'icons.png'))
window.resize(1060,740);window.navigation.setCurrentRow(0);settle();window.grab().save(str(out/'settings-home.png'))
window.navigation.setCurrentRow(1);settle();window.grab().save(str(out/'settings-appearance.png'))
window.close()
print('PASS installed SVG/PNG icons; captures written',flush=True)
