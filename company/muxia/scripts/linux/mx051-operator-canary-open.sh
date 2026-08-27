#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX051_CANARY_REQUIRES_LINUX" >&2
  exit 50
fi
if [[ -z "${DISPLAY:-}" ]]; then
  echo "MX051_CANARY_REQUIRES_DESKTOP_SESSION" >&2
  exit 51
fi
if (( EUID == 0 )); then
  echo "MX051_CANARY_MUST_NOT_RUN_AS_ROOT" >&2
  exit 52
fi

MUXIA_ROOT="${MUXIA_ROOT:-/var/lib/muxia}"
PROFILE_ID="${MUXIA_PROFILE_ID:-chatgpt-linux-a}"
PROFILE_DIR="$MUXIA_ROOT/profiles/$PROFILE_ID/browser"
STATE_DIR="$MUXIA_ROOT/state"
DOWNLOAD_DIR="$HOME/Downloads"
CHROME="${MUXIA_CHROME:-/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome}"
RECEIPT="$STATE_DIR/mx051-operator-canary-session.json"

test -x "$CHROME"
test -d "$PROFILE_DIR"
install -d -m 0700 "$STATE_DIR" "$DOWNLOAD_DIR"
if pgrep -af -- "--user-data-dir=$PROFILE_DIR" >/dev/null; then
  echo "MX051_PROFILE_ALREADY_RUNNING:$PROFILE_ID" >&2
  exit 53
fi

cat >"$RECEIPT" <<EOF
{
  "schema": "die.muxia.mx051.operator-canary-session.v1",
  "task_id": "MX-051",
  "status": "WAITING_OPERATOR_CANARIES",
  "interaction_mode": "OPERATOR_CONTROLLED_NORMAL_CHROMIUM",
  "profile_id": "$PROFILE_ID",
  "profile_dir": "$PROFILE_DIR",
  "provider_url": "https://chatgpt.com/",
  "download_dir": "$DOWNLOAD_DIR",
  "expected_text_response": "MUXIA_LINUX_TEXT_OK_1",
  "remote_debugging_enabled": false,
  "playwright_attached": false,
  "prompt_submitted_by_automation": false,
  "output_extracted_by_automation": false,
  "credential_values_read_by_muxia": false,
  "bypass_attempted": false,
  "opened_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

"$CHROME" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --ozone-platform=x11 \
  https://chatgpt.com/ \
  >/dev/null 2>&1 &
BROWSER_PID=$!

echo
echo "MX-051 OPERATOR CANARY"
echo "1) Text prompt:"
echo "   Reply with exactly this text and nothing else: MUXIA_LINUX_TEXT_OK_1"
echo "2) Pastikan jawabannya persis: MUXIA_LINUX_TEXT_OK_1"
echo "3) Image prompt:"
echo "   Create one square image: a single solid blue circle centered on a plain white background, with no text."
echo "4) Download gambar dengan tombol Download ke folder default Downloads."
echo "5) Tutup Chromium, lalu beri tahu Architect: CANARY SELESAI."
echo
wait "$BROWSER_PID"
echo "MX051_OPERATOR_CANARY_BROWSER_CLOSED:$PROFILE_ID"
