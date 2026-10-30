"""Fresh EroDist Qt 6 application, independent of the retired port prototype."""
import os
import shutil
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QProcess
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QScrollArea, QLabel,
    QPushButton, QTextEdit, QFileDialog, QMessageBox,
)
from .model import VERSION, SECTIONS, system_report, save_report

STYLE = '''
QWidget {color:#edf0f5; background:#111318;}
QLabel {background:transparent;}
QLabel#brand {font-size:21px;font-weight:700;}
QLabel#title {font-size:28px;font-weight:700;}
QLabel#muted {color:#9ba3b2;}
QLabel#eyebrow {color:#858e9e;font-size:11px;font-weight:600;}
QLabel#badge {background:#252a33;border:1px solid #3c4351;border-radius:10px;padding:7px;}
QListWidget {background:#181c23;border:1px solid #303641;border-radius:16px;padding:7px;}
QListWidget::item {padding:12px 7px;margin:3px 0;border-radius:10px;}
QListWidget::item:selected {background:#343c49;color:#fff;}
QListWidget::item:hover:!selected {background:#232a34;}
QPushButton {background:#20262f;border:1px solid #363e4b;border-radius:14px;padding:11px;}
QPushButton:hover {background:#2c3542;border-color:#7b899e;}
QPushButton:focus {border:2px solid #c1ccdc;}
QPushButton:disabled {color:#939dab;}
QPushButton#tile {text-align:left;}
QLabel#tileTitle {font-size:16px;font-weight:600;}
QTextEdit {background:#181d25;border:1px solid #363e4b;border-radius:12px;padding:12px;}
QScrollArea {border:0;}
QScrollBar:vertical {width:9px;background:#181c23;border-radius:4px;}
QScrollBar::handle:vertical {background:#505c70;min-height:28px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QToolTip {background:#252b35;color:#fff;border:1px solid #667084;}
'''


