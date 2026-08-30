# MUXIA Sanitized Observability and Fault Injection v1

Date: 2026-08-30
Status: `MX-060 DONE / MX-061 DONE / MX-062 READY`

## Scope

This batch establishes the reliability gates that must exist before the real 24-hour non-production soak. It adds no provider authority, credential handling, submission path, spend, or production cutover.

## Sanitized health contract

`buildSanitizedHealthSnapshot` exposes only bounded operational fields:

- provider ID, adapter version, capability names and health state;
- profile ID/provider/state, boolean lease activity, abstract process health, timestamps, failure count and diagnostic codes;
- job ID/provider/capability/profile selector, state, attempt, abstract artifact health and diagnostic codes;
- aggregate counts and `HEALTHY | DEGRADED | BLOCKED` grade.

The surface deliberately omits profile paths, artifact paths, lease owner values, browser PIDs, raw exceptions, request/response bodies and provider session state. Artifact failures are reduced to stable error codes. Rows are sorted by stable IDs so repeated observations of unchanged state are deterministic.

`sanitizeLogEvent` recursively redacts credential-equivalent keys and credential-shaped string values, bounds string length and nesting depth, handles circular values, and turns errors into name plus diagnostic code. It never serializes an error stack or raw error detail.

## Fault disposition contract

| Injected fault | Job state | Profile state | Recovery | Escalation |
| --- | --- | --- | --- | --- |
| timeout | `TIMED_OUT` | `READY` after lease release | bounded requeue | operator after retry limit |
| browser crash | `FAILED` | `READY` after crash recovery | release dead assignment lease | quarantine on ambiguous owner |
| lease contention | `BLOCKED` | unchanged | retry after current owner release | quarantine on ambiguous owner |
| disk/artifact failure | `FAILED` | unchanged | repair storage then bounded requeue | operator storage repair |
| authentication required | `WAITING_OPERATOR` | `AUTH_REQUIRED` with process/lease cleared | operator reauthentication then requeue | operator authentication required |

Every disposition pins `successAllowed=false`. The suite exercises the real registries/state machine and proves that a missing/corrupt artifact cannot become `SUCCEEDED`. Invalid job transitions are rejected before artifact lookup, preserving deterministic fault diagnosis.

## Auth-required durability rule

`ProfileRegistry.requireAuthentication` verifies both the persisted lease record and current registry owner, transitions through the canonical profile state graph, clears the process and logical owner, increments failure count, writes the profile atomically, then removes the lease file. A wrong or ambiguous owner performs no mutation. A crash between profile write and lock deletion can only leave a conservative lock, never duplicate ownership.

## Verification and next gate

The TypeScript build plus MUXIA core/parity suite must pass on the clean Windows staging worktree. The full bridge, one-canon Windows/Linux checks and high-confidence secret scan must also be green before publication.

After merge, `MX-062` starts as a real elapsed 24-hour bounded soak. No shortened or synthetic duration may satisfy that task.
