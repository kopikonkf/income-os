#!/usr/bin/env bash
set -euo pipefail

DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"
SERVICE_USER="die-division01"
SERVICE_GROUP="die-runtime"
UNIT_SRC="$DIE_HOME/company/division/division001/linux/die-division01-runtime-mcp.service"
UNIT_DST="/etc/systemd/system/die-division01-runtime-mcp.service"
ENV_DIR="$DIE_CONFIG_ROOT/division01"
ENV_FILE="$ENV_DIR/runtime-mcp.env"
DIV_STATE_DIR="$DIE_STATE_ROOT/division01"
STATE_DIR="$DIE_STATE_ROOT/state"
BROWSER_PROFILE="$DIV_STATE_DIR/browser-profile"
INSTALL_DIR="$DIE_INSTALL_ROOT/division01"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "E_ROOT_REQUIRED: run with sudo" >&2
  exit 2
fi

for p in "$DIE_HOME" "$UNIT_SRC" "$DIE_HOME/company/identity-registry.json"; do
  [[ -e "$p" ]] || { echo "E_REQUIRED_PATH_MISSING: $p" >&2; exit 2; }
done

getent group "$SERVICE_GROUP" >/dev/null || groupadd --system "$SERVICE_GROUP"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --gid "$SERVICE_GROUP" --home-dir /nonexistent --shell /usr/sbin/nologin "$SERVICE_USER"
fi
usermod -a -G "$SERVICE_GROUP" kopiko

install -d -m 0755 "$DIE_CONFIG_ROOT" "$ENV_DIR" "$DIE_INSTALL_ROOT" "$INSTALL_DIR"
if [[ ! -d "$STATE_DIR" ]]; then
  install -d -o root -g "$SERVICE_GROUP" -m 2770 "$STATE_DIR"
fi
install -d -o kopiko -g "$SERVICE_GROUP" -m 0750 "$DIV_STATE_DIR" "$BROWSER_PROFILE"

# Shared preliminary state bootstrap may already exist from DIE-200.
# Never overwrite it here; CUT-002/CUT-003 own final state sync/replay.
if [[ -z "$(find "$STATE_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  cp -a "$DIE_HOME/state/." "$STATE_DIR/"
  chown -R root:"$SERVICE_GROUP" "$STATE_DIR"
  chmod -R u+rwX,g+rwX,o-rwx "$STATE_DIR"
  git -C "$DIE_HOME" rev-parse HEAD > "$DIV_STATE_DIR/bootstrap-source-sha"
  chown kopiko:"$SERVICE_GROUP" "$DIV_STATE_DIR/bootstrap-source-sha"
  chmod 0640 "$DIV_STATE_DIR/bootstrap-source-sha"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  login="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  umask 077
  cat > "$ENV_FILE" <<EOF
DIE_MCP_TOKEN=$token
DIE_MCP_LOGIN_PASSWORD=$login
DIE_MCP_BASE_URL=https://division01-linux-precutover.invalid
DIE_MCP_OAUTH_CLIENT_ID=chatgpt-division01-linux-precutover
DIE_MCP_OAUTH_REDIRECT_HOSTS="chatgpt.com;openai.com"
EOF
  unset token login
fi
chown root:root "$ENV_FILE"
chmod 0600 "$ENV_FILE"

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
cat > "$INSTALL_DIR/README" <<EOF
DIE Division01 Linux runtime install marker.
Canonical source: $DIE_HOME/company/division/division001
Mutable state: $DIE_STATE_ROOT
Protected config: $ENV_FILE
Browser profile: $BROWSER_PROFILE
D:\\OAUTH is not Division01 and is not imported by this installer.
Public Windows endpoint is NOT cut over by DIE-201.
EOF
chmod 0644 "$INSTALL_DIR/README"

systemctl daemon-reload
systemctl enable die-division01-runtime-mcp.service >/dev/null

echo "DIE201_INSTALL_READY"
echo "SERVICE=die-division01-runtime-mcp.service"
echo "BROWSER_PROFILE=$BROWSER_PROFILE"
echo "OAUTH_IMPORTED=NO"
echo "PUBLIC_CUTOVER=NOT_PERFORMED"
