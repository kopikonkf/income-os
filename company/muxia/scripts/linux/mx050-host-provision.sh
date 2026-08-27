#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX050_REQUIRES_LINUX" >&2
  exit 20
fi
if (( EUID != 0 )); then
  echo "MX050_HOST_PROVISION_REQUIRES_ROOT" >&2
  exit 24
fi

SOURCE_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BROWSER_ROOT="${PLAYWRIGHT_BROWSERS_PATH:-/opt/muxia/playwright-browsers}"
EXPECTED_BROWSER="$BROWSER_ROOT/chromium-1234/chrome-linux64/chrome"
APPARMOR_SOURCE="$SOURCE_DIR/config/linux/apparmor.d/muxia-playwright-chrome"
APPARMOR_TARGET="/etc/apparmor.d/muxia-playwright-chrome"

command -v node >/dev/null 2>&1 || { echo "NODE_REQUIRED" >&2; exit 21; }
command -v npm >/dev/null 2>&1 || { echo "NPM_REQUIRED" >&2; exit 22; }
command -v apparmor_parser >/dev/null 2>&1 || { echo "APPARMOR_PARSER_REQUIRED" >&2; exit 25; }

NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
if (( NODE_MAJOR != 24 )); then
  echo "NODE_24_LTS_REQUIRED:found=${NODE_MAJOR}" >&2
  exit 23
fi

install -d -o root -g root -m 0755 /opt/muxia "$BROWSER_ROOT"
cd "$SOURCE_DIR"
export PLAYWRIGHT_BROWSERS_PATH="$BROWSER_ROOT"
export DEBIAN_FRONTEND=noninteractive
npx playwright install --with-deps chromium
chown -R root:root /opt/muxia
find /opt/muxia -type d -exec chmod 0755 {} +
find /opt/muxia -type f -exec chmod go-w {} +

test -x "$EXPECTED_BROWSER"
install -o root -g root -m 0644 "$APPARMOR_SOURCE" "$APPARMOR_TARGET"
apparmor_parser -r "$APPARMOR_TARGET"

echo "MX050_HOST_PROVISION_PASS:$EXPECTED_BROWSER"
