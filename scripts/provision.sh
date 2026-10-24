#!/bin/sh
# Administrator-only installation. Static deployment never executes this script.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test "$(id -u)" -eq 0
python3 "$repo/scripts/verify.py" "$repo/website"
systemctl stop pardo-telemetry.timer pardo-container-monitor.timer
systemctl stop pardo-telemetry.service pardo-container-monitor.service
install -d -m 755 /etc/pardo-cloud-lab /usr/local/lib/pardo-cloud-lab
install -d -o github-runner -g github-runner -m 755 /srv/pardo-cloud-lab/releases
install -d -o julio -g julio -m 755 /srv/pardo-cloud-lab/website/telemetry /var/lib/pardo-telemetry /var/lib/pardo-alerts
install -d -o root -g root -m 755 /var/lib/pardo-container-monitor
for script in telemetry.py container-monitor.py alerts.py; do
  install -o root -g root -m 644 "$repo/monitoring/$script" "/usr/local/lib/pardo-cloud-lab/$script"
done
install -m 644 "$repo/scripts/configure-alerts.py" /usr/local/lib/pardo-cloud-lab/configure-alerts.py
for unit in "$repo"/systemd/*; do install -m 644 "$unit" /etc/systemd/system/; done
install -m 644 "$repo/nginx.conf" /etc/pardo-cloud-lab/nginx.conf
install -m 644 "$repo/compose.yaml" /etc/pardo-cloud-lab/compose.yaml
if [ ! -L /srv/pardo-cloud-lab/releases/current ]; then
  initial="bootstrap-$(date +%Y%m%d%H%M%S)"
  cp -a "$repo/website" "/srv/pardo-cloud-lab/releases/$initial"
  chown -R github-runner:github-runner "/srv/pardo-cloud-lab/releases/$initial"
  ln -s "$initial" /srv/pardo-cloud-lab/releases/current
fi
docker compose -p pardo-cloud-lab -f /etc/pardo-cloud-lab/compose.yaml config --quiet
docker compose -p pardo-cloud-lab -f /etc/pardo-cloud-lab/compose.yaml up -d --no-deps web
docker exec pardo-web nginx -t
systemctl daemon-reload
systemctl start pardo-container-monitor.service pardo-telemetry.service
systemctl enable --now pardo-container-monitor.timer pardo-telemetry.timer pardo-alerts.timer
curl --fail --silent http://127.0.0.1:8080/release.json
