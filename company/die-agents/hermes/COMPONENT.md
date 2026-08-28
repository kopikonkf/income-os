# Hermes - Component Ownership

Status: `LINUX_IMPLEMENTATION_READY`
Migration task: `DIE-202`

Hermes remains the operational orchestrator and anti-macet layer. It delegates bounded jobs through the Worker Contract; it does not become Worker-001 and does not call MUXIA as an authority bypass.

Canonical source references:
- `company/die-agents/hermes/SOUL.md`
- `company/die-agents/hermes/AGENTS.md`
- `company/die-agents/hermes/worker_dispatch.py`
- `company/die-agents/hermes/linux/`
- `bin/die_operator_tick.py`
- `bin/die_operator_switch.py`
- `bin/die_platform_receipt.py`
- `bridge/income_os_bridge/`

Linux rebuild uses clean upstream Hermes provenance and a fresh HERMES_HOME. Windows AppData profile, auth.json, .env, sessions, state.db, caches, and dirty Hermes source tree are not copied.
