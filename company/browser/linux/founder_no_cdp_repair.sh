#!/usr/bin/env bash
set -euo pipefail
principal="${1:-}"; url="${2:-https://chatgpt.com/}"
case "$principal" in
  executive) profile=/var/lib/die/executive/browser-profile; klass=DIE-Executive-AuthRepair; hold=/var/lib/die/state/principal-auth-repair/die-lnx-executive-001.json ;;
  division01) profile=/var/lib/die/division01/browser-profile; klass=DIE-Division01-AuthRepair; hold=/var/lib/die/state/principal-auth-repair/die-lnx-division-001.json ;;
  cluster-a) profile=/var/lib/muxia/profiles/chatgpt-linux-a/browser; klass=DIE-V1-Runtime01-AuthRepair; hold=/var/lib/muxia/state/founder-repair/cluster-a.json ;;
  cluster-b) profile=/var/lib/muxia/profiles/web-ai-cluster-b/browser; klass=DIE-V1-Runtime02-AuthRepair; hold=/var/lib/muxia/state/founder-repair/cluster-b.json ;;
  *) echo 'usage: founder_no_cdp_repair.sh executive|division01|cluster-a|cluster-b [url]' >&2; exit 64 ;;
esac
[[ -d "$profile" ]] || { echo E_REPAIR_PROFILE >&2; exit 66; }
ps -eo args= | grep -F -- "--user-data-dir=$profile" | grep -E 'chrome|chromium|brave' >/dev/null && { echo E_REPAIR_PROFILE_BUSY >&2; exit 73; }
export DISPLAY="${DISPLAY:-:12.0}"
export XAUTHORITY="${XAUTHORITY:-/home/kopiko/.Xauthority}"
echo "FOUNDER_NO_CDP_REPAIR principal=$principal profile=$profile display=$DISPLAY" >&2
set +e
/usr/bin/google-chrome-stable --user-data-dir="$profile" --no-first-run --no-default-browser-check --disable-background-mode --class="$klass" "$url"
rc=$?
set -e
if [[ $rc -eq 0 ]]; then
  python3 - "$hold" "$principal" <<'PY'
import json,os,sys,tempfile,datetime
p,principal=sys.argv[1:]
os.makedirs(os.path.dirname(p),exist_ok=True)
try:v=json.load(open(p))
except Exception:v={'schema':'die.browser.auth-repair-hold.v1','scope_id':principal}
v.update({'state':'CLOSED','requires_founder_release':False,'automated_cdp_allowed':False,'closed_by':'FOUNDER_NO_CDP_REPAIR','closed_at':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'credential_values_read':False,'cookies_or_tokens_read':False,'captcha_bypass_authorized':False})
fd,tmp=tempfile.mkstemp(prefix='.repair-close-',dir=os.path.dirname(p));os.close(fd)
with open(tmp,'w') as f:json.dump(v,f,indent=2);f.write('\n')
os.chmod(tmp,0o640);os.replace(tmp,p)
PY
fi
exit "$rc"
