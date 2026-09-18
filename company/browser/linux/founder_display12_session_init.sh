#!/usr/bin/env bash
set -euo pipefail
[[ "$(id -un)" == kopiko ]] || exit 0
export DISPLAY="${DISPLAY:-:12.0}"
for _ in $(seq 1 80); do
  if /usr/bin/xhost +SI:localuser:kopiko >/dev/null 2>&1; then break; fi
  sleep 0.25
done
for _ in $(seq 1 80); do
  if /usr/bin/wmctrl -d >/dev/null 2>&1; then
    /usr/bin/wmctrl -n 5
    exit 0
  fi
  sleep 0.25
done
exit 1
