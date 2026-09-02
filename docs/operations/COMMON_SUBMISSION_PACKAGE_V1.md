# Common Submission Package v1

## Scope

`SUB-001A` establishes the immutable packaging contract between a QA/QC-approved asset and future marketplace-specific submission adapters. It is deliberately packaging-only: it does not submit, does not publish, and does not read or embed marketplace credentials.

The contract pins the exact delivery artifact plus the exact QA receipt, QC receipt, Blueprint, metadata payload, and dated platform profile by SHA-256. Once sealed, package bytes are immutable; any semantic or binary change requires a new package identity and hash.

Founder authority remains external to this contract. `PREPARED` is not authorization. A later authority receipt is required before any route may advance to `AUTHORIZED`, and this task grants no marketplace action capability.

## Package contract

Schema:

`company/schemas/die.asset.submission-package.v1.schema.json`

Required provenance pins:

- artifact SHA-256;
- QA receipt SHA-256;
- QC receipt SHA-256;
- Blueprint SHA-256;
- metadata SHA-256;
- platform-profile SHA-256;
- route identity.

The package authority boundary is fixed to:

- `submission_authorized = false`;
- `publication_authorized = false`;
- `credentials_embedded = false`;
- `mutable_after_seal = false`.

## Route-state contract

Schema:

`company/schemas/die.asset.submission-route-state.v1.schema.json`

Canonical lifecycle states are distinct and must never be collapsed into a generic "published" boolean:

`PREPARED -> AUTHORIZED -> SUBMITTED -> REVIEW_PENDING -> APPROVED | REJECTED -> RECONCILED`

`PREPARED` means only that a package is structurally complete and hash-pinned. `AUTHORIZED` requires an external authorization receipt. `SUBMITTED` and later states require evidence from the future submission engine/platform adapter. This schema itself performs no external action.

## Authority and credential boundary

This component:

- does not submit;
- does not publish;
- does not log in to a marketplace;
- does not read or embed marketplace credentials;
- does not infer Founder authorization;
- does not retry or reconcile external actions;
- does not implement platform-specific transport.

Those concerns remain downstream under `SUB-001B` and later tasks.

## Failure semantics

A consumer must fail closed when any required hash is absent or malformed, when the package is not `PREPARED` at creation, or when a route claims an authority-bearing state without the required authorization receipt reference. No downstream adapter may treat package existence as submission permission.
