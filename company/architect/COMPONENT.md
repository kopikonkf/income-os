# Architect - Component Ownership

Status: `LINUX_STAGING_LIVE`
Migration task: `MX-053`

MX-053 is DONE/PASS. H01 now runs Linux-native Architect MCP v0.2.0 as a loopback-only local executor staging service (`holding_id=H01`, `runtime_id=architect-h01-linux`, `principal_id=chatgpt-architect`) from the single canonical `mcp-architect` codebase. Windows Architect MCP remains active as rollback/control. No public ingress or ChatGPT connector handoff is authorized here; CUT-006 remains the only control-channel handoff and is gated by both MX-054 and CUT-005.

Canonical source references:
- repository: `github.com/kopikonkf/mcp-architect`
- Windows rollback checkout: `D:\mcp-architect`
- H01 Linux checkout: `/srv/mcp-architect` at accepted SHA `1c3cd96847f94624a4c470291247798d4e31bfba`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
