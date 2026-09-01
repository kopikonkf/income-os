# Workers - Component Ownership

Status: `LINUX_IMPLEMENTATION_READY`
Migration task: `DIE-202`

`Worker` is the bounded executor role. `OpenCode CLI` is Worker-001 and the default general execution worker V1. Hermes is the orchestrator; MUXIA is the browser/provider/job/artifact infrastructure; Architect MCP is not a worker.

Canonical source references:
- `company/workers/contract/IDENTITY.md`
- `company/workers/contract/WORKER_CONTRACT_V0.md`
- `company/workers/contract/worker-job-envelope.v1.schema.json`
- `company/workers/contract/worker-result-envelope.v1.schema.json`
- `company/workers/opencode/`

Runtime roots:
- install: `/opt/die/workers/opencode`
- mutable home: `/var/lib/die/workers/opencode`
- job workspaces: `/var/lib/die/workspaces`

No Windows OpenCode config/provider credential is copied by DIE-202.


## Bounded concurrency

Hermes may dispatch independent Worker-001 jobs through `company/die-agents/hermes/worker_pool.py`. V1 defaults to four concurrent jobs with a hard ceiling of four. Each job has an isolated workspace/runtime HOME/evidence directory; Worker processes cannot spawn workers.
