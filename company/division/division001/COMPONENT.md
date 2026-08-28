# Division01 - Component Ownership

Status: `OWNERSHIP_BOUNDARY`
Migration task: `DIE-201`

D:\OAUTH is explicitly not Division01.

Canonical source references:
- `company/division/division001/IDENTITY.md`
- `bin/wake_division01.py`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `ops/windows/runtime-mcp/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
