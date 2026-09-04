# Factory v2 Linux Runtime Activation and Cognition Recovery

Task: `FA-140A`
Status: PASS (engineering); live activation receipt is completed after merge/deploy.
Date: 2026-09-04

This closes two production-stall classes discovered on `PRODSEED000025`:

1. **Cognition immutable drift.** A request path has a stable semantic identity, but canon/thread context can advance before transport. If a request has no response and no principal transport receipt, the stale request is archived under `outbox/superseded/` and replaced atomically. Once response or transport evidence exists, the original request remains authoritative and is reused; identity drift still fails closed.
2. **Python runtime mismatch.** `production_runtime_tick.sh` now requires a dedicated Factory runtime Python at `/opt/die/factory-asset/venv/bin/python`. The environment is built from pinned `requirements-runtime.txt` using `prepare_runtime_venv.py` and import-smoked before use.

Unresolved rights evidence is a parked human gate rather than a global throughput blocker. The external card state becomes `WAITING_FOUNDER_RIGHTS_REVIEW`. It becomes actionable again only when `rights-observation.json` is complete and bound to the exact `active_master_sha256`; the FA-136 gate still decides PASS/REVIEW/BLOCK and no human clearance is fabricated.
## Cognition browser transport versioning

Browser recovery markers are fingerprinted from stable request context (excluding created/expires timestamps). A stale prior version of the same logical request cannot masquerade as the current request. If the prior version is still generating, only that stale generation is stopped before the new version is submitted. Legacy unversioned markers remain recoverable when their prompt is byte-identical to the active request.

## Sealed context fallback and cron snapshot shim

Routine production cognition attempts Runtime MCP first. Connector/account unavailability alone may fall back to the exact sealed Hermes envelope; observed mismatches still fail closed. Context-convergence retries receive a new logical review request attempt so an already-delivered blocked response remains immutable. The Hermes production cron snapshot is a stable shim into the repository wrapper, preventing stale interpreter/dependency behavior after future fast-forward deployments.
