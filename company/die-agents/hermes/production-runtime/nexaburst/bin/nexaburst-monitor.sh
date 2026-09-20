#!/usr/bin/env bash
set -euo pipefail
ROOT=/var/lib/die/h01/nexaburst
STATE=$ROOT/state
prev_total=0
prev_idle=0
while true; do
  read -r cpu user nice system idle iowait irq softirq steal _ < /proc/stat
  total=$((user+nice+system+idle+iowait+irq+softirq+steal))
  idle_all=$((idle+iowait))
  if (( prev_total > 0 )); then
    dt=$((total-prev_total)); di=$((idle_all-prev_idle))
    if (( dt > 0 )); then cpu_pct=$((100*(dt-di)/dt)); else cpu_pct=0; fi
  else cpu_pct=0; fi
  prev_total=$total; prev_idle=$idle_all
  mem_line=$(free -m | awk '/^Mem:/ {printf "%d / %d MiB (%.0f%%)", $3,$2,100*$3/$2}')
  swap_line=$(free -m | awk '/^Swap:/ {if ($2>0) printf "%d / %d MiB", $3,$2; else printf "0 MiB"}')
  disk_line=$(df -h "$ROOT" | awk 'NR==2 {printf "%s used / %s total, %s free", $3,$2,$4}')
  load_line=$(awk '{print $1" "$2" "$3}' /proc/loadavg)
  phase=$(pgrep -f 'nexaburst-phase1-runner.py' >/dev/null && echo RUNNING || echo IDLE)
  v2=$(pgrep -f 'nexaburst-v2-worker.py --continuous' >/dev/null && echo RUNNING || echo IDLE)
  up=$(uptime -p)
  clear
  printf 'NexaBurst H01 System Monitor\n'
  printf '============================\n'
  printf 'CPU        : %s%%  (%s cores)\n' "$cpu_pct" "$(nproc)"
  printf 'Load       : %s\n' "$load_line"
  printf 'RAM        : %s\n' "$mem_line"
  printf 'Swap       : %s\n' "$swap_line"
  printf 'Disk       : %s\n' "$disk_line"
  printf 'Phase-1    : %s\n' "$phase"
  printf 'V2 worker  : %s\n' "$v2"
  printf 'Uptime     : %s\n' "$up"
  printf '\nRefresh: 2s | Ctrl+C to close monitor\n'
  sleep 2
done
