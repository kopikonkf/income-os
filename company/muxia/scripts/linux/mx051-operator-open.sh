#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX051_OPERATOR_REQUIRES_LINUX" >&2
  exit 40
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo "MX051_OPERATOR_REQUIRES_DESKTOP_SESSION" >&2
  exit 41
fi
if (( EUID == 0 )); then
  echo "MX051_OPERATOR_MUST_NOT_RUN_AS_ROOT" >&2
  exit 42
fi

MUXIA_ROOT="${MUXIA_ROOT:-/var/lib/muxia}"
PROFILE_ID="${MUXIA_PROFILE_ID:-chatgpt-linux-a}"
PROFILE_DIR="$MUXIA_ROOT/profiles/$PROFILE_ID/browser"
STATE_DIR="$MUXIA_ROOT/state"
CHROME="${MUXIA_CHROME:-/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome}"
RECEIPT="$STATE_DIR/mx051-operator-auth-bootstrap.json"

test -x "$CHROME"
install -d -m 0700 "$PROFILE_DIR" "$STATE_DIR"
if pgrep -af -- "--user-data-dir=$PROFILE_DIR" >/dev/null; then
  echo "MX051_PROFILE_ALREADY_RUNNING:$PROFILE_ID" >&2
  exit 43
fi

"$CHROME"   --user-data-dir="$PROFILE_DIR"   --no-first-run   --no-default-browser-check   --ozone-platform=x11   https://chatgpt.com/auth/login   >/dev/null 2>&1 &
BROWSER_PID=$!

cat >"$RECEIPT" <<EOF
{
  "schema": "die.muxia.mx051.operator-auth-bootstrap.v1",
  "task_id": "MX-051",
  "status": "WAITING_OPERATOR_LOGIN",
  "mode": "OPERATOR_CONTROLLED_NORMAL_CHROMIUM",
  "browser_pid": $BROWSER_PID,
  "profile_id": "$PROFILE_ID",
  "profile_dir": "$PROFILE_DIR",
  "provider_url": "https://chatgpt.com/auth/login",
  "remote_debugging_enabled": false,
  "playwright_attached": false,
  "automation_flags_added": false,
  "credential_values_read_by_muxia": false,
  "bypass_attempted": false,
  "opened_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "Browser MUXIA sudah dibuka."
echo "Login ChatGPT secara manual, pastikan halaman chat siap, lalu TUTUP Chromium."
echo "Profile: $PROFILE_ID"
wait "$BROWSER_PID"
echo "MX051_OPERATOR_BROWSER_CLOSED:$PROFILE_ID"
