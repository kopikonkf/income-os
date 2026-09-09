#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:-/srv/die}
SRC="$ROOT/company/factory-asset/systemd/die-muxia-cluster-b.service"
BROWSER_SRC="$ROOT/company/factory-asset/systemd/die-muxia-cluster-b-browser.service"
test -f "$SRC" || { echo E_CLUSTER_B_UNIT_SOURCE >&2; exit 2; }
test -f "$BROWSER_SRC" || { echo E_CLUSTER_B_BROWSER_UNIT_SOURCE >&2; exit 2; }
install -m 0644 "$BROWSER_SRC" /etc/systemd/system/die-muxia-cluster-b-browser.service
install -m 0644 "$SRC" /etc/systemd/system/die-muxia-cluster-b.service
systemctl daemon-reload
systemctl enable die-muxia-cluster-b-browser.service die-muxia-cluster-b.service
if [[ ${START_NOW:-no} == yes ]]; then systemctl restart die-muxia-cluster-b-browser.service die-muxia-cluster-b.service; fi
