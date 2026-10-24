#!/bin/sh
# Restrict only this site's published port; preserve other container policies.
set -eu
iptables -nL DOCKER-USER >/dev/null
iptables -nL PARDO-WEB >/dev/null 2>&1 || iptables -N PARDO-WEB
iptables -F PARDO-WEB
iptables -A PARDO-WEB -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
iptables -A PARDO-WEB -s 10.0.0.0/24 -j RETURN
iptables -A PARDO-WEB -i tailscale0 -j RETURN
iptables -A PARDO-WEB -j DROP
iptables -C DOCKER-USER -p tcp -m conntrack --ctorigdstport 8080 -j PARDO-WEB 2>/dev/null || iptables -I DOCKER-USER 1 -p tcp -m conntrack --ctorigdstport 8080 -j PARDO-WEB
