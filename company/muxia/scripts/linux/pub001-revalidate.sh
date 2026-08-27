#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "PUB001_REQUIRES_LINUX" >&2
  exit 20
fi

ROOT_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export MUXIA_ROOT="${MUXIA_ROOT:-/var/lib/muxia}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/muxia/playwright-browsers}"

cd "$ROOT_DIR"

test -d "$MUXIA_ROOT" || { echo "MUXIA_ROOT_MISSING:$MUXIA_ROOT" >&2; exit 21; }
test -d "$PLAYWRIGHT_BROWSERS_PATH" || { echo "PLAYWRIGHT_BROWSERS_PATH_MISSING:$PLAYWRIGHT_BROWSERS_PATH" >&2; exit 22; }

NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
if (( NODE_MAJOR != 24 )); then
  echo "NODE_24_LTS_REQUIRED:found=${NODE_MAJOR}" >&2
  exit 23
fi

npm run build
npm run test:core
npm run test:parity

echo "PUB001_LINUX_REVALIDATION_PASS"
