# MUXIA-B06 — LINUX PARITY FOUNDATION

Status: MX-050 DONE / OPERATOR GUI NEXT / MX-051 READY AFTER GUI
Date: 2026-08-27
Execution policy: STOP_ON_FIRST_FAILURE
Chain: `sealed preflight -> MX-050 -> operator GUI -> MX-051 -> MX-052 -> STOP`

## Target

- Host: `administrator`
- OS: Ubuntu 24.04.4 LTS, kernel `6.8.0-138-generic`
- Source: `/srv/die/company/muxia`
- Runtime: `/var/lib/muxia`
- Browser binaries: `/opt/muxia/playwright-browsers`
- Runtime user/group: `kopiko:muxia`

## Sealed source preflight

MUXIA was published from a clean staging clone rather than the dirty live `C:\DIE` worktree.

- branch: `architect/muxia-b06-linux-proof`
- original source commit: `1176c7a86ad369382e1aee23bdb7465a00c5de62`
- publication receipt commit: `26398e54a1924ab3583f1a04a095a8437620e7e1`
- sealed files: 86
- secret-pattern scan: PASS
- source bundle hash and 86-file manifest: PASS on Linux
- live Windows state, profiles, services, Proxima, and unrelated dirty files: excluded

## MX-050 result

MX-050 completed PASS on the actual Linux VPS.

- Node.js: `v24.18.1`, official archive checksum verified
- npm: `11.16.0`
- Playwright: `1.62.1`
- Chromium: Playwright-managed Chrome for Testing `151.0.7922.34`
- headless persistent-profile smoke: PASS
- Electron dependency: absent
- debug endpoint policy: loopback only
- residual MUXIA Chromium after verification: zero

Canonical receipt:

`company/muxia/receipts/MX-050-linux-bootstrap.receipt.json`

## MX-050-R1 repair

The first bootstrap exposed host assumptions hidden by the Windows developer environment:

1. `tsc` was global on Windows and absent from declared dependencies;
2. Ubuntu 24.04 AppArmor blocked user namespaces for developer Chromium;
3. three physical Proxima evidence tests referenced Windows-only artifacts intentionally excluded from Linux.

One repair child, `MX-050-R1`, handled all defects:

- TypeScript `5.9.3` exact-pinned;
- Chromium installed under root-owned `/opt/muxia/playwright-browsers`;
- an exact-path AppArmor `userns` profile preserves the Chromium sandbox;
- `--no-sandbox` is forbidden;
- physical Windows legacy-evidence tests skip explicitly when that evidence is absent.

Verification:

- Windows: core 43/43 + parity 5/5 = 48/48 PASS
- Linux: core 43/43 PASS
- Linux parity: 2 PASS + 3 explicit Windows-only SKIP
- false success: zero

## Boundary

No Executive, Division01, OAUTH, Atlas, Hermes production, Proxima, Aether, Cloudflare, marketplace, publication, spend, or account action was changed by MX-050.

Next: install the restricted XFCE+xrdp operator layer, then begin MX-051 manual-login parity.
