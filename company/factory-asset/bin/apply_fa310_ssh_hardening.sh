#!/usr/bin/env bash
set -euo pipefail
MODE=${1:-}
SRC=${FA310_CONFIG_SRC:-/srv/die/company/factory-asset/config/sshd/40-die-management-hardening.conf}
DST=/etc/ssh/sshd_config.d/40-die-management-hardening.conf
STATE=/var/lib/die/state/fa310-management-ingress
BACKUP=$STATE/40-die-management-hardening.conf.before
ROLLBACK=$STATE/rollback.sh
mkdir -p "$STATE"
case "$MODE" in
 apply)
   [[ $EUID -eq 0 ]] || { echo E_ROOT >&2; exit 2; }
   test -f "$SRC" || { echo E_SOURCE >&2; exit 2; }
   if [[ -f "$DST" ]]; then cp -a "$DST" "$BACKUP"; else : > "$BACKUP.absent"; fi
   cp "$SRC" "$DST"; chmod 0644 "$DST"
   cat > "$ROLLBACK" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
DST=/etc/ssh/sshd_config.d/40-die-management-hardening.conf
STATE=/var/lib/die/state/fa310-management-ingress
if [[ -f "$STATE/40-die-management-hardening.conf.before" ]]; then cp -a "$STATE/40-die-management-hardening.conf.before" "$DST"; else rm -f "$DST"; fi
/usr/sbin/sshd -t && systemctl reload ssh
printf '%s\n' "$(date -u +%FT%TZ) AUTO_ROLLBACK_EXECUTED" >> "$STATE/rollback.log"
EOF
   chmod 0700 "$ROLLBACK"
   /usr/sbin/sshd -t
   systemd-run --quiet --unit=fa310-ssh-rollback --on-active=3m "$ROLLBACK"
   systemctl reload ssh
   echo APPLIED_ROLLBACK_ARMED
   ;;
 commit)
   [[ $EUID -eq 0 ]] || { echo E_ROOT >&2; exit 2; }
   /usr/sbin/sshd -t
   systemctl stop fa310-ssh-rollback.timer >/dev/null 2>&1 || true
   systemctl reset-failed fa310-ssh-rollback.service >/dev/null 2>&1 || true
   date -u +%FT%TZ > "$STATE/committed-at.txt"
   echo COMMITTED
   ;;
 rollback)
   [[ $EUID -eq 0 ]] || { echo E_ROOT >&2; exit 2; }
   exec "$ROLLBACK"
   ;;
 *) echo 'usage: apply_fa310_ssh_hardening.sh apply|commit|rollback' >&2; exit 2;;
esac
