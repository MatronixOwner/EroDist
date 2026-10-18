import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    id: presentation
    Timer {
        interval: 14000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }
    function onActivate() { presentation.currentSlide = 0; }
    Slide {
        Rectangle { anchors.fill: parent; color: "#191919" }
        Column {
            anchors.centerIn: parent
            width: parent.width * 0.85
            spacing: 24
            Text { width: parent.width; text: "EroDist 0.4"; color: "#ffffff"; font.pixelSize: 36; horizontalAlignment: Text.AlignHCenter }
            Text { width: parent.width; text: qsTr("Удобная система на Debian с рабочим столом XFCE. Установка продолжается — не выключайте компьютер."); color: "#cccccc"; font.pixelSize: 19; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#191919" }
        Column {
            anchors.centerIn: parent
            width: parent.width * 0.85
            spacing: 24
            Text { width: parent.width; text: qsTr("Всё под рукой"); color: "#ffffff"; font.pixelSize: 32; horizontalAlignment: Text.AlignHCenter }
            Text { width: parent.width; text: qsTr("Центр настроек, обновления, скриншоты и каталог программ с Python. После установки создайте резервные копии важных файлов."); color: "#cccccc"; font.pixelSize: 19; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
        }
    }
}
