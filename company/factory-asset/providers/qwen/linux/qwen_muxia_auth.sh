#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-probe}"
MUXIA_RUNTIME="${MUXIA_RUNTIME:-/srv/die/company/muxia/scripts/linux/muxia-webai-browser-runtime.mjs}"
NODE="${NODE:-/usr/local/bin/node}"
XVFB="${XVFB:-/usr/bin/xvfb-run}"
BROWSER_EXECUTABLE="${BROWSER_EXECUTABLE:-/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome}"
PROFILE_ID="${QWEN_MUXIA_PROFILE_ID:-chatgpt-linux-a}"
PROFILE_DIR="${QWEN_MUXIA_PROFILE_DIR:-/var/lib/muxia/profiles/${PROFILE_ID}/browser}"
STATUS_FILE="${QWEN_MUXIA_STATUS_FILE:-/var/lib/muxia/state/fa112-qwen-auth-status.json}"
START_URL="https://chat.qwen.ai/"
PRINCIPAL_ID="muxia-${PROFILE_ID}"

runtime_args=("$NODE" "$MUXIA_RUNTIME" --die-home /srv/die --profile-id "$PROFILE_ID" --profile-dir "$PROFILE_DIR" --status-file "$STATUS_FILE" --browser-executable "$BROWSER_EXECUTABLE" --start-url "$START_URL" --principal-id "$PRINCIPAL_ID")

case "$MODE" in
  login)
    [[ -n "${DISPLAY:-}" ]] || { echo 'FA112_QWEN_LOGIN_REQUIRES_VISIBLE_RDP_DISPLAY' >&2; exit 3; }
    echo 'FA112_QWEN_OPERATOR_LOGIN_NO_CDP: login to Qwen in Cluster A, then CLOSE the browser. No prompt should be submitted.' >&2
    exec "$BROWSER_EXECUTABLE" \
      --user-data-dir="$PROFILE_DIR" \
      --no-first-run \
      --no-default-browser-check \
      --class=MUXIA-${PROFILE_ID}-auth \
      "$START_URL"
    ;;
  probe)
    set +e
    "$XVFB" -a "${runtime_args[@]}" --command probe >/tmp/fa112-qwen-probe.out 2>/tmp/fa112-qwen-probe.err
    set -e
    [[ -f "$STATUS_FILE" ]] || { echo '{"status":"UNKNOWN","reason":"NO_STATUS_FILE"}'; exit 4; }
    /usr/bin/python3 - "$STATUS_FILE" "$PROFILE_ID" <<'PY'
import json,sys
from urllib.parse import urlsplit
p,profile_id=sys.argv[1:3]
v=json.load(open(p))
raw=str(v.get('url',''))
s=urlsplit(raw)
url=f'{s.scheme}://{s.netloc}{s.path}' if s.scheme and s.netloc else ''
login=int(v.get('loginUiCount') or 0);edit=int(v.get('editableCount') or 0)
base={'profile_id':profile_id,'url':url,'login_ui_count':login,'editable_count':edit,'prompt_submitted':False,'credential_values_read':False}
if login>0 or any(x in url.lower() for x in ('login','signup','auth')):
    print(json.dumps({'status':'AUTH_REQUIRED',**base}))
    raise SystemExit(3)
if 'qwen.ai' in url and edit>0 and login==0:
    print(json.dumps({'status':'READY',**base}))
    raise SystemExit(0)
print(json.dumps({'status':'UNKNOWN',**base}))
raise SystemExit(4)
PY
    ;;
  *) echo 'usage: qwen_muxia_auth.sh [probe|login]' >&2; exit 2 ;;
esac
