#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-probe}"
MUXIA_RUNTIME="${MUXIA_RUNTIME:-/srv/die/company/muxia/scripts/linux/muxia-webai-browser-runtime.mjs}"
NODE="${NODE:-/usr/local/bin/node}"
XVFB="${XVFB:-/usr/bin/xvfb-run}"
PROFILE_ID="${QWEN_MUXIA_PROFILE_ID:-web-ai-shared}"
PROFILE_DIR="${QWEN_MUXIA_PROFILE_DIR:-/var/lib/muxia/profiles/${PROFILE_ID}/browser}"
STATUS_FILE="${QWEN_MUXIA_STATUS_FILE:-/var/lib/muxia/state/fa112-qwen-auth-status.json}"
START_URL="https://chat.qwen.ai/"
PRINCIPAL_ID="muxia-${PROFILE_ID}"

runtime_args=("$NODE" "$MUXIA_RUNTIME" --die-home /srv/die --profile-id "$PROFILE_ID" --profile-dir "$PROFILE_DIR" --status-file "$STATUS_FILE" --start-url "$START_URL" --principal-id "$PRINCIPAL_ID")

case "$MODE" in
  login)
    [[ -n "${DISPLAY:-}" ]] || { echo 'FA112_QWEN_LOGIN_REQUIRES_VISIBLE_RDP_DISPLAY' >&2; exit 3; }
    echo 'FA112_QWEN_OPERATOR_LOGIN: login to Qwen in this MUXIA-owned browser, then CLOSE the browser. No prompt should be submitted.' >&2
    exec "${runtime_args[@]}" --command launch
    ;;
  probe)
    set +e
    "$XVFB" -a "${runtime_args[@]}" --command probe >/tmp/fa112-qwen-probe.out 2>/tmp/fa112-qwen-probe.err
    set -e
    [[ -f "$STATUS_FILE" ]] || { echo '{"status":"UNKNOWN","reason":"NO_STATUS_FILE"}'; exit 4; }
    /usr/bin/python3 - "$STATUS_FILE" <<'PY'
import json,sys
p=sys.argv[1];v=json.load(open(p))
url=str(v.get('url',''));login=int(v.get('loginUiCount') or 0);edit=int(v.get('editableCount') or 0)
if login>0 or any(x in url.lower() for x in ('login','signup','auth')):
    print(json.dumps({'status':'AUTH_REQUIRED','profile_id':'web-ai-shared','url':url,'login_ui_count':login,'editable_count':edit,'prompt_submitted':False,'credential_values_read':False}))
    raise SystemExit(3)
if 'qwen.ai' in url and edit>0 and login==0:
    print(json.dumps({'status':'READY','profile_id':'web-ai-shared','url':url,'login_ui_count':login,'editable_count':edit,'prompt_submitted':False,'credential_values_read':False}))
    raise SystemExit(0)
print(json.dumps({'status':'UNKNOWN','profile_id':'web-ai-shared','url':url,'login_ui_count':login,'editable_count':edit,'prompt_submitted':False,'credential_values_read':False}))
raise SystemExit(4)
PY
    ;;
  *) echo 'usage: qwen_muxia_auth.sh [probe|login]' >&2; exit 2 ;;
esac
