// Plasma's own scripting API. No third-party widgets, phone or search service.
var panel = new Panel;
panel.location = 'bottom';
panel.height = 48;
panel.floating = true;
var menu = panel.addWidget('org.kde.plasma.kickoff');
menu.currentConfigGroup = ['General'];
menu.writeConfig('icon', '/usr/share/icons/hicolor/scalable/apps/erodist.svg');
panel.addWidget('org.kde.plasma.pager');
var tasks = panel.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', ['applications:erodist-settings.desktop','applications:org.kde.dolphin.desktop','applications:org.kde.konsole.desktop']);
panel.addWidget('org.kde.plasma.systemtray');
panel.addWidget('org.kde.plasma.digitalclock');
var desktopList = desktops();
for (var i=0; i<desktopList.length; i++) {
    desktopList[i].wallpaperPlugin = 'org.kde.image';
    desktopList[i].currentConfigGroup = ['Wallpaper','org.kde.image','General'];
    desktopList[i].writeConfig('Image','file:///usr/share/erodist-neon/black-gradient.png');
}
