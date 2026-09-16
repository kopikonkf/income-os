#!/bin/sh
# XRDP reconnect channel self-heal for persistent XFCE sessions.
# Restores cliprdr/rdpdr when xrdp reconnects to an older Xorg session whose
# chansrv process/socket stopped listening. Does not touch Xorg/XFCE.
set -eu
D="${DISPLAY:-}"
[ -n "$D" ] || exit 0
N="${D#:}"; N="${N%%.*}"
case "$N" in ''|*[!0-9]*) exit 0;; esac
SOCKROOT="${XRDP_SOCKET_PATH:-/run/xrdp/sockdir}"
SOCK="$SOCKROOT/xrdp_chansrv_socket_$N"
if ss -xl 2>/dev/null | grep -Fq "$SOCK"; then exit 0; fi
for p in $(pgrep -u "$(id -u)" -x xrdp-chansrv 2>/dev/null || true); do
  pd=$(cat "/proc/$p/environ" 2>/dev/null | tr '\0' '\n' | sed -n 's/^DISPLAY=//p' || true)
  [ "$pd" = "$D" ] || continue
  kill -TERM "$p" 2>/dev/null || true
done
sleep 0.2
rm -f "$SOCKROOT/xrdp_chansrv_socket_$N" "$SOCKROOT/xrdpapi_$N" 2>/dev/null || \
  sudo -n rm -f "$SOCKROOT/xrdp_chansrv_socket_$N" "$SOCKROOT/xrdpapi_$N" 2>/dev/null || true
export XRDP_SESSION="${XRDP_SESSION:-1}"
export XRDP_SOCKET_PATH="$SOCKROOT"
export XRDP_PULSE_SINK_SOCKET="${XRDP_PULSE_SINK_SOCKET:-xrdp_chansrv_audio_out_socket_$N}"
export XRDP_PULSE_SOURCE_SOCKET="${XRDP_PULSE_SOURCE_SOCKET:-xrdp_chansrv_audio_in_socket_$N}"
export PULSE_SCRIPT="${PULSE_SCRIPT:-/etc/xrdp/pulse/default.pa}"
nohup /usr/sbin/xrdp-chansrv >/dev/null 2>&1 &
exit 0