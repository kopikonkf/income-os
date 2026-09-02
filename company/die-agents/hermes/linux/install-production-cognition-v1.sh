#!/usr/bin/env bash
set -euo pipefail
DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
HERMES_HOME="${HERMES_HOME:-$DIE_STATE_ROOT/hermes/income-operator}"
HERMES_BIN="${HERMES_BIN:-/opt/die/hermes/venv/bin/hermes}"
JOB_NAME="die-production-cognition-v1"
SCHEDULE='*/1 * * * *'
SCRIPT_REL='production-cognition/production_cognition_tick.sh'
SOURCE="$DIE_HOME/company/die-agents/hermes/production-cognition"
DEST="$HERMES_HOME/scripts/production-cognition"
WORKDIR="$DIE_HOME/company/die-agents/hermes"
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo E_ROOT_REQUIRED >&2; exit 2; }
[[ -x "$HERMES_BIN" ]] || { echo E_HERMES_BIN >&2; exit 2; }
[[ -f "$SOURCE/production_cognition_tick.py" ]] || { echo E_COGNITION_SOURCE >&2; exit 2; }
[[ -f "$DIE_HOME/company/browser/linux/cognition_roundtrip.mjs" ]] || { echo E_COGNITION_TRANSPORT >&2; exit 2; }
install -d -o die-hermes -g die-runtime -m 2770 "$DEST" "$DIE_STATE_ROOT/state/production-cognition"
install -d -o die-hermes -g die-runtime -m 2770 "$DIE_STATE_ROOT/division01/cognition-receipts" "$DIE_STATE_ROOT/executive/cognition-receipts"
for f in production_cognition_tick.py validate_production_cognition.py die.production.family-blueprint.v1.schema.json die.production.family-blueprint-review.v1.schema.json die.production.cognition-receipt.v1.schema.json; do
  install -o die-hermes -g die-runtime -m 0640 "$SOURCE/$f" "$DEST/$f"
done
chmod 0750 "$DEST/production_cognition_tick.py" "$DEST/validate_production_cognition.py"
cat > "$DEST/production_cognition_tick.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 "$DIE_HOME/company/die-agents/hermes/production-cognition/production_cognition_tick.py" "\$@"
EOF
chown die-hermes:die-runtime "$DEST/production_cognition_tick.sh"
chmod 0750 "$DEST/production_cognition_tick.sh"
/usr/bin/python3 - <<'PYDEP'
import jsonschema
print('PRODUCTION_COGNITION_PYTHON_DEPENDENCY=PASS')
PYDEP
JOB_ID=$(runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" python3 - <<'PY'
import json,os
p=os.path.join(os.environ['HERMES_HOME'],'cron','jobs.json')
try:d=json.load(open(p))
except FileNotFoundError:raise SystemExit(0)
items=d.get('jobs',[]) if isinstance(d,dict) else d
if isinstance(items,dict):items=list(items.values())
for j in items:
 if isinstance(j,dict) and j.get('name')=='die-production-cognition-v1': print(j.get('id',''));break
PY
)
if [[ -n "$JOB_ID" ]]; then
  runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" cron edit "$JOB_ID" --schedule "$SCHEDULE" --script "$SCRIPT_REL" --no-agent --deliver telegram --workdir "$WORKDIR" --no-continuity
  ACTION=UPDATED
else
  runuser -u die-hermes -- env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" cron create "$SCHEDULE" --name "$JOB_NAME" --script "$SCRIPT_REL" --no-agent --deliver telegram --workdir "$WORKDIR"
  ACTION=CREATED
fi
echo PRODUCTION_COGNITION_INSTALL=PASS
echo JOB_NAME="$JOB_NAME"
echo ACTION="$ACTION"
echo MODE=DETERMINISTIC_NO_AGENT
echo SCHEDULE="$SCHEDULE"
echo SCRIPT="$SCRIPT_REL"
