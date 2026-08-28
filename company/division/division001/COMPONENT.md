# Division01 - Component Ownership

Status: `LINUX_STAGED_WAITING_OPERATOR_AUTH`
Migration task: `DIE-201`

Linux Decision MCP is staged and healthy pre-cutover. D:\OAUTH remains explicitly not Division01. Fresh Linux browser profile requires manual operator login; Windows rollback remains active until CUT-004.

Canonical source references:
- `company/division/division001/IDENTITY.md`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `ops/windows/runtime-mcp/`
- `company/division/division001/linux/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
