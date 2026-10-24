#!/bin/sh
# No account password or SSH authentication changes.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install -m 755 "$repo/scripts/network-rules.sh" /usr/local/lib/pardo-cloud-lab/network-rules.sh
install -m 644 "$repo/systemd/pardo-network.service" /etc/systemd/system/pardo-network.service
ufw allow from 10.0.0.0/24 to any port 22 proto tcp
ufw allow from 10.0.0.0/24 to any port 8080 proto tcp
ufw allow in on tailscale0 to any port 22 proto tcp
ufw allow in on tailscale0 to any port 8080 proto tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
systemctl daemon-reload
systemctl enable --now pardo-network.service
ufw status
iptables -S PARDO-WEB
