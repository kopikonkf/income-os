# FA-318 Live Runtime Dependency-Closure Reconciliation — 2026-09-18

Status: **Closure PASS / Provider COMMITTED_UNRESOLVED**

The live H01 `/srv/die` tree is intentionally drifted and cannot be repaired with a blind pull/reset. A selective reconciliation was therefore performed for the FA-318 typed pre-generation runtime family after the production cycle failed because canonical `factory_orchestration_v2.py` imported a missing `pre_generation_contract.py`.

## Root cause

The live postproduction orchestrator and multi-cluster dispatcher already matched `origin/main`, but seven FA-318 prompt/compiler contracts were absent and three cognition files were stale. This created a partial-deployment version skew: the consumer code had been promoted without its dependency closure.

## Closure promoted

Exact bytes from `origin/main` were selectively deployed for:

- cognition receipt schema;
- canonical production cognition tick;
- cognition validator;
- production prompt policy;
- pre-generation contract;
- production prompt compiler;
- production preset registry;
- production preset, subject-spec, visual-requirement and compiled-prompt schemas.

Existing live asset-expression, blueprint, router and core schemas already matched canonical and were not rewritten.

The canonical `production_runtime_tick.py` was **not** wholesale copied because its current `main` version also contains later expression-ledger evolution beyond the FA-318 closure. Only the exactly-once committed-unresolved guard discovered during acceptance was patched minimally to the live-old runtime.

Rollback material is under:

`/var/lib/die/rollback/FA-318-runtime-closure/20260918T073922Z`

## Preflight

Using the production Factory Python environment:

- FA-318 policy loaded successfully;
- production preset registry validated with two presets;
- current postproduction orchestrator imported successfully;
- an isolated copy of `PRODSEED000138` proved the canonical legacy-resume path because the live card predates the typed sidecar deployment and has no pre-generation lock;
- canonical cognition tick on the actual card returned READY/idle under `--no-resume`;
- no provider call occurred during preflight.

Future cards now use the canonical FA-318 cognition path: Executive NO_VETO advances to typed Subject Spec, deterministic visual contract/provider prompt, then a hash-bound pre-generation lock before `BLUEPRINT_READY`.

## Same-card replay

The same durable card `PRODSEED000138` was replayed. No compensating seed and no semantic duplicate were created.

The runtime reached real provider dispatch:

- provider: Duck.ai;
- runtime: V1 Runtime 02;
- attempt: 1;
- dispatch committed: true;
- commit id: `206443d06d6195bd0e408c3700858d8e5ad085c1031371d963325569a9649206`.

Immediately after commit Duck.ai returned a human challenge. The attempt therefore ended:

- failure: `CHECKPOINT / E_HUMAN_CHALLENGE_REQUIRED`;
- `retry_allowed=false`;
- no provider-original bytes were acquired;
- postproduction did not start;
- browser runtime closed gracefully to COLD;
- CDP/control endpoint closed;
- profile process gone;
- lease released;
- no forced cleanup.

Automation did not bypass the challenge.

## Exactly-once hardening

The dispatcher already refuses any second provider dispatch when a prior provider attempt has `dispatch_committed=true`. During this incident the upper production tick was also hardened so a `BLUEPRINT_READY` card with a durable failed committed receipt is parked before the queue is touched.

The live verification result is:

```text
status=IDLE
reason=COMMITTED_UNRESOLVED
provider_call_performed=false
provider_id=duckai
failure_code=CHECKPOINT
retry_allowed=false
next_action=FOUNDER_RECONCILIATION_REQUIRED_NO_AUTOMATIC_REDISPATCH
```

The workspace still contains exactly one provider attempt.

## Current frontier

The dependency-closure incident is resolved. The remaining blocker for `PRODSEED000138` is external/manual reconciliation of the already-committed Duck.ai request. Automatic resubmission is forbidden. If the Founder clears the human challenge, reconciliation should inspect the existing committed request/output and acquire it if present; it must not send the generation prompt a second time.
