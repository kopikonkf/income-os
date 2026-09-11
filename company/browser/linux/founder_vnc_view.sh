#!/usr/bin/env bash
set -euo pipefail
cluster=''; display=''; port=''; mode='read-only'
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-id) cluster="$2"; shift 2;;
    --display) display="$2"; shift 2;;
    --port) port="$2"; shift 2;;
    --mode) mode="$2"; shift 2;;
    *) echo "E_ARG:$1" >&2; exit 2;;
  esac
done
[[ "$cluster" =~ ^cluster-[ab]$ ]] || { echo E_CLUSTER >&2; exit 2; }
[[ "$display" =~ ^10[12]$ ]] || { echo E_DISPLAY >&2; exit 2; }
[[ "$port" =~ ^59[12][0-9]{2}$ ]] || { echo E_PORT >&2; exit 2; }
[[ "$mode" == read-only || "$mode" == interactive ]] || { echo E_MODE >&2; exit 2; }
pid="$(pgrep -f "^Xvfb :${display} " | head -1 || true)"
[[ -n "$pid" && -r "/proc/$pid/cmdline" ]] || { echo E_XVFB_OWNER_NOT_FOUND >&2; exit 3; }
mapfile -d '' argv < "/proc/$pid/cmdline"
auth=''
for ((i=0;i<${#argv[@]};i++)); do
  if [[ "${argv[$i]}" == '-auth' && $((i+1)) -lt ${#argv[@]} ]]; then auth="${argv[$((i+1))]}"; break; fi
done
[[ -n "$auth" && -r "$auth" ]] || { echo E_XAUTHORITY_NOT_FOUND >&2; exit 3; }
args=(-display ":$display" -auth "$auth" -localhost -rfbport "$port" -forever -shared -noxdamage -repeat -nopw -quiet)
[[ "$mode" == read-only ]] && args+=(-viewonly)
exec /usr/bin/x11vnc "${args[@]}"
