#!/usr/bin/env bash
set -euo pipefail
arg(){ local k="$1"; shift; while (($#)); do if [[ "$1" == "$k" ]]; then echo "$2"; return 0; fi; shift; done; return 1; }
CLUSTER_ID=$(arg --cluster-id "$@")
PROFILE_DIR=$(arg --profile-dir "$@")
DEBUG_PORT=$(arg --debug-port "$@")
DISPLAY_NUM=$(arg --x-display "$@")
STATE_ROOT=$(arg --state-root "$@")
CHROME_BIN=${CHROME_BIN:-/usr/bin/google-chrome-stable}
[[ "$CLUSTER_ID" =~ ^[A-Za-z0-9._-]+$ ]] || { echo E_EXTERNAL_BROWSER_CLUSTER >&2; exit 2; }
[[ "$PROFILE_DIR" = /* && -d "$PROFILE_DIR" ]] || { echo E_EXTERNAL_BROWSER_PROFILE >&2; exit 2; }
[[ "$DEBUG_PORT" =~ ^[0-9]+$ && "$DISPLAY_NUM" =~ ^[0-9]+$ ]] || { echo E_EXTERNAL_BROWSER_PORT_DISPLAY >&2; exit 2; }
[[ -x "$CHROME_BIN" ]] || { echo E_EXTERNAL_BROWSER_BINARY >&2; exit 2; }
mkdir -p "$STATE_ROOT"
PID_FILE="$STATE_ROOT/$CLUSTER_ID.owner.pid"; META_FILE="$STATE_ROOT/$CLUSTER_ID.owner.json"
if [[ -L "$PROFILE_DIR/SingletonLock" ]]; then
  target=$(readlink "$PROFILE_DIR/SingletonLock" || true); pid=${target##*-}
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then echo "E_EXTERNAL_BROWSER_PROFILE_OWNED:$pid" >&2; exit 3; fi
  rm -f "$PROFILE_DIR/SingletonLock" "$PROFILE_DIR/SingletonCookie" "$PROFILE_DIR/SingletonSocket"
elif [[ -e "$PROFILE_DIR/SingletonLock" ]]; then
  echo E_EXTERNAL_BROWSER_UNKNOWN_LOCK >&2; exit 3
fi
if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${DEBUG_PORT}$"; then echo E_EXTERNAL_BROWSER_DEBUG_PORT_IN_USE >&2; exit 4; fi
cleanup(){ rm -f "$PID_FILE" "$META_FILE"; }
child=''
term(){ [[ -n "$child" ]] && kill -TERM "$child" 2>/dev/null || true; [[ -n "$child" ]] && wait "$child" 2>/dev/null || true; cleanup; exit 0; }
trap term INT TERM
trap cleanup EXIT
printf '%s\n' "$$" > "$PID_FILE"
python3 - <<PY
import json
from pathlib import Path
Path('$META_FILE').write_text(json.dumps({'schema':'die.muxia.external-browser-owner.v1','cluster_id':'$CLUSTER_ID','owner_pid':$$,'profile_dir':'$PROFILE_DIR','debug_host':'127.0.0.1','debug_port':int('$DEBUG_PORT'),'browser_owner_model':'EXTERNAL_PERSISTENT_CHROME_CDP','credential_values_read':False,'cookies_or_tokens_read':False},sort_keys=True)+'\n')
PY
/usr/bin/xvfb-run --server-num="$DISPLAY_NUM" --server-args='-screen 0 1920x1080x24' "$CHROME_BIN" \
  --user-data-dir="$PROFILE_DIR" --remote-debugging-address=127.0.0.1 --remote-debugging-port="$DEBUG_PORT" \
  --no-first-run --no-default-browser-check --disable-session-crashed-bubble --disable-background-mode about:blank &
child=$!
wait "$child"
