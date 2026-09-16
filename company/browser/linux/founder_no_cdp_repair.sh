#!/usr/bin/env bash
set -euo pipefail
principal="${1:-}"; url="${2:-https://chatgpt.com/}"
case "$principal" in
  executive) profile=/var/lib/die/executive/browser-profile; klass=DIE-Executive-AuthRepair ;;
  division01) profile=/var/lib/die/division01/browser-profile; klass=DIE-Division01-AuthRepair ;;
  cluster-a) profile=/var/lib/muxia/profiles/chatgpt-linux-a/browser; klass=DIE-V1-Runtime01-AuthRepair ;;
  cluster-b) profile=/var/lib/muxia/profiles/web-ai-cluster-b/browser; klass=DIE-V1-Runtime02-AuthRepair ;;
  *) echo 'usage: founder_no_cdp_repair.sh executive|division01|cluster-a|cluster-b [url]' >&2; exit 64 ;;
esac
[[ -d "$profile" ]] || { echo E_REPAIR_PROFILE >&2; exit 66; }
ps -eo args= | grep -F -- "--user-data-dir=$profile" | grep -E 'chrome|chromium|brave' >/dev/null && { echo E_REPAIR_PROFILE_BUSY >&2; exit 73; }
export DISPLAY="${DISPLAY:-:12.0}"
export XAUTHORITY="${XAUTHORITY:-/home/kopiko/.Xauthority}"
echo "FOUNDER_NO_CDP_REPAIR principal=$principal profile=$profile display=$DISPLAY" >&2
exec /usr/bin/google-chrome-stable --user-data-dir="$profile" --no-first-run --no-default-browser-check --disable-background-mode --class="$klass" "$url"
