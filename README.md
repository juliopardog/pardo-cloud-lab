# Pardo Cloud Lab

Private, self-hosted engineering website with measured Linux and container health,
GitHub deployment history, and seven days of host metric history.

## Build and validate

Python 3.12+, Node 22 for development checks, and npm are sufficient.
The website itself needs only Nginx; no Node runtime or database is required.

```sh
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/build.py
python3 scripts/verify.py
npm run check
npm test
python3 -m unittest discover -s tests -p 'test_*.py'
docker compose config --quiet
```

`generate.py` defines page content and styling; `assets/` holds the browser code
and icons. The build writes `website/` and a SHA-256 release manifest. Do not
commit credentials, runtime snapshots, runner installations, or SMTP settings.

## Deployment

Only pushes to this repository's `main` branch and manual main-branch dispatches
deploy. Pull-request checks execute on GitHub-hosted workers. The deployment
workflow builds and tests there, then passes static assets to the restricted
self-hosted runner. The runner has no Docker-group access or general sudo access.

`scripts/deploy.py` verifies the release, prepares a new release directory,
atomically switches the current symlink, verifies HTTP responses and revision,
and restores and verifies the previous release if those checks fail. Five recent
release directories are retained for operational rollback; scheduled backups
were explicitly deferred by the owner.

To roll back manually on the server:

```sh
sudo -u github-runner python3 /usr/local/lib/pardo-cloud-lab/rollback.py
```

Nginx is pinned by image digest. Its installed configuration is
`/etc/pardo-cloud-lab/nginx.conf`; the runtime Compose configuration is
`/etc/pardo-cloud-lab/compose.yaml`. Changes to host configuration and privileged
collectors require an administrator to install the reviewed repository files.
The static deployment workflow does not receive root privileges.

## Paths and services

| Purpose | Location |
| --- | --- |
| Website releases | `/srv/pardo-cloud-lab/releases/` |
| Live release | `/srv/pardo-cloud-lab/releases/current` |
| Aggregate browser snapshots | `/srv/pardo-cloud-lab/website/telemetry/` |
| Private history/cache | `/var/lib/pardo-telemetry/` |
| Restricted container snapshot | `/var/lib/pardo-container-monitor/` |
| Root-owned collector programs | `/usr/local/lib/pardo-cloud-lab/` |
| SMTP credentials, when configured | `/etc/pardo-cloud-lab/alerts.env` (mode 600) |

`pardo-telemetry.timer` collects host counters and a local HTTP check every fifteen
seconds. `pardo-container-monitor.timer` reads a fixed allowlist containing only
`pardo-web`; it exports health status, state, restarts and start time, never
environment variables or logs. The browser has no Docker socket or command API.
Public GitHub deploy-workflow runs refresh every five minutes without tokens.
Snapshots older than forty-five seconds are shown as unavailable.

History stores one sample per minute for seven days, starting from installation.
The network rate measures default-route interfaces to avoid double-counting
container bridge traffic. Local sampled health is not internet availability.

```sh
systemctl status pardo-telemetry.timer pardo-container-monitor.timer
journalctl -u pardo-telemetry.service -u pardo-container-monitor.service
curl http://127.0.0.1:8080/release.json
```

## Email alerts

Run `sudo python3 /usr/local/lib/pardo-cloud-lab/configure-alerts.py` in your own
terminal to enter SMTP settings and the sender's app password through a hidden
prompt. This does not change the Linux account password. Never put SMTP
credentials in GitHub, the website, or chat. The alert timer skips execution until
the private configuration file exists.

Sustained failures trigger an email after three checks; recovery triggers one
email. Alerts cover stale telemetry, local HTTP and container failures, high
CPU/RAM/disk use, and failed deployment workflows. The server cannot email while
completely offline; an independent monitor remains a separate setup step.

## Private access and maintenance

Local access: `http://10.0.0.62:8080`. Tailscale allows authorized devices to reach
the same website without public router port forwards. Each device needs login to
the owner's tailnet; use the issued server name/address after enrollment.
The original ChatGPT Sites publication is separate and is not automatically
updated by this repository.

Linux password authentication is preserved at the owner's request. The account
password is unchanged. Keep SSH keys private and review tailnet membership.
The administrator-installed `scripts/security-maintenance.sh` configures daily
Ubuntu-base security updates without automatic reboots. Linux Mint-specific,
Tailscale, and pinned container updates still need periodic review.
Backups, a real reboot test, router address reservation, and a complete outage
monitor require follow-up. There is no contact-submission backend; the contact
page links to the owner's existing GitHub and business website.
