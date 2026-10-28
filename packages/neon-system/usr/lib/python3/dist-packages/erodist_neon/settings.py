"""Qt 6 settings shell; uses stock KDE backends and no background service."""
import subprocess
from pathlib import Path

SECTIONS = [
 ('Система', [('Обновления и приложения', ['plasma-discover']), ('Настройки Plasma', ['systemsettings'])]),
 ('Оформление', [('Общий стиль', ['systemsettings','kcm_lookandfeel']), ('Цвета', ['systemsettings','kcm_colors']), ('Значки', ['systemsettings','kcm_icons']), ('Шрифты', ['systemsettings','kcm_fonts'])]),
 ('Устройства', [('Экран', ['systemsettings','kcm_kscreen']), ('Звук', ['systemsettings','kcm_pulseaudio']), ('Клавиатура', ['systemsettings','kcm_keyboard'])]),
 ('Сеть и время', [('Сеть', ['systemsettings','kcm_networkmanagement']), ('Дата и время', ['systemsettings','kcm_clock'])]),
]
STYLE = '''QWidget{background:#131419;color:#eeeeef;} QMainWindow{background:#0e0f12;}
QListWidget{background:#1a1b21;border:0;border-radius:12px;min-width:150px;padding:8px;}
QListWidget::item{padding:12px;border-radius:8px;} QListWidget::item:selected{background:#363842;}
QPushButton{background:#25272f;border:1px solid #464954;border-radius:10px;padding:12px;text-align:left;}
QPushButton:hover{background:#343640;} QLabel#heading{font-size:26px;font-weight:600;}
QTextEdit{background:#1a1b21;border:1px solid #363840;border-radius:12px;padding:12px;}
QScrollArea{border:0;} QToolTip{background:#25272f;color:#eee;}'''


def create_window():
    from PySide6.QtCore import Qt, QObject, QThread, Signal
    from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QListWidget,QStackedWidget,QLabel,QPushButton,QScrollArea,QTextEdit,QFileDialog
    from .info import collect
    window=QMainWindow()
    window.setWindowTitle('EroDist — центр управления')
    window.resize(960,660)
    window.setMinimumSize(600,420)
    window.setStyleSheet(STYLE)
    root=QWidget(); window.setCentralWidget(root)
    outer=QVBoxLayout(root); outer.setContentsMargins(22,22,22,22)
    heading=QLabel('EroDist'); heading.setObjectName('heading'); outer.addWidget(heading)
    body=QHBoxLayout(); outer.addLayout(body,1)
    sidebar=QListWidget(); sidebar.setMaximumWidth(230); body.addWidget(sidebar)
    stack=QStackedWidget(); body.addWidget(stack,1)
    status=QLabel('Plasma · Qt 6 · редакция выбирается при установке'); status.setWordWrap(True); outer.addWidget(status)
    sidebar.currentRowChanged.connect(stack.setCurrentIndex)
    def page(title):
        content=QWidget(); layout=QVBoxLayout(content)
        label=QLabel(title); label.setObjectName('heading'); label.setWordWrap(True); layout.addWidget(label)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(content)
        sidebar.addItem(title); stack.addWidget(scroll)
        return layout
    def launch(command):
        try:
            subprocess.Popen(command)
            status.setText('Открыт штатный модуль KDE. Результат настройки автоматически не проверяется.')
        except OSError as exc:
            status.setText('Не удалось открыть модуль: '+str(exc))
    for title, actions in SECTIONS:
        layout=page(title)
        for text, command in actions:
            button=QPushButton(text); button.clicked.connect(lambda checked=False,args=command: launch(args)); layout.addWidget(button)
        layout.addStretch()
    layout=page('О системе и диагностика')
    report=QTextEdit(); report.setReadOnly(True); report.setPlainText('Читаем локальные сведения…'); layout.addWidget(report,1)
    save=QPushButton('Сохранить показанный отчёт…'); save.setEnabled(False); layout.addWidget(save)
    hint=QLabel('Автоотправки нет. Проверьте текст перед сохранением или передачей. Имена пользователей, IP/MAC, серийные номера, файлы и журналы не собираются.'); hint.setWordWrap(True); layout.addWidget(hint)
    def save_report():
        filename,_=QFileDialog.getSaveFileName(window,'Сохранить отчёт','erodist-report.txt','Text (*.txt)')
        if not filename: return
        try:
            import os,tempfile
            path=Path(filename); fd,name=tempfile.mkstemp(dir=path.parent,prefix='.erodist-report-')
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as file: file.write(report.toPlainText())
                os.replace(name,path)
            finally:
                if os.path.exists(name): os.unlink(name)
            status.setText('Отчёт сохранён локально. Отправки не было.')
        except OSError as exc: status.setText('Ошибка сохранения: '+str(exc))
    save.clicked.connect(save_report)
    class Reader(QObject):
        finished=Signal(str)
        def run(self):
            try: text=collect()
            except (OSError,ValueError) as exc: text='Ошибка чтения: '+str(exc)
            self.finished.emit(text)
    # The window owns thread lifetime; no UI calls from the hardware reader.
    thread=QThread(window); reader=Reader(); reader.moveToThread(thread)
    thread.started.connect(reader.run)
    reader.finished.connect(lambda text:(report.setPlainText(text),save.setEnabled(True)))
    reader.finished.connect(thread.quit)
    reader.finished.connect(reader.deleteLater)
    thread.start()
    window._reader=(thread,reader)
    def close_event(event):
        if thread.isRunning():
            status.setText('Завершаем чтение сведений…'); event.ignore()
            thread.finished.connect(window.close)
        else: event.accept()
    window.closeEvent=close_event
    sidebar.setCurrentRow(0)
    return window


def main():
    import sys
    from PySide6.QtWidgets import QApplication
    app=QApplication(sys.argv)
    app.setApplicationName('EroDist')
    window=create_window(); window.show()
    sys.exit(app.exec())
