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
- `company/division/division001/engines/demand-score/CONTRACT_V1.md`
- `company/division/division001/engines/demand-score/DEMAND_SCORE_MODEL_V1.contract.json`
- `company/division/division001/engines/demand-score/die.division001.demand-score.v1.schema.json`
- `company/division/division001/engines/demand-score/score_demand.py`
- `company/division/division001/engines/demand-score/rank_demand.py`
- `company/division/division001/engines/demand-score/CALIBRATION_V1.md`
- `company/division/division001/engines/longtail/CONTRACT_V1.md`
- `company/division/division001/engines/longtail/MODIFIER_ONTOLOGY_V1.json`
- `company/division/division001/engines/longtail/retrieve_object_seeds.py`
- `company/division/division001/engines/longtail/retrieve_human_contexts.py`
- `company/division/division001/engines/longtail/ENGINE_V1.md`
- `company/division/division001/engines/longtail/generate_longtail.py`
- `company/division/division001/engines/longtail/guard_longtail.py`
- `company/division/division001/engines/longtail/phrase_signal_score.py`
- `company/division/division001/engines/longtail/longtail_registry.py`

DIE-103 rule: this ownership boundary does not authorize secret/profile/runtime-data copying or premature service cutover.

Opportunity Intelligence: `OE-001 = DONE`. The canonical engine includes source-shaped fixture adapters, strict receipt validation, and registry/dedupe/freshness behavior. No live source collection is implied; live adapters require separately approved acquisition profiles.

Demand Score: `OE-002 = DONE`. Deterministic scorer, versioned transforms/weights, calibration corpus, ranking/replay regression, explicit UNKNOWN/STALE handling, and legacy-prior rejection are canonical. Demand Score alone grants no production authority.

Longtail Engine: `OE-003 = DONE`. Bounded dynamic Object+Human hypotheses pass deterministic guardrails, child-specific OE-001/OE-002 evidence, separate idempotent persistence, and ACCEPTED+COMPLETE-only ranking. Parent demand inheritance and brute-force 10D expansion remain forbidden.
