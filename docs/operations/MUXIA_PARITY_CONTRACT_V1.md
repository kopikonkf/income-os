# MUXIA PARITY CONTRACT V1

Status: MX-012 VERIFIED / COMPLETE
Date: 2026-08-27
Product: MUXIA
Source policy: independent DIE implementation; no Proxima source/test copy

## Purpose

MX-012 freezes what counts as a durable successful raster result before MUXIA core implementation begins. The contract is intentionally implementation-independent and Electron-independent.

It does not automate ChatGPT, launch a browser, mutate Proxima, or define provider-policy permission. It verifies evidence that already exists on disk.

## New DIE-owned artifacts

- `company/muxia/contracts/muxia.parity-contract.v1.json`
- `company/muxia/tests/parity/fixtures/legacy-proxima-postfix-v1.json`
- `company/muxia/tests/parity/muxia-parity-contract.test.mjs`

No Proxima source module or Proxima test module is imported by the MUXIA parity suite.

## Contract

A success claim is accepted only if, at verification time:

1. the artifact exists physically;
2. the artifact is non-empty and within the bounded size contract;
3. its actual raster container is PNG, JPEG, or WebP;
4. its physical SHA-256 is lowercase 64-hex and matches expected evidence;
5. its byte count matches expected evidence;
6. a durable artifact receipt exists;
7. receipt path/hash/bytes/MIME agree with the physical artifact; and
8. the external probe receipt agrees with the same physical artifact.

`PASS`, `VERIFIED`, or `SUCCEEDED` text alone is never sufficient.

The parity contract has no Electron runtime dependency and declares browser-session credential values out of scope.

## Baseline selected

The parity fixture uses the physically present post-fix canary:

- probe receipt: `C:\DIE\workspaces\M001-U1-001\probe\PROBE_RECEIPT_POSTFIX-20260825T084836Z.json`;
- artifact: `D:\proximav2-setup\artifacts\9fe55423eaed192b4e5e1d76f8ea74135b52667a622eaf24308b6b08eaa28318.png`;
- artifact receipt: same basename with `.receipt.json`;
- SHA-256: `9fe55423eaed192b4e5e1d76f8ea74135b52667a622eaf24308b6b08eaa28318`;
- bytes: `976345`;
- media: `image/png`.

The later post-merge historical receipt `PROBE_RECEIPT_POSTMERGE-2026-08-25T09-38-20-412Z.json` currently references a `b176...` artifact path that is not physically present at that recorded path. MX-012 therefore does not treat the newest timestamp or a historical PASS string as automatically superior evidence. Physical durability at verification time wins.

This observation does not modify or invalidate the historical receipt; it demonstrates the need for the MUXIA parity rule.

## Verification

Command:

```text
node --test company\muxia\tests\parity\muxia-parity-contract.test.mjs
```

Result:

```text
5 tests
5 pass
0 fail
```

Cases proven:

1. current physically present legacy baseline satisfies independent MUXIA contract;
2. deliberately corrupted expected SHA-256 is rejected;
3. deliberately missing artifact path is rejected even when receipt evidence says PASS;
4. success state without durable artifact/receipt is rejected as false success; and
5. the parity contract itself is Electron-independent and credential-free.

## Security/licensing boundary

The suite was authored from MUXIA PRD/ADR requirements, DIE-owned receipts, and observable physical evidence. It does not reuse Proxima source/test code. This preserves the clean-implementation boundary created by MX-011 after discovery of Proxima's personal/non-commercial license.

No cookie, token, localStorage value, browser profile secret, CDP credential, or provider auth material was requested/read by MX-012.

## Runtime boundary

MX-012 performed no:

- Proxima source modification;
- Proxima restart/stop/start;
- browser/profile/session change;
- service mutation;
- marketplace action;
- asset generation;
- production batch;
- spend.

## Next eligibility

Completion of MX-012 unlocks two independent DAG nodes:

- `MX-020 — Define core domain types`;
- `MX-P03 — ChatGPT web execution policy gate`.

`MX-P03` must complete before a production/unattended ChatGPT web adapter is implemented. It does not block pure provider-neutral MUXIA core modeling in MX-020.
