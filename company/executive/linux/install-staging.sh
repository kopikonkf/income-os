#!/usr/bin/env bash
set -euo pipefail

STAGING_DIE_HOME="${STAGING_DIE_HOME:-/opt/die/staging/income-os}"
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
SERVICE_USER="die-executive"
SERVICE_GROUP="die-runtime"
UNIT_SRC="$STAGING_DIE_HOME/company/executive/linux/die-executive-runtime-mcp-staging.service"
UNIT_DST="/etc/systemd/system/die-executive-runtime-mcp-staging.service"
ENV_DIR="$DIE_CONFIG_ROOT/staging/executive"
ENV_FILE="$ENV_DIR/runtime-mcp.env"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "E_ROOT_REQUIRED: run with sudo" >&2
  exit 2
fi

for p in "$STAGING_DIE_HOME/.git" "$UNIT_SRC" "$STAGING_DIE_HOME/company/identity-registry.json"; do
  [[ -e "$p" ]] || { echo "E_REQUIRED_PATH_MISSING:$p" >&2; exit 2; }
done
[[ -z "$(git -C "$STAGING_DIE_HOME" status --porcelain)" ]] || { echo "E_STAGING_SOURCE_DIRTY" >&2; exit 2; }
id -u "$SERVICE_USER" >/dev/null 2>&1 || { echo "E_SERVICE_USER_MISSING:$SERVICE_USER" >&2; exit 2; }
getent group "$SERVICE_GROUP" >/dev/null || { echo "E_SERVICE_GROUP_MISSING:$SERVICE_GROUP" >&2; exit 2; }

install -d -m 0755 "$DIE_CONFIG_ROOT/staging"
install -d -o root -g root -m 0700 "$ENV_DIR"
if [[ ! -f "$ENV_FILE" ]]; then
  token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  login="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  umask 077
  cat > "$ENV_FILE" <<EOF
DIE_MCP_TOKEN=$token
DIE_MCP_LOGIN_PASSWORD=$login
DIE_MCP_BASE_URL=https://executive-mcp.aethers.biz.id
DIE_MCP_OAUTH_CLIENT_ID=chatgpt-die-lnx-executive-001
DIE_MCP_OAUTH_REDIRECT_HOSTS="chatgpt.com;openai.com"
DIE_MCP_CONTROL_POLICY=staging-read-only
EOF
  unset token login
fi
chown root:root "$ENV_FILE"
chmod 0600 "$ENV_FILE"

# Refuse a stale or accidentally production-bound staging config without reading secrets.
grep -qx 'DIE_MCP_BASE_URL=https://executive-mcp.aethers.biz.id' "$ENV_FILE" || { echo "E_STAGING_BASE_URL_MISMATCH" >&2; exit 2; }
grep -qx 'DIE_MCP_CONTROL_POLICY=staging-read-only' "$ENV_FILE" || { echo "E_STAGING_CONTROL_POLICY" >&2; exit 2; }

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl disable "die-executive-runtime-mcp-staging.service" >/dev/null 2>&1 || true
systemctl stop "die-executive-runtime-mcp-staging.service" >/dev/null 2>&1 || true

echo "MCP_LNX_STAGING_INSTALL=PASS"
echo "SERVICE=die-executive-runtime-mcp-staging.service"
echo "SOURCE_SHA=$(git -C "$STAGING_DIE_HOME" rev-parse HEAD)"
echo "CONTROL_POLICY=staging-read-only"
echo "SERVICE_ENABLED=NO"
echo "SERVICE_STARTED=NO"
echo "SECRET_VALUES_RETURNED=NO"
