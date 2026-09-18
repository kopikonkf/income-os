#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"; target="${2:-}"; url="${3:-https://chatgpt.com/}"
case "$target" in
  executive) profile=/var/lib/die/executive/browser-profile; hold=/var/lib/die/state/principal-auth-repair/die-lnx-executive-001.json; map=executive; klass=DIE-Executive-FounderHandoff ;;
  division01) profile=/var/lib/die/division01/browser-profile; hold=/var/lib/die/state/principal-auth-repair/die-lnx-division-001.json; map=division01; klass=DIE-Division01-FounderHandoff ;;
  runtime01|cluster-a) profile=/var/lib/muxia/profiles/chatgpt-linux-a/browser; hold=/var/lib/muxia/state/founder-repair/cluster-a.json; map=runtime01; klass=DIE-V1-Runtime01-FounderHandoff ;;
  runtime02|cluster-b) profile=/var/lib/muxia/profiles/web-ai-cluster-b/browser; hold=/var/lib/muxia/state/founder-repair/cluster-b.json; map=runtime02; klass=DIE-V1-Runtime02-FounderHandoff ;;
  *) echo 'usage: die-founder-browser-handoff acquire|status|release executive|division01|runtime01|runtime02 [url]' >&2; exit 64 ;;
esac
proc_for_profile(){
  for d in /proc/[0-9]*; do
    [[ -r "$d/cmdline" ]] || continue
    first="$(tr '\0' '\n' <"$d/cmdline" 2>/dev/null | sed -n '1p')"
    case "$first" in */chrome|*/chromium|*/brave|*/google-chrome|*/google-chrome-stable) ;; *) continue ;; esac
    if tr '\0' '\n' <"$d/cmdline" 2>/dev/null | grep -Fqx -- "--user-data-dir=$profile"; then basename "$d"; return 0; fi
  done
  return 0
}
write_hold(){
  local state="$1" reason="$2"
  python3 - "$hold" "$target" "$profile" "$state" "$reason" <<'PY'
import datetime,json,os,sys,tempfile
p,target,profile,state,reason=sys.argv[1:]
os.makedirs(os.path.dirname(p),exist_ok=True)
try:v=json.load(open(p))
except Exception:v={'schema':'die.browser.auth-repair-hold.v1'}
now=datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
v.update({'schema':'die.browser.auth-repair-hold.v1','state':state,'mode':'FOUNDER_INTERACTIVE_HANDOFF','scope_id':target,'profile_id':profile,'requires_founder_release':state=='ACTIVE','automated_cdp_allowed':False,'credential_values_read':False,'cookies_or_tokens_read':False,'captcha_bypass_authorized':False})
if state=='ACTIVE':v.update({'reason_code':reason,'founder_handoff_requested_at':now})
else:v.update({'closed_by':'FOUNDER_INTERACTIVE_HANDOFF','closed_at':now})
fd,tmp=tempfile.mkstemp(prefix='.founder-handoff-',dir=os.path.dirname(p));os.close(fd)
with open(tmp,'w') as f:json.dump(v,f,indent=2);f.write('\n')
os.chmod(tmp,0o640);os.replace(tmp,p)
PY
}
case "$cmd" in
  status)
    echo "TARGET=$target"; echo "PROFILE=$profile"; echo "PID=$(proc_for_profile || true)"; [[ -f "$hold" ]] && cat "$hold" || echo '{"state":"ABSENT"}'
    ;;
  release)
    pid="$(proc_for_profile || true)"; [[ -z "$pid" ]] || { echo "E_FOUNDER_BROWSER_STILL_ACTIVE:$pid" >&2; exit 73; }
    write_hold CLOSED FOUNDER_RELEASED
    echo "FOUNDER_HANDOFF_RELEASED target=$target"
    ;;
  acquire)
    [[ -S /tmp/.X11-unix/X12 ]] || { echo E_FOUNDER_DISPLAY12_UNAVAILABLE >&2; exit 69; }
    export DISPLAY=:12.0
    /usr/bin/wmctrl -d >/dev/null 2>&1 || { echo E_FOUNDER_DISPLAY12_WM >&2; exit 69; }
    /usr/bin/wmctrl -n 5
    write_hold ACTIVE FOUNDER_PREEMPT_REQUEST
    wait_seconds="${DIE_FOUNDER_HANDOFF_WAIT_SECONDS:-900}"
    deadline=$((SECONDS+wait_seconds))
    while pid="$(proc_for_profile || true)"; [[ -n "$pid" ]]; do
      if (( SECONDS >= deadline )); then echo "E_FOUNDER_HANDOFF_DRAIN_TIMEOUT:$pid" >&2; exit 75; fi
      sleep 1
    done
    for f in DevToolsActivePort SingletonLock SingletonCookie SingletonSocket; do rm -f "$profile/$f"; done
    set +e
    /usr/bin/google-chrome-stable --user-data-dir="$profile" --no-first-run --no-default-browser-check --disable-background-mode --class="$klass" "$url" >/tmp/die-founder-handoff-${target}.out 2>/tmp/die-founder-handoff-${target}.err &
    browser_pid=$!
    set -e
    /usr/local/bin/node /srv/die/company/browser/linux/founder_display12.mjs place "$map" "$browser_pid" || { kill -TERM "$browser_pid" 2>/dev/null || true; wait "$browser_pid" 2>/dev/null || true; echo E_FOUNDER_HANDOFF_PLACEMENT >&2; exit 76; }
    echo "FOUNDER_HANDOFF_ACTIVE target=$target pid=$browser_pid display=:12.0"
    set +e; wait "$browser_pid"; rc=$?; set -e
    pid="$(proc_for_profile || true)"; [[ -z "$pid" ]] || { echo "E_FOUNDER_BROWSER_STILL_ACTIVE_AFTER_OWNER_EXIT:$pid" >&2; exit 77; }
    write_hold CLOSED FOUNDER_BROWSER_CLOSED
    echo "FOUNDER_HANDOFF_CLOSED target=$target rc=$rc"
    exit "$rc"
    ;;
  *) echo 'usage: die-founder-browser-handoff acquire|status|release TARGET [url]' >&2; exit 64 ;;
esac
