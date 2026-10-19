#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $EUID -eq 0 ]] || { echo 'Build inside privileged Arch Linux container as root.' >&2; exit 1; }
command -v mkarchiso >/dev/null
VERSION=0.7.0-arch1
PROFILE="$ROOT/build/profile"
[[ ! -e "$PROFILE" ]] || { echo 'Use a fresh build directory for archiso.' >&2; exit 1; }
mkdir -p "$ROOT/build" "$ROOT/artifacts"
cp -a /usr/share/archiso/configs/releng "$PROFILE"
# Keep upstream boot configuration/kernel hooks; remove unneeded rescue services.
rm -rf "$PROFILE/airootfs/etc/systemd/system" "$PROFILE/airootfs/etc/systemd/network"
rm -f "$PROFILE/airootfs/etc/resolv.conf"
cp -a "$ROOT/archiso/airootfs/." "$PROFILE/airootfs/"
cat "$ROOT/archiso/packages.x86_64" > "$PROFILE/packages.x86_64"
# archiso's required boot/runtime tools, sourced from its maintained releng list.
grep -E '^(archiso|mkinitcpio|mkinitcpio-archiso|syslinux|edk2-shell|efibootmgr|dosfstools|e2fsprogs|btrfs-progs|grub|memtest86\+|memtest86\+-efi|dmidecode|smartmontools|parted|cryptsetup|squashfs-tools|nvme-cli|openssh)$' /usr/share/archiso/configs/releng/packages.x86_64 >> "$PROFILE/packages.x86_64"
sort -u -o "$PROFILE/packages.x86_64" "$PROFILE/packages.x86_64"
# Official signed repositories, including multilib for Steam. Never use partial upgrades.
cp /etc/pacman.conf "$PROFILE/pacman.conf"
if ! grep -q '^\[multilib\]' "$PROFILE/pacman.conf"; then
  printf '\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n' >> "$PROFILE/pacman.conf"
fi
cp "$PROFILE/pacman.conf" "$PROFILE/airootfs/etc/pacman.conf"
cat >> "$PROFILE/profiledef.sh" <<'PROFILEDEF'
iso_name="erodist"
iso_label="ERODIST_ARCH"
iso_publisher="EroDist"
iso_application="EroDist Arch Linux XFCE"
iso_version="0.7.0-arch1"
install_dir="erodist"
airootfs_image_type="squashfs"
# Faster decompression for Live application launch than the old XZ image.
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15' '-b' '1M')
file_permissions["/etc/sudoers.d/10-erodist"]="0:0:440"
PROFILEDEF
# Make target payload BEFORE adding Live services; users/passwords never copied.
PAYLOAD="$PROFILE/airootfs/usr/share/erodist/target-overlay"
mkdir -p "$PAYLOAD/etc" "$PAYLOAD/usr"
for path in etc/xdg etc/skel etc/lightdm etc/default etc/erodist-version etc/sudoers.d usr/local usr/share/applications usr/share/backgrounds usr/share/themes usr/share/erodist usr/share/polkit-1; do
  [[ -e "$PROFILE/airootfs/$path" ]] || continue
  [[ "$path" != usr/share/erodist ]] || continue
  mkdir -p "$PAYLOAD/$(dirname "$path")"
  cp -a "$PROFILE/airootfs/$path" "$PAYLOAD/$path"
done
mkdir -p "$PAYLOAD/usr/share/erodist"
cp "$PROFILE/airootfs/usr/share/erodist/"*.{json,html} "$PAYLOAD/usr/share/erodist/"
# Target packages omit build/install-only tools, keep the same XFCE applications.
grep -v -E '^(archinstall|arch-install-scripts)$' "$ROOT/archiso/packages.x86_64" > "$PROFILE/airootfs/usr/share/erodist/desktop-packages.txt"
rm -f "$PAYLOAD/usr/local/libexec/erodist-live-setup" "$PAYLOAD/usr/local/libexec/erodist-image-setup"
# lightdm and NetworkManager, not simultaneous networkd/resolved or root autologin.
SYSTEM="$PROFILE/airootfs/etc/systemd/system"
mkdir -p "$SYSTEM/multi-user.target.wants" "$SYSTEM/graphical.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$SYSTEM/multi-user.target.wants/NetworkManager.service"
ln -sf /usr/lib/systemd/system/systemd-timesyncd.service "$SYSTEM/multi-user.target.wants/systemd-timesyncd.service"
ln -sf /usr/lib/systemd/system/lightdm.service "$SYSTEM/display-manager.service"
ln -sf /usr/lib/systemd/system/graphical.target "$SYSTEM/default.target"
ln -sf ../erodist-live-setup.service "$SYSTEM/graphical.target.wants/erodist-live-setup.service"
ln -sf /run/NetworkManager/resolv.conf "$PROFILE/airootfs/etc/resolv.conf"
printf 'erodist\n' > "$PROFILE/airootfs/etc/hostname"
# Executable overlay permissions must survive mkarchiso's ownership handling.
while IFS= read -r executable; do
  relative="${executable#"$PROFILE/airootfs"}"
  printf 'file_permissions["%s"]="0:0:755"\n' "$relative" >> "$PROFILE/profiledef.sh"
done < <(find "$PROFILE/airootfs/usr/local" -type f -perm /111)
# Fail on missing/renamed packages in the current Arch repositories, including catalog.
pacman --config "$PROFILE/pacman.conf" -Sy --noconfirm
python3 "$ROOT/scripts/check-arch.py" "$PROFILE"
pacman -Q > "$ROOT/artifacts/build-tools.txt"
mkarchiso -v -w "$ROOT/build/work" -o "$ROOT/artifacts" "$PROFILE"
cd "$ROOT/artifacts"
sha256sum *.iso > SHA256SUMS
