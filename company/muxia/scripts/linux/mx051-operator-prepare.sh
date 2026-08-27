#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX051_PREPARE_REQUIRES_LINUX" >&2
  exit 44
fi
if (( EUID != 0 )); then
  echo "MX051_PREPARE_REQUIRES_ROOT" >&2
  exit 45
fi

SOURCE_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OPERATOR_USER="${MUXIA_OPERATOR_USER:-kopiko}"
OPERATOR_HOME="$(getent passwd "$OPERATOR_USER" | cut -d: -f6)"
OPERATOR_GROUP="$(id -gn "$OPERATOR_USER")"
PROFILE_DIR=/var/lib/muxia/profiles/chatgpt-linux-a/browser

install -d -o "$OPERATOR_USER" -g muxia -m 0700 "$PROFILE_DIR"
install -d -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0755 "$OPERATOR_HOME/Desktop"
install -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0755   "$SOURCE_DIR/config/linux/xrdp/MUXIA-ChatGPT-Login.desktop"   "$OPERATOR_HOME/Desktop/MUXIA-ChatGPT-Login.desktop"
chmod 0755 "$SOURCE_DIR/scripts/linux/mx051-operator-open.sh"

passwd -S "$OPERATOR_USER" | grep -q "^$OPERATOR_USER P "
echo "MX051_OPERATOR_PREPARE_PASS:$OPERATOR_USER:$PROFILE_DIR"
