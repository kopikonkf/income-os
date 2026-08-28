# Executive - Component Ownership

Status: `LINUX_STAGED_WAITING_OPERATOR_AUTH`
Migration task: `DIE-200`

Linux Decision MCP is staged and healthy pre-cutover. Executive identity is now canonical under this component. Browser profile is fresh and currently requires operator login; Windows production/rollback remains active until CUT-004.

Canonical source references:
- `company/executive/IDENTITY.md`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `bridge/income_os_bridge/runtime_mcp_oauth.py`
- `ops/windows/runtime-mcp/`
- `company/executive/linux/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.
