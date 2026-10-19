"""Local, reviewable Archinstall profile; no partition choices or credentials here."""
from pathlib import Path
import shutil
from archinstall.default_profiles.profile import Profile, ProfileType


class EroDistProfile(Profile):
    def __init__(self):
        super().__init__('EroDist XFCE', ProfileType.Custom)

    @property
    def packages(self):
        return Path('/usr/share/erodist/desktop-packages.txt').read_text().splitlines()

    def install(self, install_session):
        install_session.add_additional_packages(self.packages)

    def post_install(self, install_session):
        # Only EroDist's reviewed desktop overlay, not the Live rootfs/accounts.
        target = Path(install_session.target)
        source = Path('/usr/share/erodist/target-overlay')
        for folder in ['etc', 'usr']:
            shutil.copytree(source / folder, target / folder, dirs_exist_ok=True, symlinks=True)
        locale = target / 'etc/locale.gen'
        with locale.open('a') as handle:
            handle.write('\nru_RU.UTF-8 UTF-8\nen_US.UTF-8 UTF-8\n')
        install_session.arch_chroot('locale-gen')
        theme = target / 'usr/share/themes'
        shutil.copytree(theme / 'Arc-Dark/xfwm4', theme / 'EroDist-Black/xfwm4', dirs_exist_ok=True)
        resource = theme / 'Arc-Dark/gtk-3.0/gtk.gresource'
        if resource.is_file():
            shutil.copy2(resource, theme / 'EroDist-Black/gtk-3.0/gtk.gresource')
        install_session.enable_service(['NetworkManager', 'lightdm'])
        install_session.arch_chroot('systemctl set-default graphical.target')
        # Multilib is official; enable it for Steam, never add AUR or third-party repos.
        config = target / 'etc/pacman.conf'
        text = config.read_text()
        import re
        text = re.sub(r'(?m)^#\[multilib\]\n#Include = /etc/pacman.d/mirrorlist', '[multilib]\nInclude = /etc/pacman.d/mirrorlist', text)
        config.write_text(text)