def resolve_program(name):
    executable = shutil.which(name)
    if executable:
        return executable
    if name == 'plasma-changeicons':
        # KDE installs this tool in libexec, not in PATH. No shell or privileges.
        for directory in ('/usr/lib/x86_64-linux-gnu/libexec', '/usr/lib/aarch64-linux-gnu/libexec', '/usr/libexec', '/usr/lib/libexec'):
            candidate = Path(directory) / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def label(text, role=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if role:
        widget.setObjectName(role)
    return widget


class Center(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Центр настроек EroDist')
        self.setWindowIcon(QIcon.fromTheme('erodist-control-center'))
        self.setMinimumSize(640, 460)
        self.resize(1060, 740)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(18)
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QIcon.fromTheme('erodist-control-center').pixmap(48, 48))
        header.addWidget(logo)
        header.addWidget(label('Центр настроек EroDist', 'brand'), 1)
        header.addWidget(label('PLASMA  /  QT 6', 'badge'))
        outer.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(20)
        outer.addLayout(body, 1)
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(178)
        self.navigation.setIconSize(QSize(25, 25))
        body.addWidget(self.navigation)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        self.status = label('Настройки применяются штатными средствами KDE. Приложению не нужны права администратора.', 'muted')
        outer.addWidget(self.status)
        self.theme_process = QProcess(self)
        self.theme_process.finished.connect(self.theme_finished)
        self.theme_process.errorOccurred.connect(self.theme_failed)
        self.make_home()
        for title, actions in SECTIONS.items():
            layout = self.page(title, actions[0][2], 'Выберите параметр. Он откроется в штатном модуле KDE.')
            for name, subtitle, icon, command in actions:
                button = self.tile(name, subtitle, icon)
                button.clicked.connect(lambda checked=False, cmd=command: self.launch(cmd))
                layout.addWidget(button)
            layout.addStretch()
        self.make_wine()
        self.make_about()
        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)

    def page(self, title, icon, subtitle):
        item = QListWidgetItem(QIcon.fromTheme(icon), 'Wine · EXE' if title == 'Windows-программы' else title)
        item.setToolTip(title)
        self.navigation.addItem(item)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 6, 10, 8)
        layout.setSpacing(14)
        layout.addWidget(label(title, 'title'))
        layout.addWidget(label(subtitle, 'muted'))
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return layout

    def tile(self, title, subtitle, icon):
        button = QPushButton()
        button.setObjectName('tile')
        button.setAccessibleName(title)
        button.setToolTip(subtitle)
        row = QHBoxLayout(button)
        row.setContentsMargins(14, 14, 14, 14)
        row.setSpacing(16)
        picture = QLabel()
        picture.setPixmap(QIcon.fromTheme(icon).pixmap(46, 46))
        picture.setFixedSize(46, 46)
        row.addWidget(picture)
        text = QVBoxLayout()
        text.setSpacing(5)
        text.addWidget(label(title, 'tileTitle'))
        text.addWidget(label(subtitle, 'muted'))
        row.addLayout(text, 1)
        for child in button.findChildren(QLabel):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        button.setMinimumHeight(100)
        return button

    def make_home(self):
        layout = self.page('Главная', 'erodist-control-center', 'Ваш рабочий стол. Ваши правила. Всё необходимое — рядом.')
        layout.addWidget(label('ПЕРСОНАЛЬНОЕ ПРОСТРАНСТВО', 'eyebrow'))
        for title, subtitle, icon, target in [
            ('Сделайте систему своей', 'Новые иконки EroDist, цвета и оформление', 'erodist-appearance', 1),
            ('Устройства без лишних шагов', 'Дисплей, звук, клавиатура и мышь', 'erodist-display', 2),
            ('Оставайтесь на связи', 'Подключения, дата и время', 'erodist-network', 3),
            ('Программы и обновления', 'Установка приложений через KDE Discover', 'erodist-software', 4),
        ]:
            button = self.tile(title, subtitle, icon)
            button.clicked.connect(lambda checked=False, row=target: self.navigation.setCurrentRow(row))
            layout.addWidget(button)
        layout.addStretch()

    def make_wine(self):
        layout = self.page('Windows-программы', 'erodist-terminal', 'Wine · только по вашему явному запуску')
        layout.addWidget(label('Wine не является песочницей. EXE получает доступ к вашим файлам. '
                               'Запускайте только доверенные программы. Совместимость игр, DRM и античитов не гарантируется.', 'muted'))
        for title, description, action in [
            ('Запустить EXE', 'Выбрать файл и подтвердить запуск через Wine', 'run'),
            ('Настроить Wine', 'Открыть параметры текущего пользовательского Wine-префикса', 'configure'),
            ('Удалить Windows-программу', 'Открыть стандартный список удаления программ Wine', 'uninstall'),
        ]:
            button = self.tile(title, description, 'erodist-terminal')
            button.clicked.connect(lambda checked=False, selected=action: self.wine_action(selected))
            layout.addWidget(button)
        layout.addWidget(label('При первом запуске Wine создаёт личный префикс. Дополнительные компоненты '
                               'конкретной программы могут потребовать интернета. Папка префикса не удаляется этим центром.', 'muted'))
        layout.addStretch()

    def wine_action(self, action):
        from .wine import command_for, WineActionError
        filename = None
        if action == 'run':
            filename, _ = QFileDialog.getOpenFileName(self, 'Выберите Windows-программу', '', 'Windows EXE (*.exe *.EXE)')
            if not filename:
                return
        try:
            executable, arguments = command_for(action, filename)
        except WineActionError as exc:
            self.status.setText(str(exc))
            return
        if action == 'run':
            dialog = QMessageBox(self)
            dialog.setWindowTitle('Запустить Windows-программу?')
            dialog.setTextFormat(Qt.TextFormat.PlainText)
            dialog.setText('Запустить через Wine:\n' + arguments[0])
            dialog.setInformativeText('EXE может изменять ваши файлы. Wine — не песочница. Запускайте только доверенные файлы.')
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if dialog.exec() != QMessageBox.StandardButton.Yes:
                return
        ok, _ = QProcess.startDetached(executable, arguments)
        self.status.setText('Запуск передан Wine. Это не подтверждение совместимости: ошибки самой программы могут появиться в её окне. '
                            'Windows-программа продолжит работу при закрытии центра.' if ok else
                            'Не удалось запустить Wine. Проверьте его установку и права доступа к выбранному EXE.')

    def make_about(self):
        layout = self.page('О системе', 'erodist-editor', 'Только локальные сведения. Никакой автоматической отправки.')
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setPlainText(system_report())
        self.report.setMinimumHeight(210)
        layout.addWidget(self.report)
        export = QPushButton('Сохранить показанные сведения…')
        export.clicked.connect(self.export)
        layout.addWidget(export)
        layout.addWidget(label(f'Центр настроек EroDist {VERSION}. Новое приложение для Plasma 6.\n'
                               'Мы не собираем имена пользователей, IP/MAC, серийные номера, файлы или журналы.\n'
                               'Приложение не меняет редакцию системы и не устанавливает программы самостоятельно.', 'muted'))
        layout.addStretch()

    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        self.pages.currentWidget().verticalScrollBar().setValue(0)

    def launch(self, command):
        executable = resolve_program(command[0])
        if not executable:
            self.status.setText('Компонент не установлен: ' + command[0] + '. Установите его штатным менеджером пакетов.')
            return
        if command[0] == 'plasma-changeicons':
            if self.theme_process.state() != QProcess.ProcessState.NotRunning:
                return
            self.status.setText('Применяем тему значков для текущего пользователя…')
            self.theme_process.start(executable, list(command[1:]))
            return
        ok, _ = QProcess.startDetached(executable, list(command[1:]))
        self.status.setText('Команда передана KDE. Изменения выполняются в открытом модуле, а не в этом окне.' if ok else 'Не удалось запустить компонент KDE.')

    def theme_finished(self, code, status):
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.status.setText('Тема значков EroDist применена для текущего пользователя. Некоторые приложения обновят значок после перезапуска.')
        else:
            self.status.setText('Не удалось применить тему. Выберите EroDist Graphite в штатном разделе «Значки» KDE.')

    def theme_failed(self, error):
        self.status.setText('Не удалось запустить применение темы: ' + self.theme_process.errorString())

    def export(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить сведения', 'erodist-system.txt', 'Text (*.txt)')
        if not filename:
            return
        try:
            save_report(Path(filename), self.report.toPlainText())
            self.status.setText('Сведения сохранены локально. Отправки не было.')
        except OSError as exc:
            self.status.setText('Ошибка сохранения: ' + str(exc))

    def closeEvent(self, event):
        if self.theme_process.state() != QProcess.ProcessState.NotRunning:
            self.status.setText('Дождитесь завершения применения темы значков.')
            event.ignore()
        else:
            event.accept()


def configure_icons():
    # The offscreen Qt platform does not necessarily supply desktop theme paths.
    paths = QIcon.themeSearchPaths()
    if '/usr/share/icons' not in paths:
        paths.append('/usr/share/icons')
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName('EroDist')


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Центр настроек EroDist')
    app.setDesktopFileName('erodist-control-center')
    configure_icons()
    window = Center()
    window.show()
    sys.exit(app.exec())
