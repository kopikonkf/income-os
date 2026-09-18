#!/usr/bin/env bash
set -euo pipefail
ROOT="${DIE_HOME:-/srv/die}"
[[ ${EUID:-$(id -u)} -eq 0 ]] || exit 2
install -m 0755 "$ROOT/company/browser/linux/founder_display12_session_init.sh" /usr/local/bin/die-founder-display12-init
install -m 0755 "$ROOT/company/browser/linux/founder_browser_handoff.sh" /usr/local/bin/die-founder-browser-handoff
install -m 0755 "$ROOT/company/browser/linux/founder_no_cdp_repair.sh" /usr/local/bin/die-founder-no-cdp-repair
install -o kopiko -g kopiko -m 0755 "$ROOT/company/muxia/config/linux/xrdp/xsession" /home/kopiko/.xsession
install -m 0644 "$ROOT/company/browser/linux/die-principal-browser-broker.service" /etc/systemd/system/die-principal-browser-broker.service
install -m 0644 "$ROOT/company/muxia/scripts/linux/die-muxia-dispatch.service" /etc/systemd/system/die-muxia-dispatch.service
systemctl daemon-reload
runuser -u kopiko -- env DISPLAY=:12.0 XAUTHORITY=/home/kopiko/.Xauthority /usr/local/bin/die-founder-display12-init
systemctl restart die-principal-browser-broker.service die-muxia-dispatch.service
printf '%s\n' 'FA339_INSTALL=PASS' 'DISPLAY=:12.0' 'WORKSPACES=5' 'HANDOFF=SAFE_DRAIN_NO_CDP'
