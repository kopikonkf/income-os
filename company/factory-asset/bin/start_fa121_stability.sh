#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo E_FA121_START_REQUIRES_ROOT >&2
  exit 2
fi
RUNTIME_ROOT="${FA121_RUNTIME_ROOT:-/opt/factory-asset/fa121-runtime}"
STATE_ROOT="${FA121_STATE_ROOT:-/var/lib/factory-asset/fa121-stability}"
RUNNER="$RUNTIME_ROOT/company/factory-asset/bin/run_fa121_stability_canary.mjs"
REVISION_FILE="$RUNTIME_ROOT/REVISION"
[[ -x /usr/local/sbin/die-fa121-stability-tick ]] || { echo E_FA121_NOT_INSTALLED >&2; exit 2; }
[[ -f "$RUNNER" && -f "$REVISION_FILE" ]] || { echo E_FA121_RUNTIME_MISSING >&2; exit 2; }
if [[ -f "$STATE_ROOT/state.json" ]]; then
  /usr/sbin/runuser -u kopiko -- /usr/local/bin/node "$RUNNER" status --repo-root "$RUNTIME_ROOT" --state-root "$STATE_ROOT"
  exit 0
fi
systemctl start die-fa121-cluster-broker.service
ready=0
for _ in $(seq 1 30); do
  if /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:39121/v1/status >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[[ $ready -eq 1 ]] || { systemctl status --no-pager die-fa121-cluster-broker.service >&2 || true; echo E_FA121_BROKER_START >&2; exit 2; }
REVISION="$(tr -d '\r\n' < "$REVISION_FILE")"
/usr/sbin/runuser -u kopiko -- /usr/local/bin/node "$RUNNER" init --repo-root "$RUNTIME_ROOT" --state-root "$STATE_ROOT" --repo-revision "$REVISION"
systemctl enable --now die-fa121-stability.timer
systemctl start --no-block die-fa121-stability-tick.service
/usr/sbin/runuser -u kopiko -- /usr/local/bin/node "$RUNNER" status --repo-root "$RUNTIME_ROOT" --state-root "$STATE_ROOT"
