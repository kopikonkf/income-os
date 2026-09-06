#!/usr/bin/env bash
set -euo pipefail
RUNTIME_ROOT="${FA121_RUNTIME_ROOT:-/opt/factory-asset/fa121-runtime}"
STATE_ROOT="${FA121_STATE_ROOT:-/var/lib/factory-asset/fa121-stability}"
RUNNER="$RUNTIME_ROOT/company/factory-asset/bin/run_fa121_stability_canary.mjs"
LOCK="$STATE_ROOT/tick.lock"
mkdir -p "$STATE_ROOT"
set +e
/usr/sbin/runuser -u kopiko -- /usr/bin/flock -E 75 -n "$LOCK" /usr/local/bin/node "$RUNNER" tick --repo-root "$RUNTIME_ROOT" --state-root "$STATE_ROOT"
rc=$?
set -e
if [[ $rc -eq 75 ]]; then
  exit 0
fi
if [[ -f "$STATE_ROOT/CLOSE_RUNTIME" ]]; then
  /usr/bin/systemctl disable --now die-fa121-stability.timer >/dev/null 2>&1 || true
  /usr/bin/systemctl stop die-fa121-cluster-broker.service >/dev/null 2>&1 || true
fi
exit "$rc"
