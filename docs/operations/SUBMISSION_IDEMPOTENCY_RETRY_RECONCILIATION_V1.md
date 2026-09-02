# Submission Idempotency, Retry, and Reconciliation Core v1

`SUB-001C` is a pure decision boundary. It never logs in, submits, publishes, reads credentials, or grants authority.

## Invariants

- Exact `package_sha256 + route_id` produces one stable idempotency key across every retry.
- Replaying an already-recorded attempt is `NOOP_DUPLICATE`.
- Attempt counters may advance by exactly one only; gaps fail closed.
- The immutable package/route scope must match before any attempt is mechanically eligible.
- A first attempt is mechanically eligible only while route state is `AUTHORIZED`; Founder authority from SUB-001B remains separately required.
- Every retry is reconciliation-first. `NOT_CHECKED`, `AMBIGUOUS`, and `UNREACHABLE` external state return `STOP_REVIEW` rather than blindly repeating submission.
- If the marketplace already shows submitted/review/approved/rejected state, the core returns `RECONCILE_NO_SUBMIT`.
- A retry becomes mechanically eligible only after a positive external observation of `NOT_FOUND`.
- `SUBMITTED`, `REVIEW_PENDING`, `APPROVED`, `REJECTED`, or `RECONCILED` internal routes never permit a repeat action; they reconcile instead.
- Every decision keeps `submission_action_authorized = false`. Mechanical retry eligibility is not submission authority.

## Separation of responsibilities

`SUB-001A` pins immutable package and route identity. `SUB-001B` defines Founder authority plus external credential/session boundaries. `SUB-001C` only decides whether an exact attempt is a duplicate, needs reconciliation/review, or is mechanically eligible. Marketplace adapters and actual submission remain downstream and separately governed.
