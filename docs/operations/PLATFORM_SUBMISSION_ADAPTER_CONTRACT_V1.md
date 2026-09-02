# Platform Submission Adapter Contract v1

SUB-001E defines the common marketplace adapter boundary. Every adapter MUST declare exactly one execution mode: `AUTOMATED_ALLOWED`, `OPERATOR_REQUIRED`, `OFFICIAL_API_ONLY`, or `BLOCKED_POLICY_UNKNOWN`.

The common interface exposes four semantics: `prepare`, `submit`, `reconcile`, and `receipt`. `prepare`, `reconcile`, and `receipt` may be implemented without external submission. `submit` is always an external action and always requires explicit Founder authority plus the separately governed credential/session boundary from SUB-001B.

Execution policy is monotonic and fail-closed. `BLOCKED_POLICY_UNKNOWN` forbids submission. `OPERATOR_REQUIRED` permits preparation and an operator handoff but the adapter itself may not submit. `OFFICIAL_API_ONLY` rejects browser/private-endpoint execution and permits a future submission path only through a verified official API. `AUTOMATED_ALLOWED` means platform policy permits automation; it does not itself grant Founder authority or prove credentials/session readiness.

An adapter may tighten a platform policy but must never weaken it. Credentials remain external and recreated; no cookie/token extraction or embedding is part of this contract. Reconciliation must precede ambiguous retry according to SUB-001C. Receipt semantics must preserve exact package/route/idempotency lineage. This task defines contract only: no marketplace login, submission, publication, credential access, or account action is performed.
