#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo E_ROOT_REQUIRED >&2; exit 2; }
ROOT="${DIE_HOME:-/srv/die}"
for f in company/browser/linux/job_scoped_cluster_runtime.mjs company/browser/linux/principal_job_browser_runtime.mjs company/browser/linux/founder_no_cdp_repair.sh company/factory-asset/bin/production_multi_cluster_dispatch.mjs; do
  [[ -f "$ROOT/$f" ]] || { echo "E_FA338_SOURCE:$f" >&2; exit 2; }
done
install -m 0755 "$ROOT/company/browser/linux/founder_no_cdp_repair.sh" /usr/local/bin/die-founder-no-cdp-repair
# Retain historical units for bounded rollback, but remove them from the active boot/runtime graph.
for unit in die-fa121-stability.timer die-fa121-cluster-broker.service die-muxia-cluster-a-browser.service die-muxia-cluster-b.service die-muxia-cluster-b-browser.service; do
  systemctl disable --now "$unit" >/dev/null 2>&1 || true
done
systemctl daemon-reload
for port in 39121 39122 39221 39222; do
  if ss -ltnH | awk '{print $4}' | grep -Eq "(^|:)${port}$"; then echo "E_FA338_LEGACY_PORT:$port" >&2; exit 3; fi
done
for profile in /var/lib/muxia/profiles/chatgpt-linux-a/browser /var/lib/muxia/profiles/web-ai-cluster-b/browser; do
  if ps -eo args= | grep -F -- "--user-data-dir=$profile" | grep -E 'chrome|chromium|brave' >/dev/null; then echo "E_FA338_LEGACY_PROFILE_OWNER:$profile" >&2; exit 3; fi
done
systemctl enable die-muxia-dispatch.service >/dev/null 2>&1 || true
systemctl restart die-muxia-dispatch.service
printf '%s\n' 'FA338_CUTOVER=PASS' 'OWNER_MODEL=JOB_SCOPED_HEADFUL_BROWSER_CDP' 'LEGACY_OWNER_UNITS=DISABLED_ROLLBACK_RETAINED' 'IDLE_BROWSER_OWNERS=0'
