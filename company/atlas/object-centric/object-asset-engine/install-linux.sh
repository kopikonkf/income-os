#!/usr/bin/env bash
set -euo pipefail
DIE_CONFIG_ROOT="${DIE_CONFIG_ROOT:-/etc/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
ENGINE_ROOT="${DIE_OBJECT_ENGINE_ROOT:-$DIE_STATE_ROOT/atlas/object-asset-engine}"
CONFIG_DIR="$DIE_CONFIG_ROOT/object-asset-engine"
SOURCE_ROOT="${DIE_HOME:-/srv/die}/company/atlas/object-centric/object-asset-engine"
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then echo E_ROOT_REQUIRED >&2; exit 2; fi
getent group die-runtime >/dev/null || groupadd --system die-runtime
install -d -o root -g die-runtime -m 2770 "$ENGINE_ROOT" "$ENGINE_ROOT/db" "$ENGINE_ROOT/data" "$ENGINE_ROOT/outputs" "$ENGINE_ROOT/reports" "$ENGINE_ROOT/state"
install -d -o root -g root -m 0755 "$CONFIG_DIR"
install -o root -g root -m 0644 "$SOURCE_ROOT/config.linux.v1.json" "$CONFIG_DIR/config.json"
cat > "$CONFIG_DIR/runtime.env" <<EOF
DIE_OBJECT_ENGINE_ROOT=$ENGINE_ROOT
# Optional audit credential path. Configure later under /etc/die; never copy Windows makan.txt.
# DIE_OBJECT_ENGINE_GEMINI_KEY_FILE=/etc/die/object-asset-engine/gemini-keys.txt
EOF
chown root:root "$CONFIG_DIR/runtime.env"
chmod 0600 "$CONFIG_DIR/runtime.env"
python3 - <<'PY'
from pathlib import Path
import os,sqlite3
root=Path(os.environ.get('DIE_OBJECT_ENGINE_ROOT','/var/lib/die/atlas/object-asset-engine'))
for name in ['object_asset_engine.db','seed_library.db']:
    p=root/'db'/name
    if not p.is_file(): raise SystemExit('DB_MISSING:'+name)
    with sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True) as c:
        q=c.execute('PRAGMA quick_check').fetchone()[0]
        if q!='ok': raise SystemExit('DB_QUICK_CHECK_FAILED:'+name+':'+str(q))
print('OBJECT_ENGINE_DB_CHECK=PASS')
PY
echo OBJECT_ENGINE_INSTALL=PASS
echo ENGINE_ROOT=$ENGINE_ROOT
echo SERVICE_STARTED=NO
echo WINDOWS_CREDENTIAL_COPIED=NO
