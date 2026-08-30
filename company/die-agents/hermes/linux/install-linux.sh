#!/usr/bin/env bash
set -euo pipefail

DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"
HERMES_UPSTREAM="https://github.com/NousResearch/hermes-agent.git"
HERMES_COMMIT="a0ca7c19204e514f9590ce3b812e029b315ab9e9"
INSTALL_ROOT="$DIE_INSTALL_ROOT/hermes"
SOURCE_ROOT="$INSTALL_ROOT/source"
VENV="$INSTALL_ROOT/venv"
HERMES_HOME="$DIE_STATE_ROOT/hermes/income-operator"
WORKSPACES_ROOT="$DIE_STATE_ROOT/workspaces"
ENV_DIR="$DIE_CONFIG_ROOT/hermes"
ENV_FILE="$ENV_DIR/hermes.env"
UNIT_SRC="$DIE_HOME/company/die-agents/hermes/linux/die-hermes-gateway.service"
UNIT_DST="/etc/systemd/system/die-hermes-gateway.service"
SERVICE_USER="die-hermes"
SERVICE_GROUP="die-runtime"

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "E_ROOT_REQUIRED" >&2
  exit 2
fi

for p in "$DIE_HOME/company/die-agents/hermes/SOUL.md" "$DIE_HOME/company/die-agents/hermes/AGENTS.md" "$UNIT_SRC"; do
  [[ -f "$p" ]] || { echo "E_REQUIRED_PATH_MISSING:$p" >&2; exit 2; }
done

getent group "$SERVICE_GROUP" >/dev/null || groupadd --system "$SERVICE_GROUP"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --gid "$SERVICE_GROUP" --home-dir "$DIE_STATE_ROOT/hermes" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
usermod -a -G "$SERVICE_GROUP" kopiko

install -d -m 0755 "$DIE_INSTALL_ROOT" "$INSTALL_ROOT" "$DIE_CONFIG_ROOT" "$ENV_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 2770 "$DIE_STATE_ROOT/hermes" "$HERMES_HOME"
install -d -o root -g "$SERVICE_GROUP" -m 2770 "$WORKSPACES_ROOT"

if [[ ! -d "$SOURCE_ROOT/.git" ]]; then
  rm -rf "$SOURCE_ROOT"
  git init "$SOURCE_ROOT" >/dev/null
  git -C "$SOURCE_ROOT" remote add origin "$HERMES_UPSTREAM"
fi
git -C "$SOURCE_ROOT" fetch --depth 1 origin "$HERMES_COMMIT"
git -C "$SOURCE_ROOT" checkout --detach --force FETCH_HEAD >/dev/null
test "$(git -C "$SOURCE_ROOT" rev-parse HEAD)" = "$HERMES_COMMIT"
test -z "$(git -C "$SOURCE_ROOT" status --porcelain)"

if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  rm -rf "$VENV"
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV/bin/python" -m pip install -e "$SOURCE_ROOT" >/dev/null
"$VENV/bin/python" -m pip install 'python-telegram-bot[webhooks]==22.8' >/dev/null

install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$DIE_HOME/company/die-agents/hermes/SOUL.md" "$HERMES_HOME/SOUL.md"
install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0640 "$DIE_HOME/company/die-agents/hermes/AGENTS.md" "$HERMES_HOME/AGENTS.md"

cat > "$ENV_FILE" <<EOF
HERMES_HOME=$HERMES_HOME
DIE_WORKER_RUNNER=$DIE_HOME/company/workers/opencode/runner.py
DIE_HERMES_WORKER_DISPATCH=$DIE_HOME/company/die-agents/hermes/worker_dispatch.py
DIE_OPENCODE_BIN=$DIE_INSTALL_ROOT/workers/opencode/bin/opencode
DIE_OPENCODE_HOME=$DIE_STATE_ROOT/workers/opencode/home
DIE_WORKSPACES_ROOT=$WORKSPACES_ROOT
EOF
chown root:root "$ENV_FILE"
chmod 0600 "$ENV_FILE"

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl disable die-hermes-gateway.service >/dev/null 2>&1 || true
rm -f "$ENV_DIR/READY"

version="$(runuser -u "$SERVICE_USER" -- env HERMES_HOME="$HERMES_HOME" "$VENV/bin/hermes" --version | head -n 1 | tr -d '\r')"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$HERMES_HOME"
cat > "$INSTALL_ROOT/INSTALL_PROVENANCE" <<EOF
source=$HERMES_UPSTREAM
commit=$HERMES_COMMIT
version=$version
windows_profile_copied=false
windows_auth_copied=false
windows_state_db_copied=false
service_ready_gate=$ENV_DIR/READY
EOF
chmod 0644 "$INSTALL_ROOT/INSTALL_PROVENANCE"

echo "HERMES_INSTALL=PASS"
echo "SOURCE_COMMIT=$HERMES_COMMIT"
echo "HERMES_HOME=$HERMES_HOME"
echo "SERVICE_ENABLED=NO"
echo "SERVICE_STARTED=NO"
echo "READY_GATE=$ENV_DIR/READY"
