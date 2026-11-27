#!/usr/bin/env bash
# PSR lane-2 post-production watchdog (cron * * * * *).
# Keeps KW-Gemini enrichment + V2 post-processing running until both queues drain.
#  - KW: 6 parallel workers, one per live Gemini key (shard 6)
#  - V2: 8 parallel workers (shard 8, OMP_NUM_THREADS=1 — best measured throughput)
# Honours STOP_PSR / net-hold / v2-hold. Idempotent, self-guarded (no spam).
set -u
SESSION=/home/kopiko/die-sessions/NEXABURST-H01-P001
BIN=$SESSION/bin
ROOT=/var/lib/die/h01/nexaburst-lane2-psr
KWOUT=/var/lib/die/h01/nexaburst-kw-psr
STATE=$ROOT/state
LANE2_ENV_FILE=/home/kopiko/.config/die/nexaburst-lane2.env
PY=/opt/die/factory-asset/venv/bin/python
GUARD_SEC=900

iso(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
log(){ echo "$(iso) $*"; }
notify(){
  NEXABURST_ENV_PATH=$LANE2_ENV_FILE "$BIN/nexaburst-notify.py" \
    --event BATCH_SUMMARY --text "lane=PSR-L0 postprod-watchdog $*" \
    >/dev/null 2>&1 || true
}
guard_ok(){ local m="$STATE/postprod-watchdog.$1"
  [[ ! -f "$m" ]] && return 0
  (( $(date +%s) - $(stat -c %Y "$m") >= GUARD_SEC )); }
mark(){ touch "$STATE/postprod-watchdog.$1"; }

# honour hard stops
[[ -f "$STATE/STOP_PSR" ]] && { log "SKIP STOP_PSR present"; exit 0; }
if python3 -c "import json;raise SystemExit(0 if json.load(open('/var/lib/die/h01/nexaburst/state/net-hold.json')).get('hold') else 1)" 2>/dev/null; then
  log "SKIP net-hold active"; exit 0
fi

# ---- work remaining? ----
read -r KW_TODO V2_TODO < <(python3 - "$ROOT" "$KWOUT" <<'EOF'
import json,sys,os
root,kwout=sys.argv[1],sys.argv[2]
q=os.path.join(root,'state','v2-queue.jsonl')
d=os.path.join(root,'state','v2-done.jsonl')
h=os.path.join(root,'state','v2-hold-ids.txt')
def ids(p,key='asset_id'):
    s=set()
    if os.path.isfile(p):
        for l in open(p,encoding='utf-8'):
            l=l.strip()
            if not l: continue
            try: s.add(json.loads(l).get(key))
            except Exception: pass
    return s
queue=ids(q)
done=ids(d)
held=set()
if os.path.isfile(h):
    held={x.strip() for x in open(h,encoding='utf-8') if x.strip()}
kw=ids(os.path.join(kwout,'receipts.jsonl'))
open_ids=queue-done-held
kw_todo=len(open_ids-kw)
v2_todo=len(open_ids&kw)
print(kw_todo,v2_todo)
EOF
)
log "TODO kw=$KW_TODO v2=$V2_TODO"
if [[ "${KW_TODO:-0}" -eq 0 && "${V2_TODO:-0}" -eq 0 ]]; then
  if [[ ! -f "$STATE/postprod-drained" ]]; then
    touch "$STATE/postprod-drained"
    notify "DRAINED — KW + V2 queue empty. Post-production complete."
    log "DRAINED"
  fi
  exit 0
fi
rm -f "$STATE/postprod-drained"

# ---- KW workers (6, one per live key) ----
KW_QUOTA_FILE=$KWOUT/quota-exhausted-until
KW_READY=1
if [[ -f "$KW_QUOTA_FILE" ]]; then
  UNTIL=$(cat "$KW_QUOTA_FILE" 2>/dev/null || echo 0)
  if [[ "$(date -u +%s)" -lt "${UNTIL:-0}" ]]; then
    KW_READY=0
    log "KW quota exhausted until $(date -u -d @$UNTIL +%Y-%m-%dT%H:%M:%SZ) — waiting"
  fi
fi
if [[ "${KW_TODO:-0}" -gt 0 && "$KW_READY" -eq 1 ]]; then
  declare -A SHARD=([0]=0 [3]=1 [4]=2 [5]=3 [7]=4)
  for k in 0 3 4 5 7; do
    if ! pgrep -f "kw-enrich.py .*--key-subset $k " >/dev/null 2>&1; then
      if guard_ok "kw$k"; then
        mark "kw$k"
        nohup "$BIN/nexaburst-kw-enrich.py" --all \
          --queue "$ROOT/state/v2-queue.jsonl" --out "$KWOUT" \
          --daily-cap 100000000 --gap 0.5 --min-gap 7 \
          --key-subset "$k" --shard "${SHARD[$k]}/5" --tag "k$k" --skip 1,2,6 \
          >> "$KWOUT/run-k$k.log" 2>&1 &
        log "RELAUNCH kw key=$k pid=$!"
        notify "RELAUNCH kw-enrich key=$k (todo=$KW_TODO)"
      else
        log "kw$k relaunch guarded"
      fi
    fi
  done
fi

# ---- vault workers (2 shards, one asset each per tick) ----
VAULT_TODO=$(python3 - "$ROOT" <<'EOF'
import json,sys,os
root=sys.argv[1]
d=os.path.join(root,'state','vault-done.jsonl')
h=os.path.join(root,'state','vault-hold-ids.txt')
done=set()
if os.path.isfile(d):
    for l in open(d,encoding='utf-8'):
        l=l.strip()
        if l:
            try: done.add(json.loads(l).get('archive_identity'))
            except Exception: pass
held=set()
if os.path.isfile(h):
    held={x.strip() for x in open(h,encoding='utf-8') if x.strip()}
n=0
for w in sorted(os.listdir(os.path.join(root,'workspaces'))):
    if w in held: continue
    st=os.path.join(root,'workspaces',w,'factory-v2','postproduction-state.json')
    if not os.path.isfile(st): continue
    try: s=json.load(open(st,encoding='utf-8'))
    except Exception: continue
    if s.get('state')!='METADATA_READY': continue
    n+=1
print(n)
EOF
)
if [[ "${VAULT_TODO:-0}" -gt 0 ]]; then
  for i in 0 1; do
    if ! pgrep -f "nexaburst-vault.py --once --shard $i/2" >/dev/null 2>&1; then
      NEXABURST_ENV_PATH=$LANE2_ENV_FILE NEXABURST_ROOT=$ROOT \
        nohup /usr/bin/python3 "$BIN/nexaburst-vault.py" --once --shard "$i/2" \
        >> "$STATE/vault-shard-$i.log" 2>&1 &
    fi
  done
fi

# ---- V2 workers (4) ----
if [[ "${V2_TODO:-0}" -gt 0 ]]; then
  if [[ -f "$STATE/v2-worker.hold" ]]; then
    log "SKIP v2 workers (v2-worker.hold present)"
  else
    for i in 0 1 2 3 4 5 6 7; do
      if ! pgrep -f "v2-worker-psr.py --continuous.*--shard $i/8" >/dev/null 2>&1; then
        if guard_ok "v2$i"; then
          mark "v2$i"
          OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nohup "$PY" "$BIN/nexaburst-v2-worker-psr.py" \
            --continuous --poll-seconds 5 --shard "$i/8" \
            >> "$STATE/v2-worker-psr-$i.log" 2>&1 &
          log "RELAUNCH v2 shard=$i/8 pid=$!"
          notify "RELAUNCH v2-worker shard=$i/8 (todo=$V2_TODO)"
        else
          log "v2$i relaunch guarded"
        fi
      fi
    done
  fi
fi
exit 0
