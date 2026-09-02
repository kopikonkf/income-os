# Submission Authority, Credential and Session Boundary v1

## Scope

`SUB-001B` defines the authority and session boundary between an immutable `SUB-001A` package and any later submission transport. It does not submit. It does not publish. It does not log in, read credentials, export cookies/tokens, or create marketplace side effects.

The default is fail-closed: package existence never implies authority. An irreversible submission may advance beyond `PREPARED` only when an exact package/route/platform-profile combination has an explicit Founder authority receipt with decision `AUTHORIZE_SUBMISSION`.

## Explicit Founder authority

Schema:

`company/schemas/die.asset.submission-authority.v1.schema.json`

An authority receipt pins:

- exact submission-package SHA-256;
- exact route identity;
- exact platform-profile SHA-256;
- explicit `AUTHORIZE_SUBMISSION` or `DENY_SUBMISSION` decision;
- `FOUNDER_EXPLICIT` authority class;
- issued time and optional expiry;
- platform scope;
- single-attempt scope.

Authorization is package-locked and route-locked. It cannot be inferred from QA/QC PASS, package presence, an existing browser session, an operator role, or a previous authorization for another package/route.

## Credential and session boundary

Schema:

`company/schemas/die.asset.submission-session-boundary.v1.schema.json`

Credentials remain external to DIE submission artifacts. The contract records only non-secret session readiness and an optional opaque profile reference. It explicitly forbids:

- embedding credentials in submission packages or authority receipts;
- logging credential material;
- extracting cookies or tokens;
- bypassing browser/OS credential protection;
- implicit delegation from session availability;
- treating an authenticated session as submission authority.

Supported session modes are deliberately bounded to an externally established interactive session or an external browser-profile session. An expired or missing session may be recreated interactively; no secret recovery/extraction path is defined.

## Separation of concerns

`SUB-001A` answers: **what exact bytes/evidence are prepared?**

`SUB-001B` answers: **is there explicit Founder permission for this exact route, and is a non-secret external session boundary available?**

Later tasks answer idempotency/reconciliation and platform-specific transport. This task alone performs no external marketplace action.

## Fail-closed rules

A downstream consumer must stop when:

- the authority receipt is absent for an authority-bearing transition;
- the authority decision is not `AUTHORIZE_SUBMISSION`;
- package, route, or platform-profile pins differ;
- authority is expired;
- a second submission attempt is requested under a single-attempt receipt;
- credential material appears in a DIE submission artifact;
- cookie/token extraction or protection bypass would be required;
- session state is `UNAVAILABLE`, `EXPIRED`, or `REAUTH_REQUIRED` and the transport requires an authenticated session.

No condition above may be repaired by implicit delegation or blind retry.
