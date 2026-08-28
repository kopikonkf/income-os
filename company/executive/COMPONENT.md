# Executive - Component Ownership

Status: `OWNERSHIP_BOUNDARY`
Migration task: `DIE-200`

No duplicate copy of shared runtime source; current repo paths remain canonical until DIE-200 relocation/rebuild.

Canonical source references:
- `company/executive/IDENTITY.md`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `bridge/income_os_bridge/runtime_mcp_oauth.py`
- `ops/windows/runtime-mcp/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
