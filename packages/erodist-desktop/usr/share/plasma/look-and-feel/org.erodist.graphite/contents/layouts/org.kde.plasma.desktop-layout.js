// Fresh-profile layout only. No phone widget, additional search service or daemon.
var panel = new Panel;
panel.location = 'bottom';
panel.height = 52;
panel.floating = true;
panel.alignment = 'center';
panel.lengthMode = 'fit';
var menu = panel.addWidget('org.kde.plasma.kickoff');
menu.currentConfigGroup = ['General'];
menu.writeConfig('icon', 'erodist-control-center');
var tasks = panel.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', ['applications:erodist-control-center.desktop', 'applications:org.kde.dolphin.desktop', 'applications:org.kde.konsole.desktop', 'applications:firefox.desktop']);
panel.addWidget('org.kde.plasma.systemtray');
panel.addWidget('org.kde.plasma.digitalclock');
var screens = desktops();
for (var i = 0; i < screens.length; ++i) {
    screens[i].wallpaperPlugin = 'org.kde.image';
    screens[i].currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    screens[i].writeConfig('Image', 'file:///usr/share/erodist-desktop/desktop.png');
}
