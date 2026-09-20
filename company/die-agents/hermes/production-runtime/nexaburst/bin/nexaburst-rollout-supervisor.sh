#!/usr/bin/env bash
set -euo pipefail
SESSION=/home/kopiko/die-sessions/NEXABURST-H01-P001
ROOT=/var/lib/die/h01/nexaburst
STATE=$ROOT/state
RUNNER=$SESSION/bin/nexaburst-rollout-runner.py
CONTROL=$STATE/operator-control.json
FIRST100=$STATE/FIRST100_COMPLETE.json
ARM=$STATE/FULL_ROLLOUT_ARMED.json
PAUSE=$STATE/full-rollout-pause.json
PIDFILE=$STATE/full-rollout.pid
BACKLOG_RESUME=500
MIN_FREE_GIB=100

[[ -f "$FIRST100" ]] || exit 0
[[ -f "$ARM" ]] || exit 0

MODE=$(python3 - "$CONTROL" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get('mode','PAUSED'))
except Exception: print('PAUSED')
PY
)
[[ "$MODE" == "RUNNING" ]] || exit 0

if [[ -f "$PIDFILE" ]]; then
  PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then exit 0; fi
fi

if [[ -f "$PAUSE" ]]; then
  CODE=$(python3 - "$PAUSE" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get('code','UNKNOWN'))
except Exception: print('UNKNOWN')
PY
)
  case "$CODE" in
    V2_BACKLOG_GATE)
      BACKLOG=$(python3 - <<'PY'
import sqlite3
c=sqlite3.connect('/var/lib/die/h01/nexaburst/state/nexaburst-manifestation-ledger.db')
print(c.execute("select count(*) from manifestations where lane_id='WC-L0' and status='RAW_DONE'").fetchone()[0])
c.close()
PY
)
      FREE_GIB=$(python3 - <<'PY'
import os
s=os.statvfs('/var/lib/die/h01/nexaburst')
print(int(s.f_bavail*s.f_frsize/1024**3))
PY
)
      if (( BACKLOG <= BACKLOG_RESUME && FREE_GIB >= MIN_FREE_GIB )); then
        rm -f "$PAUSE"
      else
        exit 0
      fi
      ;;
    *)
      # Provider, 429, checkpoint, lineage and plan conflicts never auto-clear.
      exit 0
      ;;
  esac
fi

nohup "$RUNNER" >>"$STATE/full-rollout.out" 2>>"$STATE/full-rollout.err" &
echo $! >"$PIDFILE"
