# Architect - Component Ownership

Status: `LINUX_STAGING_AUTHORIZED`
Migration task: `MX-053`

Founder amendment 2026-09-08 authorizes Linux-native Architect MCP coexistence staging under MX-053 after MCP-LNX-005, while the Windows Architect MCP remains active as rollback/control. CUT-006 remains the only control-channel handoff and is gated by both MX-054 and CUT-005.

Canonical source references:
- `D:\mcp-architect`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
