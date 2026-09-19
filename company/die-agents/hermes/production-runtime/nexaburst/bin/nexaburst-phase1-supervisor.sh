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

# Durable pause semantics. Only objectively recovered conditions auto-clear.
if [[ -f "$PAUSE" ]]; then
  CODE=$(python3 -c "import json; print(json.load(open('$PAUSE')).get('code',''))" 2>/dev/null || echo UNKNOWN)
  RESUME=$(python3 -c "import json; print(json.load(open('$PAUSE')).get('resume_after_epoch') or 0)" 2>/dev/null || echo 0)
  case "$CODE" in
    RETRY_BACKOFF)
      if (( $(date +%s) >= RESUME )); then rm -f "$PAUSE"; else exit 0; fi ;;
    AUTH_REQUIRED|UNLIMITED_INACTIVE|PROVIDER_GATE|BROWSER_UNAVAILABLE)
      H=$(node "$SESSION/bin/nexaburst-health.mjs" 2>/dev/null || true)
      READY=$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("yes" if d.get("cdp") and d.get("page") and d.get("authenticated") and d.get("unlimited_active") else "no")' "$H" 2>/dev/null || echo no)
      if [[ "$READY" == "yes" ]]; then rm -f "$PAUSE"; else exit 0; fi ;;
    STORAGE_GATE)
      FREE=$(df -B1 --output=avail "$ROOT" | tail -1 | tr -d ' ')
      if (( FREE >= 32212254720 )); then rm -f "$PAUSE"; else exit 0; fi ;;
    *)
      # Candidate/config/lineage blocks require Founder resolution.
      exit 0 ;;
  esac
fi

# V2 durable pause blocks raw acquisition; never create an unbounded backlog.
if [[ -f "$STATE/v2-pause.json" ]]; then exit 0; fi

nohup "$RUNNER" --max-success 100 --max-priority 999 >"$STATE/phase1-first100.out" 2>"$STATE/phase1-first100.err" &
echo $! >"$PIDFILE"
