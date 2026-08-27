#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX050_GUI_REQUIRES_LINUX" >&2
  exit 30
fi
if (( EUID != 0 )); then
  echo "MX050_GUI_PROVISION_REQUIRES_ROOT" >&2
  exit 31
fi

SOURCE_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OPERATOR_USER="${MUXIA_OPERATOR_USER:-kopiko}"
XRDP_CONFIG=/etc/xrdp/xrdp.ini
XRDP_BACKUP=/etc/xrdp/xrdp.ini.pre-muxia-20260827

getent passwd "$OPERATOR_USER" >/dev/null
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends xfce4 xfce4-terminal xrdp xorgxrdp dbus-x11 policykit-1-gnome

if [[ ! -e "$XRDP_BACKUP" ]]; then
  install -o root -g root -m 0600 "$XRDP_CONFIG" "$XRDP_BACKUP"
fi
if grep -q '^port=3389$' "$XRDP_CONFIG"; then
  sed -i '0,/^port=3389$/s|^port=3389$|port=tcp://.:3389|' "$XRDP_CONFIG"
fi
grep -q '^port=tcp://\.:3389$' "$XRDP_CONFIG" || {
  echo "XRDP_LOOPBACK_CONFIG_FAILED" >&2
  exit 32
}

adduser xrdp ssl-cert >/dev/null
OPERATOR_HOME="$(getent passwd "$OPERATOR_USER" | cut -d: -f6)"
OPERATOR_GROUP="$(id -gn "$OPERATOR_USER")"
install -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0755 "$SOURCE_DIR/config/linux/xrdp/xsession" "$OPERATOR_HOME/.xsession"
install -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0644 "$SOURCE_DIR/config/linux/xrdp/xsessionrc" "$OPERATOR_HOME/.xsessionrc"

systemctl enable xrdp xrdp-sesman >/dev/null
systemctl restart xrdp-sesman xrdp
systemctl is-active --quiet xrdp
systemctl is-active --quiet xrdp-sesman
LISTENERS="$(ss -H -lnt '( sport = :3389 )' | awk '{print $4}')"
printf '%s\n' "$LISTENERS" | grep -Fxq '127.0.0.1:3389'
if printf '%s\n' "$LISTENERS" | grep -Fvxq '127.0.0.1:3389'; then
  echo "XRDP_PUBLIC_BIND_REJECTED:$LISTENERS" >&2
  exit 33
fi

echo "MX050_GUI_PROVISION_PASS:127.0.0.1:3389:$OPERATOR_USER"
