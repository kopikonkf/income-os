#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo E_FA121_INSTALL_REQUIRES_ROOT >&2
  exit 2
fi
RUNTIME_ROOT="${FA121_RUNTIME_ROOT:-/opt/factory-asset/fa121-runtime}"
STATE_ROOT="${FA121_STATE_ROOT:-/var/lib/factory-asset/fa121-stability}"
SRC="$RUNTIME_ROOT/company/factory-asset/systemd"
BIN="$RUNTIME_ROOT/company/factory-asset/bin"
[[ -f "$SRC/die-fa121-cluster-broker.service" ]] || { echo E_FA121_UNIT_SOURCE >&2; exit 2; }
[[ -f "$SRC/die-muxia-cluster-a-browser.service" ]] || { echo E_FA121_BROWSER_UNIT_SOURCE >&2; exit 2; }
[[ -f "$BIN/fa121-systemd-tick.sh" ]] || { echo E_FA121_TICK_WRAPPER >&2; exit 2; }
id kopiko >/dev/null 2>&1 || { echo E_FA121_RUNTIME_USER >&2; exit 2; }
install -d -o kopiko -g kopiko -m 0750 "$STATE_ROOT" "$STATE_ROOT/broker" "$STATE_ROOT/attempts" "$STATE_ROOT/artifacts" "$STATE_ROOT/status-history"
install -m 0755 "$BIN/fa121-systemd-tick.sh" /usr/local/sbin/die-fa121-stability-tick
install -m 0644 "$SRC/die-muxia-cluster-a-browser.service" /etc/systemd/system/die-muxia-cluster-a-browser.service
install -m 0644 "$SRC/die-fa121-cluster-broker.service" /etc/systemd/system/die-fa121-cluster-broker.service
install -m 0644 "$SRC/die-fa121-stability-tick.service" /etc/systemd/system/die-fa121-stability-tick.service
install -m 0644 "$SRC/die-fa121-stability.timer" /etc/systemd/system/die-fa121-stability.timer
systemctl daemon-reload
systemctl disable --now die-fa121-stability.timer >/dev/null 2>&1 || true
systemctl stop die-fa121-cluster-broker.service >/dev/null 2>&1 || true
systemctl enable die-muxia-cluster-a-browser.service die-fa121-cluster-broker.service >/dev/null 2>&1 || true
echo FA121_SYSTEMD_INSTALLED
