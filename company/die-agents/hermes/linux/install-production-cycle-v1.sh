#!/usr/bin/env bash
set -euo pipefail
DIE_HOME="${DIE_HOME:-/srv/die}"; DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"; DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"; MUXIA_ROOT="${MUXIA_ROOT:-/var/lib/muxia}"
HERMES_HOME="${HERMES_HOME:-$DIE_STATE_ROOT/hermes/income-operator}"; HERMES_BIN="${HERMES_BIN:-$DIE_INSTALL_ROOT/hermes/venv/bin/hermes}"
JOB_NAME="die-production-cycle-v1"; SCHEDULE='0 */3 * * *'; SCRIPT_REL='production-runtime/production_runtime_tick.sh'; WORKDIR="$DIE_HOME/company/die-agents/hermes"
SRC="$DIE_HOME/company/die-agents/hermes/production-runtime"; DEST="$HERMES_HOME/scripts/production-runtime"
MUXIA_DISPATCH_SRC="$DIE_HOME/company/muxia/scripts/linux/die-muxia-image-dispatch.py"; MUXIA_DISPATCH_DST="$DIE_INSTALL_ROOT/bin/die-muxia-image-dispatch"
MUXIA_WORKER_SRC="$DIE_HOME/company/muxia/scripts/linux/die-muxia-dispatch-worker.py"; MUXIA_WORKER_DST="$DIE_INSTALL_ROOT/bin/die-muxia-dispatch-worker"
MUXIA_UNIT_SRC="$DIE_HOME/company/muxia/scripts/linux/die-muxia-dispatch.service"; MUXIA_UNIT_DST="/etc/systemd/system/die-muxia-dispatch.service"
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo E_ROOT_REQUIRED >&2; exit 2; }
[[ -x "$HERMES_BIN" && -f "$SRC/production_runtime_tick.py" && -f "$SRC/production_runtime_tick.sh" && -f "$SRC/factory_orchestration_v2.py" && -f "$DIE_HOME/company/muxia/scripts/linux/muxia-chatgpt-image.mjs" && -f "$MUXIA_DISPATCH_SRC" && -f "$MUXIA_WORKER_SRC" && -f "$MUXIA_UNIT_SRC" ]] || { echo E_RUNTIME_SOURCE >&2; exit 2; }
install -d -o die-hermes -g die-runtime -m 2770 "$DEST" "$DIE_STATE_ROOT/state/production-runtime"
install -o die-hermes -g die-runtime -m 0750 "$SRC/production_runtime_tick.py" "$DEST/production_runtime_tick.py"
install -o die-hermes -g die-runtime -m 0750 "$SRC/production_runtime_tick.sh" "$DEST/production_runtime_tick.sh"
install -o die-hermes -g die-runtime -m 0640 "$SRC/factory_orchestration_v2.py" "$DEST/factory_orchestration_v2.py"
/usr/bin/python3 "$DIE_HOME/company/factory-asset/bin/prepare_runtime_venv.py" --venv "$DIE_INSTALL_ROOT/factory-asset/venv" --requirements "$DIE_HOME/company/factory-asset/requirements-runtime.txt"
install -d -o root -g root -m 0755 "$DIE_INSTALL_ROOT/bin"
install -o root -g root -m 0755 "$MUXIA_DISPATCH_SRC" "$MUXIA_DISPATCH_DST"
install -o root -g root -m 0755 "$MUXIA_WORKER_SRC" "$MUXIA_WORKER_DST"
install -d -o die-hermes -g die-runtime -m 2770 "$DIE_STATE_ROOT/state/muxia-dispatch" "$DIE_STATE_ROOT/state/muxia-dispatch/requests" "$DIE_STATE_ROOT/state/muxia-dispatch/results"
install -o root -g root -m 0644 "$MUXIA_UNIT_SRC" "$MUXIA_UNIT_DST"
install -d -o kopiko -g die-runtime -m 0700 "$MUXIA_ROOT/service-home"
rm -f /etc/sudoers.d/die-hermes-muxia-image
systemctl daemon-reload
systemctl enable die-muxia-dispatch.service
systemctl restart die-muxia-dispatch.service
JOB_ID=$(runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" python3 - <<'PY'
import json,os
p=os.path.join(os.environ['HERMES_HOME'],'cron','jobs.json');d=json.load(open(p));items=d.get('jobs',[]) if isinstance(d,dict) else d
if isinstance(items,dict):items=list(items.values())
for j in items:
 if isinstance(j,dict) and j.get('name')=='die-production-cycle-v1':print(j.get('id',''));break
PY
)
if [[ -n "$JOB_ID" ]]; then
 runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" cron edit "$JOB_ID" --schedule "$SCHEDULE" --script "$SCRIPT_REL" --no-agent --deliver telegram --workdir "$WORKDIR" --no-continuity
 ACTION=UPDATED
else
 runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" cron create "$SCHEDULE" --name "$JOB_NAME" --script "$SCRIPT_REL" --no-agent --deliver telegram --workdir "$WORKDIR"
 ACTION=CREATED
fi
echo PRODUCTION_RUNTIME_INSTALL=PASS; echo JOB_ID="$JOB_ID"; echo ACTION="$ACTION"; echo MODE=DETERMINISTIC_NO_AGENT; echo SCHEDULE="$SCHEDULE"; echo SCRIPT="$SCRIPT_REL"
