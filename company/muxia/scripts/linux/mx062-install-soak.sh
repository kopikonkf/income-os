#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX062_REQUIRES_LINUX" >&2
  exit 20
fi
if (( EUID != 0 )); then
  echo "MX062_INSTALL_REQUIRES_ROOT" >&2
  exit 21
fi
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <runtime-user>" >&2
  exit 22
fi

RUNTIME_USER="$1"
id "$RUNTIME_USER" >/dev/null 2>&1 || { echo "MX062_RUNTIME_USER_NOT_FOUND" >&2; exit 23; }
SOURCE_DIR="${MUXIA_SOURCE_DIR:-/srv/die/company/muxia}"
UNIT_SOURCE="$SOURCE_DIR/config/linux/systemd/muxia-mx062-soak@.service"
UNIT_TARGET="/etc/systemd/system/muxia-mx062-soak@.service"
SOAK_ROOT="/var/lib/muxia-soak"

command -v node >/dev/null 2>&1 || { echo "NODE_REQUIRED" >&2; exit 24; }
NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
if (( NODE_MAJOR != 24 )); then
  echo "NODE_24_LTS_REQUIRED:found=${NODE_MAJOR}" >&2
  exit 25
fi

test -f "$UNIT_SOURCE"
test -f "$SOURCE_DIR/scripts/mx062-soak.mjs"
test -f "$SOURCE_DIR/dist/core/soak-runner.js"

install -d -o "$RUNTIME_USER" -g "$RUNTIME_USER" -m 0750 "$SOAK_ROOT"
install -o root -g root -m 0644 "$UNIT_SOURCE" "$UNIT_TARGET"
systemctl daemon-reload

echo "MX062_SOAK_INSTALL_PASS:unit=muxia-mx062-soak@${RUNTIME_USER}.service"
echo "MX062_NOT_STARTED:explicit_start_required"
