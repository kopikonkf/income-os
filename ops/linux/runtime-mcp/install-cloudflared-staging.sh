#!/usr/bin/env bash
set -euo pipefail

STAGING_DIE_HOME="${STAGING_DIE_HOME:-/opt/die/staging/mcp002-source}"
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
SERVICE_USER="die-cloudflared"
SERVICE_GROUP="die-cloudflared"
CONFIG_SRC="$STAGING_DIE_HOME/ops/linux/runtime-mcp/cloudflared-linux-mcp.yml"
UNIT_SRC="$STAGING_DIE_HOME/ops/linux/runtime-mcp/die-runtime-mcp-cloudflared.service"
CONFIG_DIR="$DIE_CONFIG_ROOT/staging/cloudflare"
CONFIG_DST="$CONFIG_DIR/linux-mcp.yml"
TOKEN_FILE="$CONFIG_DIR/linux-mcp.token"
UNIT_DST="/etc/systemd/system/die-runtime-mcp-cloudflared.service"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "E_ROOT_REQUIRED: run with sudo" >&2
  exit 2
fi
for p in "$STAGING_DIE_HOME/.git" "$CONFIG_SRC" "$UNIT_SRC"; do
  [[ -e "$p" ]] || { echo "E_REQUIRED_PATH_MISSING:$p" >&2; exit 2; }
done
[[ -z "$(git -C "$STAGING_DIE_HOME" status --porcelain)" ]] || { echo "E_STAGING_SOURCE_DIRTY" >&2; exit 2; }
command -v cloudflared >/dev/null 2>&1 || { echo "E_CLOUDFLARED_MISSING" >&2; exit 2; }

getent group "$SERVICE_GROUP" >/dev/null || groupadd --system "$SERVICE_GROUP"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --gid "$SERVICE_GROUP" --home-dir /nonexistent --shell /usr/sbin/nologin "$SERVICE_USER"
fi
install -d -o root -g "$SERVICE_GROUP" -m 0750 "$CONFIG_DIR"
[[ -s "$TOKEN_FILE" ]] || { echo "E_TUNNEL_TOKEN_MISSING" >&2; exit 2; }
chown root:root "$TOKEN_FILE"
chmod 0600 "$TOKEN_FILE"

install -o root -g "$SERVICE_GROUP" -m 0640 "$CONFIG_SRC" "$CONFIG_DST"
cloudflared tunnel ingress validate --config "$CONFIG_DST" >/dev/null
# Exact ingress boundary: two MCP staging origins plus terminal deny/default 404.
grep -qx '  - hostname: executive-mcp.aethers.biz.id' "$CONFIG_DST"
grep -qx '    service: http://127.0.0.1:8891' "$CONFIG_DST"
grep -qx '  - hostname: division01-mcp.aethers.biz.id' "$CONFIG_DST"
grep -qx '    service: http://127.0.0.1:8892' "$CONFIG_DST"
grep -qx '  - service: http_status:404' "$CONFIG_DST"
! grep -Eiq '9110|9333|DevTools|browser|wake|aethers\.web\.id|8790|architect' "$CONFIG_DST"

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl disable die-runtime-mcp-cloudflared.service >/dev/null 2>&1 || true
systemctl stop die-runtime-mcp-cloudflared.service >/dev/null 2>&1 || true

echo "MCP_LNX_002_INSTALL=PASS"
echo "SERVICE=die-runtime-mcp-cloudflared.service"
echo "SOURCE_SHA=$(git -C "$STAGING_DIE_HOME" rev-parse HEAD)"
echo "TOKEN_PRESENT=YES"
echo "TOKEN_VALUE_RETURNED=NO"
echo "SERVICE_ENABLED=NO"
echo "SERVICE_STARTED=NO"
