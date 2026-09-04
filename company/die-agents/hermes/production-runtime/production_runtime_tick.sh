#!/usr/bin/env bash
set -euo pipefail
FACTORY_PYTHON="${FACTORY_PYTHON:-/opt/die/factory-asset/venv/bin/python}"
[[ -x "$FACTORY_PYTHON" ]] || { echo "E_FACTORY_RUNTIME_PYTHON:$FACTORY_PYTHON" >&2; exit 2; }
exec "$FACTORY_PYTHON" /srv/die/company/die-agents/hermes/production-runtime/production_runtime_tick.py "$@"
