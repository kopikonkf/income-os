# DIE H01 Marketplace Transport and Durable Submission Receipt v1

H01-136 defines the handoff boundary after local marketplace package
preparation. It is a provider-neutral, local/synthetic contract. It consumes
either an H01-134 `die.h01.marketplace-delivery-package.v1` manifest or an
H01-135 `die.h01.submission-ready-entry.v1` projection. It does not log in,
upload, submit, publish, spend, call a provider, or read credentials.

The canonical receipt schema is
`contracts/h01-marketplace-transport.v1.schema.json`; the implementation is
`engineering/marketplace_transport_contract.py`.

## Identity and duplicate policy

The implementation first validates package eligibility and action locks, then
normalizes the source to:

```text
source_kind, marketplace, semantic_asset_id,
sorted(path, sha256, bytes) file rows
```

`package_digest` is SHA-256 of that normalized content. The deterministic
`idempotency_key` is SHA-256 of the contract name, marketplace, semantic asset
ID, and package digest. Filesystem paths, manifest timestamps, and provider
names are not identity inputs. The `duplicate_scope_key` is SHA-256 of the
contract name, marketplace, and semantic asset ID.

The local receipt store applies both keys:

- same idempotency key: return the existing receipt without a second attempt;
- same duplicate scope with a different idempotency key: reject with
  `DUPLICATE_SCOPE_CONFLICT`;
- no matching keys: create one `PREPARED` receipt.

Receipt creation holds an exclusive local store lock across duplicate checks
and the durable write, so concurrent preparers cannot both win the same
marketplace/asset scope. Corrupt receipt files fail closed instead of being
skipped during duplicate discovery.

This is deliberately strict. A changed package for an already-scoped
marketplace/asset is not silently treated as a replacement; a future
replacement flow needs a separate Founder-authorized decision.

## State machine

```text
PREPARED ──synthetic dispatch──> DISPATCHING
DISPATCHING ──accepted──────────> REMOTE_ACCEPTED
DISPATCHING ──retryable error───> RETRYABLE_FAILED ──retry──> DISPATCHING
DISPATCHING ──terminal error─────> TERMINAL_FAILED
REMOTE_ACCEPTED ────────────────> MODERATION_PENDING
MODERATION_PENDING ──accepted───> ACCEPTED
MODERATION_PENDING ──rejected───> REJECTED
```

`ACCEPTED`, `REJECTED`, and `TERMINAL_FAILED` are immutable terminal states.
`DISPATCHING` is persisted before a synthetic outcome is recorded, allowing a
restart to resume the same attempt rather than create a new one.
Receipt timestamps are RFC 3339 values and cannot move backward relative to
the last durable update.

## Retry taxonomy

The bounded retry policy is two retries after the initial attempt (three
attempts maximum). Only these synthetic dispatch outcomes are retryable:

| Outcome | Classification | Backoff after attempt |
| --- | --- | --- |
| `TIMEOUT` | `TRANSIENT_TIMEOUT` | 120 seconds |
| `RATE_LIMITED` | `RATE_LIMITED` | 120 seconds |
| `TEMPORARY_UNAVAILABLE` | `TEMPORARY_UNAVAILABLE` | 120 seconds |
| `REMOTE_5XX` | `REMOTE_5XX` | 120 seconds |
| second retryable failure | same classification | 480 seconds |

`INVALID_PACKAGE`, `INELIGIBLE_PACKAGE`, `POLICY_REJECTED`,
`RIGHTS_REJECTED`, `AUTHORITY_REQUIRED`, and `REMOTE_DUPLICATE` are terminal
and are never retried. A third retryable failure becomes
`TERMINAL_FAILED` with `RETRIES_EXHAUSTED`. Backoff is recorded as
`next_retry_at`; the module does not sleep or schedule work.

## Receipt shape

Every receipt contains:

- deterministic `receipt_id`, `idempotency_key`, `duplicate_scope_key`, and
  normalized source hashes;
- append-only-in-place `state_history`, attempt count, retry classification,
  and explicit next retry time;
- `remote.remote_reference` and `moderation.moderation_reference` as opaque
  strings with no parsing or provider-specific semantics;
- moderation status `NOT_STARTED`, `PENDING`, `ACCEPTED`, or `REJECTED`, plus
  a bounded feedback taxonomy: `CONTENT_POLICY`, `METADATA_INVALID`,
  `RIGHTS_UNCLEAR`, `QUALITY_REVIEW`, `DUPLICATE_CONTENT`, `ACCOUNT_POLICY`,
  `PROVIDER_POLICY`, and `UNKNOWN_REJECTION`;
- each rejection feedback code is mapped to a bounded `learning_target`
  (`PACKAGE_POLICY`, `METADATA`, `RIGHTS`, `QUALITY`, `DISTINCTNESS`,
  `ACCOUNT`, `MARKETPLACE_POLICY`, or `HUMAN_REVIEW`) for later governed
  learning ingestion; this contract records the input but does not mutate any
  downstream model, skill, or economic state;
- authority and action locks. `founder_authorized`,
  `submission_authorized`, `publication_authorized`,
  `external_action_performed`, and `credential_accessed` are all `false`;
  login, upload, submission, publication, and spend are all `NONE`.

Opaque remote references are accepted only as caller-provided strings and are
never dereferenced. A synthetic `REMOTE_ACCEPTED` observation is evidence of a
local test transition only; it is not evidence that a real marketplace
accepted anything.

## Founder authority gates

Local preparation and synthetic observation are permitted as contract tests.
Any future external action requires a distinct Founder approval scoped to the
exact marketplace, semantic asset ID, package digest, and single attempt.
Approval cannot be inferred from `submission_eligible`, a remote-looking
string, a moderation status, or a previous receipt. H01-136 has no API that can
record or exercise that approval, and no external action is authorized by this
task.
