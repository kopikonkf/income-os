#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "MX050_REQUIRES_LINUX" >&2
  exit 20
fi

ROOT_DIR="${MUXIA_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export MUXIA_ROOT="${MUXIA_ROOT:-/var/lib/muxia}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/muxia/playwright-browsers}"

cd "$ROOT_DIR"

command -v node >/dev/null 2>&1 || { echo "NODE_REQUIRED" >&2; exit 21; }
command -v npm >/dev/null 2>&1 || { echo "NPM_REQUIRED" >&2; exit 22; }

NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
if (( NODE_MAJOR != 24 )); then
  echo "NODE_24_LTS_REQUIRED:found=${NODE_MAJOR}" >&2
  exit 23
fi

npm ci
sudo env "PATH=$PATH" "MUXIA_SOURCE_DIR=$ROOT_DIR" "PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH" /bin/bash ./scripts/linux/mx050-host-provision.sh
npm run build
node ./scripts/linux/mx050-runtime-smoke.mjs

echo "MX050_LINUX_BOOTSTRAP_PASS"
