# MUXIA MX-040 — TWO-PROFILE ISOLATION V1

Status: VERIFIED / COMPLETE
Date: 2026-08-27
Task: `MX-040 — Two-profile isolation`

## Purpose

Prove that two MUXIA profiles are distinct identity/storage/ownership boundaries before concurrency scaling.

Profiles:

- `chatgpt-a` -> `C:\DIE\workspaces\MUXIA-B04\muxia-root\profiles\chatgpt-a`
- `chatgpt-b` -> `C:\DIE\workspaces\MUXIA-B04\muxia-root\profiles\chatgpt-b`

`chatgpt-b` was created fresh. It was not copied from `chatgpt-a` or from legacy Proxima.

## Ownership isolation

Separate owners were acquired:

- `chatgpt-a` -> `mx040-owner-a`
- `chatgpt-b` -> `mx040-owner-b`

The registry rejected:

- duplicate lease on A;
- duplicate lease on B;
- cross-owner release attempt.

After proof teardown both profiles returned to `READY` with `leaseOwner = null`.

## Browser storage isolation

No ChatGPT credential/session values were read.

Both profiles visited a temporary loopback origin controlled by the MX-040 proof. Only synthetic test keys were used:

- cookie: `muxia_mx040_cookie`
- localStorage: `muxia_mx040_marker`

Observed:

```text
Profile A sets marker A
Profile B first read -> no A marker / no A cookie
Profile B sets marker B
Profile A re-read -> still A
Profile B re-read -> still B
```

This demonstrates independent browser storage partitions at the profile-directory boundary without inspecting provider credentials.

## Artifact isolation

Synthetic artifact namespaces remained disjoint:

- `artifacts/mx040-profile-a/a.marker`
- `artifacts/mx040-profile-b/b.marker`

No cross-file contamination was observed.

## Log isolation

Synthetic log namespaces remained disjoint:

- `logs/mx040-profile-a/a.log`
- `logs/mx040-profile-b/b.log`

No cross-log contamination was observed.

## Runtime behavior

Profile A's authenticated Edge process remained alive throughout acceptance.

Profile B used a temporary independent Edge process with its own user-data directory and ephemeral loopback debug port. After proof, all B processes were terminated and its lease was released.

The first runner invocation wrote a valid PASS receipt but timed out during teardown because Playwright CDP connections kept the Node event loop alive. The functional proof was preserved, teardown was completed deterministically, and the runner was patched to exit cleanly after cleanup. No acceptance claim was made until browser/lease cleanup was verified.

## Verification

Final regression:

- TypeScript strict build: PASS;
- core tests: 36/36 PASS;
- parity tests: 5/5 PASS;
- total: 41/41 PASS.

Profile state after cleanup:

- `chatgpt-a`: READY / no lease;
- `chatgpt-b`: READY / no lease;
- profile B browser processes: 0;
- profile A browser preserved and responsive.

## Canonical receipt

`company/muxia/receipts/MX-040-two-profile-isolation.receipt.json`

## Acceptance verdict

PASS:

- distinct ownership;
- no synthetic cookie/localStorage contamination;
- no artifact contamination;
- no log contamination;
- no legacy profile copy/import;
- no credential value read.

Next DAG node: `MX-041 — Crash recovery`.
