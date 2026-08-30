# Hermes - Component Ownership

Status: `LINUX_ACTIVE_VERIFIED`
Migration task: `DIE-202`

Hermes remains the operational orchestrator and anti-macet layer. It delegates bounded jobs through the Worker Contract; it does not become Worker-001 and does not call MUXIA as an authority bypass.

Canonical source references:
- `company/die-agents/hermes/SOUL.md`
- `company/die-agents/hermes/AGENTS.md`
- `company/die-agents/hermes/worker_dispatch.py`
- `company/die-agents/hermes/linux/`
- `bin/die_operator_tick.py`
- `bin/die_operator_prepare.py`
- `company/die-agents/hermes/operator-v2/`
- `bin/die_operator_switch.py`
- `bin/die_platform_receipt.py`
- `bridge/income_os_bridge/`

Linux rebuild uses clean upstream Hermes provenance and a fresh HERMES_HOME. Windows AppData profile, auth.json, .env, sessions, state.db, caches, and dirty Hermes source tree are not copied.

Operator v2 `OE-006 = DONE`: legacy Kanban cognition is quarantined; canonical prepare is OS-neutral; anti-macet routing is deterministic, deduplicated, authority-validated, and semantics-free. Hash-chained write-ahead dispatch claims recover routing state after restart/crash, suppress duplicate dispatch, persist follow-up counters, invalidate stale/forged cognition or Founder authority, and never let journal/Kanban metadata manufacture semantic progress.
