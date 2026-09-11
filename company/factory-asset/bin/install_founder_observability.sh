#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-$(pwd)}"
SRC="$REPO/company"
[[ -f "$SRC/browser/linux/founder_vnc_view.sh" ]] || { echo E_SOURCE >&2; exit 2; }
command -v x11vnc >/dev/null || { echo E_X11VNC_MISSING >&2; exit 2; }
sudo install -d -o root -g root -m 0755 /opt/die/factory-asset-observability
sudo install -o root -g root -m 0755 "$SRC/browser/linux/founder_vnc_view.sh" /opt/die/factory-asset-observability/founder_vnc_view.sh
sudo install -o root -g root -m 0755 "$SRC/browser/linux/founder_browser_repair.py" /opt/die/factory-asset-observability/founder_browser_repair.py
for unit in die-founder-vnc-cluster-a.service die-founder-vnc-cluster-b.service; do
  sudo install -o root -g root -m 0644 "$SRC/factory-asset/systemd/$unit" "/etc/systemd/system/$unit"
done
sudo systemctl daemon-reload
sudo systemctl enable --now die-founder-vnc-cluster-a.service die-founder-vnc-cluster-b.service
