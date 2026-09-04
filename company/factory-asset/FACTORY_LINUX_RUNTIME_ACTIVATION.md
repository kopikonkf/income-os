# Factory v2 Linux Runtime Activation and Cognition Recovery

Task: `FA-140A`
Status: PASS (engineering); live activation receipt is completed after merge/deploy.
Date: 2026-09-04

This closes two production-stall classes discovered on `PRODSEED000025`:

1. **Cognition immutable drift.** A request path has a stable semantic identity, but canon/thread context can advance before transport. If a request has no response and no principal transport receipt, the stale request is archived under `outbox/superseded/` and replaced atomically. Once response or transport evidence exists, the original request remains authoritative and is reused; identity drift still fails closed.
2. **Python runtime mismatch.** `production_runtime_tick.sh` now requires a dedicated Factory runtime Python at `/opt/die/factory-asset/venv/bin/python`. The environment is built from pinned `requirements-runtime.txt` using `prepare_runtime_venv.py` and import-smoked before use.

Unresolved rights evidence is a parked human gate rather than a global throughput blocker. The external card state becomes `WAITING_FOUNDER_RIGHTS_REVIEW`. It becomes actionable again only when `rights-observation.json` is complete and bound to the exact `active_master_sha256`; the FA-136 gate still decides PASS/REVIEW/BLOCK and no human clearance is fabricated.