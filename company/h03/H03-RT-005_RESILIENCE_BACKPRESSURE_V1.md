# H03-RT-005 — Worker Retry, Backpressure, Fallback + Anti-Stall v1

Status: DONE / PASS
Date: 2026-09-09

Worker failures are typed as AUTH, RATE_LIMIT, PROVIDER, PROFILE, RUNTIME, OUTPUT or POLICY. Retry is bounded by Work Card attempts. Eligible alternatives produce `FALLBACK_ALTERNATE_WORKER`; auth/rate/provider/profile failures can circuit-break the unhealthy slot. Auth without an alternative waits for capability recovery rather than silently looping. Policy rejection and exhausted attempts fail terminally.

Queue depth at the configured limit exposes `PAUSE_NEW_DISPATCH` backpressure instead of accepting invisible backlog growth.

Artifacts: `company/h03/contracts/worker-resilience-policy.v1.schema.json` and `company/h03/lib/resilience_policy.py`.
