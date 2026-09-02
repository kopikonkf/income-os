#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 /srv/die/company/die-agents/hermes/production-runtime/production_runtime_tick.py "$@"
