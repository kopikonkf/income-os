# Division01 - Component Ownership

Status: `LINUX_STAGED_WAITING_OPERATOR_AUTH`
Migration task: `DIE-201`

Linux Decision MCP is staged and healthy pre-cutover. D:\OAUTH remains explicitly not Division01. Fresh Linux browser profile requires manual operator login; Windows rollback remains active until CUT-004.

Canonical source references:
- `company/division/division001/IDENTITY.md`
- `bridge/income_os_bridge/runtime_mcp_server.py`
- `ops/windows/runtime-mcp/`
- `company/division/division001/linux/`
- `company/division/division001/engines/opportunity-signals/SIGNAL_TAXONOMY_V1.md`
- `company/division/division001/engines/opportunity-signals/ACQUISITION_CONTRACT_V1.md`
- `company/division/division001/engines/opportunity-signals/die.division001.opportunity-signals.v1.schema.json`
- `company/division/division001/engines/opportunity-signals/ENGINE_V1.md`
- `company/division/division001/engines/opportunity-signals/signal_registry.py`
- `company/division/division001/engines/opportunity-signals/adapters/`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.

Opportunity Intelligence: `OE-001 = DONE`. The canonical engine includes source-shaped fixture adapters, strict receipt validation, and registry/dedupe/freshness behavior. No live source collection is implied; live adapters require separately approved acquisition profiles.
