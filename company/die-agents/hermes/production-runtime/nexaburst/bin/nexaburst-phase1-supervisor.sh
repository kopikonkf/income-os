#!/usr/bin/env bash
set -euo pipefail
SESSION=/home/kopiko/die-sessions/NEXABURST-H01-P001
ROOT=/var/lib/die/h01/nexaburst
STATE=$ROOT/state
RUNNER=$SESSION/bin/nexaburst-phase1-runner.py
V2=$SESSION/bin/nexaburst-v2-worker.py
NOTIFY=$SESSION/bin/nexaburst-notify.py
PIDFILE=$STATE/phase1-first100.pid
PAUSE=$STATE/phase1-pause.json
DONE=$STATE/phase1-first100-raw-complete.json

# First gate: all 10 Watercolor visual-challenge assets reached Founder QC.
WC_DONE=$(python3 - <<'PY'
import json
from pathlib import Path
p=Path('/var/lib/die/h01/nexaburst/state/v2-done.jsonl');n=0
if p.is_file():
 for l in p.read_text().splitlines():
  try:
   x=json.loads(l)
   if str(x.get('asset_id','')).startswith('NBVC-WC-') and x.get('status')=='WAITING_FOUNDER_QC':n+=1
  except:pass
print(n)
PY
)
if (( WC_DONE < 10 )); then exit 0; fi

# Reload V2 exactly once after the canary drain so Phase-1 uses current lane-lineage code.
if [[ -f "$STATE/v2-reload-after-canary.required" ]]; then
  for PID in $(pgrep -f "$V2 --continuous" 2>/dev/null || true); do kill -TERM "$PID" 2>/dev/null || true; done
  for _ in $(seq 1 20); do pgrep -f "$V2 --continuous" >/dev/null 2>&1 || break; sleep 0.5; done
  rm -f "$STATE/v2-reload-after-canary.required"
fi

# Ensure postprocessor stays alive while phase-1 has work.
if ! pgrep -f "$V2 --continuous" >/dev/null 2>&1; then
  nohup "$V2" --continuous --poll-seconds 5 >>"$STATE/v2-phase1.out" 2>>"$STATE/v2-phase1.err" &
fi

# A completed first-100 raw window is intentionally not re-launched.
[[ -f "$DONE" ]] && exit 0

# If runner is already alive, do nothing.
if [[ -f "$PIDFILE" ]]; then
  PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then exit 0; fi
fi

# Respect retry backoff pause. Other pauses require the preflight below to recover.
if [[ -f "$PAUSE" ]]; then
  read -r CODE RESUME < <(python3 - "$PAUSE" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1]));print(d.get('code',''),d.get('resume_after_epoch') or 0)
except: print('',0)
PY
)
  if [[ "$CODE" == "RETRY_BACKOFF" ]] && (( $(date +%s) < RESUME )); then exit 0; fi
fi

HEALTH=$(node "$SESSION/bin/nexaburst-health.mjs" 2>/dev/null || true)
READY=$(python3 - "$HEALTH" <<'PY'
import json,sys
try:
 d=json.loads(sys.argv[1]);print('yes' if d.get('cdp') and d.get('page') and d.get('authenticated') and d.get('unlimited_active') else 'no')
except: print('no')
PY
)
if [[ "$READY" != "yes" ]]; then
  # runner itself performs deduplicated Founder escalation; launch once to classify/pause.
  :
fi

nohup "$RUNNER" --max-success 100 --max-priority 999 >"$STATE/phase1-first100.out" 2>"$STATE/phase1-first100.err" &
echo $! >"$PIDFILE"
