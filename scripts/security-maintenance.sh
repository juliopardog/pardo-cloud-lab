#!/bin/sh
# Ubuntu-base security patches only; no automatic reboot or password changes.
set -eu
test "$(id -u)" -eq 0
. /etc/os-release
test "${UBUNTU_CODENAME:-}" = noble
DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades
cat > /etc/apt/apt.conf.d/52pardo-security <<'CONF'
#clear Unattended-Upgrade::Allowed-Origins;
Unattended-Upgrade::Allowed-Origins {
    "Ubuntu:noble-security";
    "UbuntuESMApps:noble-apps-security";
    "UbuntuESM:noble-infra-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "false";
CONF
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
CONF
systemctl enable --now apt-daily.timer apt-daily-upgrade.timer
if ! grep -q 'boot=casper' /proc/cmdline && ! mountpoint -q /cdrom; then
    systemctl disable casper-md5check.service
    systemctl reset-failed casper-md5check.service || true
fi
apt-config dump | grep -E 'Unattended-Upgrade::(Allowed-Origins|Automatic-Reboot)|APT::Periodic::Unattended'
systemctl --failed --no-pager
