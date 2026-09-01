# OpenCode Worker-001

Role: default general execution Worker V1.
Executor ID: `opencode`.
Owner/orchestrator: Hermes.

Model-backed Worker-001 execution is governed by `model-policy.v1.json` and `model_worker.py`: exact `opencode/muse-spark-1.2-contributor-free`, zero-USD only, no paid fallback, network allowlist, and bounded job workspace. Each execution uses a per-job OpenCode runtime HOME/session DB/evidence directory so interactive TUI and sibling jobs do not share mutable state.

Permanent boundaries: no Founder/Executive/Division/Architect authority inheritance; no credentials; no submission/publish/spend; no worker spawning; no writes outside the job workspace.


Parallelism is owned by Hermes, not Worker-001. `worker_pool.py` may run multiple isolated Worker-001 jobs concurrently while each Worker remains non-delegating.
