#!/usr/bin/env bash
set -euo pipefail
DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"
HERMES_HOME="${HERMES_HOME:-$DIE_STATE_ROOT/hermes/income-operator}"
HERMES_BIN="${HERMES_BIN:-$DIE_INSTALL_ROOT/hermes/venv/bin/hermes}"
SOURCE_ROOT="${DIE_OPERATOR_V2_SOURCE_ROOT:-/opt/die/staging/income-os}"
JOB_NAME="die-proactive-operator-v1"
SCRIPT_NAME="die_operator_v2_tick.py"
WORKDIR="$DIE_HOME/company/die-agents/hermes"

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo E_ROOT_REQUIRED >&2; exit 2; }
[[ -x "$HERMES_BIN" ]] || { echo E_HERMES_BIN >&2; exit 2; }
[[ -f "$SOURCE_ROOT/company/die-agents/hermes/operator-v2/linux_scheduler_tick.py" ]] || { echo E_OPERATOR_V2_SOURCE >&2; exit 2; }
install -d -o die-hermes -g die-runtime -m 2770 "$HERMES_HOME/scripts" "$DIE_STATE_ROOT/state/operator-v2/receipt-inbox" "$DIE_STATE_ROOT/state/operator-v2/outbox"
cat > "$HERMES_HOME/scripts/$SCRIPT_NAME" <<'PY'
#!/usr/bin/env python3
import os
import runpy
from pathlib import Path
root = Path(os.environ.get("DIE_OPERATOR_V2_SOURCE_ROOT", "/opt/die/staging/income-os")).resolve()
target = root / "company" / "die-agents" / "hermes" / "operator-v2" / "linux_scheduler_tick.py"
if not target.is_file():
    raise SystemExit(f"E_OPERATOR_V2_SOURCE:{target}")
runpy.run_path(str(target), run_name="__main__")
PY
chown die-hermes:die-runtime "$HERMES_HOME/scripts/$SCRIPT_NAME"
chmod 0750 "$HERMES_HOME/scripts/$SCRIPT_NAME"
if runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" DIE_HOME="$SOURCE_ROOT" DIE_STATE_ROOT="$DIE_STATE_ROOT" DIE_COMPANY_INSTANCE=DIE-LINUX DIE_OPERATOR_V2_SOURCE_ROOT="$SOURCE_ROOT" TERMINAL_CWD="$WORKDIR" "$HERMES_BIN" cron list --all | grep -Fq "$JOB_NAME"; then
  echo E_OPERATOR_CRON_ALREADY_EXISTS >&2
  exit 3
fi
runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" DIE_HOME="$SOURCE_ROOT" DIE_STATE_ROOT="$DIE_STATE_ROOT" DIE_COMPANY_INSTANCE=DIE-LINUX DIE_OPERATOR_V2_SOURCE_ROOT="$SOURCE_ROOT" TERMINAL_CWD="$WORKDIR" "$HERMES_BIN" cron create '*/30 * * * *' --name "$JOB_NAME" --script "$SCRIPT_NAME" --no-agent --workdir "$WORKDIR"
echo OPERATOR_V2_CRON_INSTALL=PASS
echo JOB_NAME="$JOB_NAME"
echo MODE=DETERMINISTIC_NO_AGENT
echo COMPANY_INSTANCE=DIE-LINUX
echo SCHEDULE='*/30 * * * *'
