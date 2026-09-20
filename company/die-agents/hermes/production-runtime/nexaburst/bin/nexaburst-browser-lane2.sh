#!/usr/bin/env bash
set -euo pipefail
UDD="/var/lib/die/h01/nexaburst-lane2-psr/profiles/nexaburst-psr-p001/udd"
STATE="/var/lib/die/h01/nexaburst-lane2-psr/state"
PORT=9321
URL="${1:-https://nexabot.id/image-generator}"
LOG="$STATE/nexaburst-psr-p001-browser.log"
PIDFILE="$STATE/nexaburst-psr-p001-browser.pid"
LOCK="/run/user/$(id -u)/nexaburst-psr-p001.lock"
export DISPLAY=":12.0"
export XAUTHORITY="/home/kopiko/.Xauthority"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
mkdir -p "$UDD" "$STATE" "$(dirname "$LOCK")"
chmod 700 "$UDD"
wmctrl -n 6 >/dev/null 2>&1 || true
if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then wmctrl -s 5 >/dev/null 2>&1 || true; echo "NEXABURST_LANE2_BROWSER_ALREADY_READY cdp=127.0.0.1:$PORT workspace=6"; exit 0; fi
if pgrep -af -- "--user-data-dir=$UDD" >/dev/null 2>&1; then echo "NEXABURST_LANE2_UDD_BUSY $UDD" >&2; exit 73; fi
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${PORT}$"; then echo "NEXABURST_LANE2_CDP_PORT_BUSY 127.0.0.1:$PORT" >&2; exit 73; fi
rm -f "$UDD/SingletonLock" "$UDD/SingletonCookie" "$UDD/SingletonSocket"
wmctrl -s 5 >/dev/null 2>&1 || true
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
    --class=NEXABURST-PSR-P001 \
    "$URL"
) 9>"$LOCK" >>"$LOG" 2>&1 &
PID=$!
printf '%s\n' "$PID" > "$PIDFILE"
for _ in $(seq 1 80); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    for p in $(pgrep -f -- "--user-data-dir=$UDD" || true); do
      WIN=$(wmctrl -lp 2>/dev/null | awk -v p="$p" '$3==p {print $1; exit}')
      if [[ -n "${WIN:-}" ]]; then wmctrl -i -r "$WIN" -t 5 >/dev/null 2>&1 || true; wmctrl -i -r "$WIN" -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true; break; fi
    done
    wmctrl -s 5 >/dev/null 2>&1 || true
    echo "NEXABURST_LANE2_BROWSER_READY cdp=127.0.0.1:$PORT workspace=6 udd=$UDD"; exit 0
  fi
  sleep .5
done
echo "NEXABURST_LANE2_BROWSER_START_TIMEOUT" >&2
exit 70
