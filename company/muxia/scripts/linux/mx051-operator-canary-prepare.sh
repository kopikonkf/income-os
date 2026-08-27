#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX051_CANARY_PREPARE_REQUIRES_LINUX" >&2
  exit 54
fi
if (( EUID != 0 )); then
  echo "MX051_CANARY_PREPARE_REQUIRES_ROOT" >&2
  exit 55
fi

SOURCE_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OPERATOR_USER="${MUXIA_OPERATOR_USER:-kopiko}"
OPERATOR_HOME="$(getent passwd "$OPERATOR_USER" | cut -d: -f6)"
OPERATOR_GROUP="$(id -gn "$OPERATOR_USER")"

install -d -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0700 "$OPERATOR_HOME/Downloads"
install -o "$OPERATOR_USER" -g "$OPERATOR_GROUP" -m 0755 \
  "$SOURCE_DIR/config/linux/xrdp/MUXIA-MX051-Canaries.desktop" \
  "$OPERATOR_HOME/Desktop/MUXIA-MX051-Canaries.desktop"
chmod 0755 "$SOURCE_DIR/scripts/linux/mx051-operator-canary-open.sh"
echo "MX051_CANARY_PREPARE_PASS:$OPERATOR_USER:$OPERATOR_HOME/Desktop/MUXIA-MX051-Canaries.desktop"
