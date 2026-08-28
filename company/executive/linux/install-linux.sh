#!/usr/bin/env bash
set -euo pipefail

DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"
SERVICE_USER="die-executive"
SERVICE_GROUP="die-runtime"
UNIT_SRC="$DIE_HOME/company/executive/linux/die-executive-runtime-mcp.service"
UNIT_DST="/etc/systemd/system/die-executive-runtime-mcp.service"
ENV_DIR="$DIE_CONFIG_ROOT/executive"
ENV_FILE="$ENV_DIR/runtime-mcp.env"
EXEC_STATE_DIR="$DIE_STATE_ROOT/executive"
STATE_DIR="$DIE_STATE_ROOT/state"
BROWSER_PROFILE="$EXEC_STATE_DIR/browser-profile"
INSTALL_DIR="$DIE_INSTALL_ROOT/executive"

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
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 2770 "$DIE_STATE_ROOT" "$STATE_DIR"
install -d -o kopiko -g "$SERVICE_GROUP" -m 0750 "$EXEC_STATE_DIR" "$BROWSER_PROFILE"

# Bootstrap only from clean Git-tracked source state. This is not CUT-002 final sync.
if [[ -z "$(find "$STATE_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  cp -a "$DIE_HOME/state/." "$STATE_DIR/"
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$STATE_DIR"
  chmod -R u+rwX,g+rwX,o-rwx "$STATE_DIR"
  git -C "$DIE_HOME" rev-parse HEAD > "$EXEC_STATE_DIR/bootstrap-source-sha"
  chown kopiko:"$SERVICE_GROUP" "$EXEC_STATE_DIR/bootstrap-source-sha"
  chmod 0640 "$EXEC_STATE_DIR/bootstrap-source-sha"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  login="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  umask 077
  cat > "$ENV_FILE" <<EOF
DIE_MCP_TOKEN=$token
DIE_MCP_LOGIN_PASSWORD=$login
DIE_MCP_BASE_URL=https://executive-linux-precutover.invalid
DIE_MCP_OAUTH_CLIENT_ID=chatgpt-executive-linux-precutover
DIE_MCP_OAUTH_REDIRECT_HOSTS="chatgpt.com;openai.com"
EOF
  unset token login
fi
chown root:root "$ENV_FILE"
chmod 0600 "$ENV_FILE"

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
cat > "$INSTALL_DIR/README" <<EOF
DIE Executive Linux runtime install marker.
Canonical source: $DIE_HOME/company/executive
Mutable state: $DIE_STATE_ROOT
Protected config: $ENV_FILE
Browser profile: $BROWSER_PROFILE
Public Windows endpoint is NOT cut over by DIE-200.
EOF
chmod 0644 "$INSTALL_DIR/README"

systemctl daemon-reload
systemctl enable die-executive-runtime-mcp.service >/dev/null

echo "DIE200_INSTALL_READY"
echo "SERVICE=die-executive-runtime-mcp.service"
echo "STATE_BOOTSTRAP=$STATE_DIR"
echo "BROWSER_PROFILE=$BROWSER_PROFILE"
echo "PUBLIC_CUTOVER=NOT_PERFORMED"
