#!/usr/bin/env bash
set -euo pipefail
ENV=/home/kopiko/.config/die/nexaburst.env
BROWSER=/home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-browser.sh
NOTIFY=/home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-notify.py
STATE=/var/lib/die/h01/nexaburst/state
SESSION=$STATE/nexaburst-p001-browser-session.json
INFLIGHT=$STATE/nexaburst-p001.inflight.lock
UDD=/var/lib/die/h01/nexaburst/profiles/nexaburst-p001/udd
CONTROL=$STATE/operator-control.json
FAILSTATE=$STATE/browser-start-failure.json
PORT=9311
MODE=${1:-ensure}
[[ -f "$ENV" ]] && set -a && . "$ENV" && set +a
MAX_AGE=${NEXABURST_BROWSER_MAX_AGE_SECONDS:-3600}

cdp_up(){ curl -fsS --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; }
control_mode(){
  python3 - "$CONTROL" <<'EOF'
import json,sys
try: print(json.load(open(sys.argv[1])).get('mode','PAUSED'))
except Exception: print('PAUSED')
EOF
}
udd_owner_alive(){ pgrep -af -- "--user-data-dir=$UDD" >/dev/null 2>&1; }
fail_age(){
  python3 - "$FAILSTATE" <<'EOF'
import json,time,sys
try: print(max(0,int(time.time())-int(json.load(open(sys.argv[1])).get('failed_epoch',0))))
except Exception: print(999999)
EOF
}
record_failure(){
  python3 - "$FAILSTATE" <<'EOF'
import json,os,time,sys
p=sys.argv[1]; old={}
try: old=json.load(open(p))
except Exception: pass
obj={'failed_epoch':int(time.time()),'count':int(old.get('count',0))+1}
t=p+'.tmp'; open(t,'w').write(json.dumps(obj)+'\n'); os.replace(t,p)
print(obj['count'])
EOF
}

inflight_alive(){
  [[ -f "$INFLIGHT" ]] || return 1
  python3 - "$INFLIGHT" <<'PY'
import json,os,sys
try:
 d=json.load(open(sys.argv[1])); p=int(d.get('pid',0)); os.kill(p,0)
except Exception: raise SystemExit(1)
raise SystemExit(0)
PY
}
age_seconds(){
  python3 - "$SESSION" <<'PY'
import json,time,sys
try:d=json.load(open(sys.argv[1])); print(max(0,int(time.time())-int(d.get('started_epoch',0))))
except Exception: print(999999999)
PY
}
stop_browser(){
  python3 - "$UDD" <<'PY'
import os,signal,sys
udd=sys.argv[1].encode(); pids=[]
for name in os.listdir('/proc'):
    if not name.isdigit(): continue
    pid=int(name)
    try:
        cmd=open(f'/proc/{pid}/cmdline','rb').read()
        exe=os.readlink(f'/proc/{pid}/exe')
    except Exception: continue
    if udd in cmd and ('brave' in os.path.basename(exe).lower()): pids.append(pid)
for pid in sorted(set(pids), reverse=True):
    try: os.kill(pid,signal.SIGTERM)
    except ProcessLookupError: pass
print('terminated_pids='+','.join(map(str,sorted(set(pids)))))
PY
  for _ in $(seq 1 40); do cdp_up || return 0; sleep 0.25; done
  echo "NEXABURST_BROWSER_STOP_TIMEOUT" >&2
  return 1
}
MODECTL=$(control_mode)
if ! cdp_up; then
  if [[ "$MODECTL" != "RUNNING" ]]; then
    echo "NEXABURST_BROWSER_AUTOSTART_SUPPRESSED control_mode=$MODECTL"
    exit 0
  fi
  if udd_owner_alive; then
    echo "NEXABURST_BROWSER_RECOVERY_DEFERRED reason=udd_owner_alive"
    exit 0
  fi
  if [[ -f "$FAILSTATE" ]]; then
    FAGE=$(fail_age)
    if (( FAGE < 900 )); then
      echo "NEXABURST_BROWSER_RECOVERY_COOLDOWN age_seconds=$FAGE"
      exit 0
    fi
  fi
  if "$BROWSER" https://nexabot.id/image-generator; then
    rm -f "$FAILSTATE"
    exit 0
  else
    COUNT=$(record_failure)
    if (( COUNT >= 3 )); then
      "$NOTIFY" --event FOUNDER_ACTION_REQUIRED --text "Nexa browser failed to start $COUNT times. Automatic browser recovery is cooling down; no rapid reopen loop." --silent >/dev/null 2>&1 || true
    fi
    exit 0
  fi
fi
AGE=$(age_seconds)
if [[ "$MODECTL" != "RUNNING" ]] && [[ "$MODE" != "rotate-now" ]]; then
  echo "NEXABURST_BROWSER_REUSE_CONTROLLED age_seconds=$AGE control_mode=$MODECTL"
  exit 0
fi
if (( AGE < MAX_AGE )) && [[ "$MODE" != "rotate-now" ]]; then
  echo "NEXABURST_BROWSER_REUSE age_seconds=$AGE max_age=$MAX_AGE"
  exit 0
fi
if inflight_alive; then
  echo "NEXABURST_BROWSER_ROTATE_DEFERRED age_seconds=$AGE reason=inflight"
  exit 0
fi
"$NOTIFY" --event BROWSER_ROTATE --text "Rotating nexaburst-p001 after ${AGE}s; no job is in flight." --silent >/dev/null 2>&1 || true
stop_browser
rm -f "$SESSION"
"$BROWSER" https://nexabot.id/image-generator
echo "NEXABURST_BROWSER_ROTATED previous_age_seconds=$AGE"
