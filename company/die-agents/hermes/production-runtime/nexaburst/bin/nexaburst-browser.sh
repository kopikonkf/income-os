#!/usr/bin/env bash
set -euo pipefail

CFG="/home/kopiko/die-sessions/NEXABURST-H01-P001/config/nexaburst.json"
UDD="/var/lib/die/h01/nexaburst/profiles/nexaburst-p001/udd"
STATE="/var/lib/die/h01/nexaburst/state"
PORT=9311
URL="${1:-https://nexabot.id/image-generator}"
LOG="$STATE/nexaburst-p001-browser.log"
PIDFILE="$STATE/nexaburst-p001-browser.pid"
LOCK="/run/user/$(id -u)/nexaburst-p001.lock"

export DISPLAY=":12.0"
export XAUTHORITY="/home/kopiko/.Xauthority"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

mkdir -p "$UDD" "$STATE" "$(dirname "$LOCK")"
chmod 700 "$UDD"

if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "NEXABURST_BROWSER_ALREADY_READY cdp=127.0.0.1:$PORT"
  wmctrl -s 3 >/dev/null 2>&1 || true
  exit 0
fi

if [[ -x /opt/die/h01/bin/h01-brave-storage-gate ]]; then
  /opt/die/h01/bin/h01-brave-storage-gate admit >/dev/null
fi

if pgrep -af -- "--user-data-dir=$UDD" >/dev/null 2>&1; then
  echo "NEXABURST_UDD_BUSY $UDD" >&2
  exit 73
fi

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${PORT}$"; then
  echo "NEXABURST_CDP_PORT_BUSY 127.0.0.1:$PORT" >&2
  exit 73
fi

# Dedicated UDD: removing stale Singleton* is safe only after no owner was found.
rm -f "$UDD/SingletonLock" "$UDD/SingletonCookie" "$UDD/SingletonSocket"

# Make Workspace 4 visible before opening the dedicated browser.
wmctrl -n 5 >/dev/null 2>&1 || true
wmctrl -s 3 >/dev/null 2>&1 || true

(
  flock -n -E 73 9 || exit $?
  exec /usr/bin/brave-browser \
    --user-data-dir="$UDD" \
    --remote-debugging-address=127.0.0.1 \
    --remote-debugging-port="$PORT" \
    --no-first-run \
    --no-default-browser-check \
    --disable-infobars \
    --disable-crash-reporter \
    --no-crash-upload \
    --disable-background-mode \
    --class=NEXABURST-P001 \
    "$URL"
) 9>"$LOCK" >>"$LOG" 2>&1 &

PID=$!
printf '%s\n' "$PID" > "$PIDFILE"

for _ in $(seq 1 80); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    WIN=$(wmctrl -lp 2>/dev/null | awk -v p="$PID" '$3==p {print $1; exit}')
    if [[ -n "${WIN:-}" ]]; then
      wmctrl -i -r "$WIN" -t 3 >/dev/null 2>&1 || true
      wmctrl -i -r "$WIN" -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
    fi
    wmctrl -s 3 >/dev/null 2>&1 || true
    STARTED_EPOCH=$(date +%s)
    cat > "$STATE/nexaburst-p001-browser-session.json" <<EOF
{"pid":$PID,"started_epoch":$STARTED_EPOCH,"cdp":"127.0.0.1:$PORT","display":":12","workspace":4}
EOF
    chmod 640 "$STATE/nexaburst-p001-browser-session.json"
    echo "NEXABURST_BROWSER_READY pid=$PID udd=$UDD cdp=127.0.0.1:$PORT display=:12 workspace=4"
    exit 0
  fi
  sleep 0.25
done

echo "NEXABURST_BROWSER_START_TIMEOUT pid=$PID log=$LOG" >&2
exit 75
