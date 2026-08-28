# Hermes - Component Ownership

Status: `OWNERSHIP_BOUNDARY`
Migration task: `DIE-202`

No AppData/profile copy. Current identity/runtime sources remain referenced, not duplicated.

Canonical source references:
- `IDENTITY/hermes-operator/SOUL.md`
- `IDENTITY/hermes-operator/AGENTS.md`
- `bin/die_operator_tick.py`
- `bin/die_operator_switch.py`
- `bridge/income_os_bridge/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
