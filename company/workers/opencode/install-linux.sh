#!/usr/bin/env bash
set -euo pipefail

PKG_VERSION="1.18.23"
INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}/workers/opencode"
STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}/workers/opencode"
WORKSPACES_ROOT="${DIE_STATE_ROOT:-/var/lib/die}/workspaces"
GROUP="die-runtime"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "E_ROOT_REQUIRED" >&2
  exit 2
fi

getent group "$GROUP" >/dev/null || groupadd --system "$GROUP"
install -d -m 0755 "$(dirname "$INSTALL_ROOT")" "$INSTALL_ROOT"
install -d -o kopiko -g "$GROUP" -m 2770 "$STATE_ROOT" "$STATE_ROOT/home"
install -d -o root -g "$GROUP" -m 2770 "$WORKSPACES_ROOT"

npm install --global --prefix "$INSTALL_ROOT" "opencode-ai@$PKG_VERSION"
BIN="$INSTALL_ROOT/bin/opencode"
[[ -x "$BIN" ]] || { echo "E_OPENCODE_BIN_MISSING:$BIN" >&2; exit 2; }

functional_version="$($BIN --version | tail -n 1 | tr -d '\r')"
cat > "$INSTALL_ROOT/INSTALL_PROVENANCE" <<EOF
package=opencode-ai
package_version=$PKG_VERSION
functional_version=$functional_version
install_method=npm-global-prefix
provider_credentials_copied=false
windows_config_copied=false
model_call_performed=false
EOF
chmod 0644 "$INSTALL_ROOT/INSTALL_PROVENANCE"

echo "OPENCODE_INSTALL=PASS"
echo "PACKAGE_VERSION=$PKG_VERSION"
echo "FUNCTIONAL_VERSION=$functional_version"
echo "BIN=$BIN"
echo "MODEL_CALL_PERFORMED=NO"
