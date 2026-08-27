# MUXIA-B06 — LINUX PARITY FOUNDATION

Status: AUTHORIZED SCOPE COMPLETE / STOP AND EVALUATE
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
- Publication branch: `architect/muxia-b06-linux-proof`

## Sealed source preflight

MUXIA was published from a clean staging clone rather than the dirty live `C:\DIE` worktree.

- original source commit: `1176c7a86ad369382e1aee23bdb7465a00c5de62`
- publication receipt commit: `26398e54a1924ab3583f1a04a095a8437620e7e1`
- sealed files: 86
- secret-pattern scan: PASS
- source bundle hash and 86-file manifest: PASS on Linux
- live Windows state, profiles, services, Proxima, and unrelated dirty files: excluded

## MX-050 result

MX-050 completed PASS on the actual Linux VPS.

- Node.js `v24.18.1`, official archive checksum verified
- npm `11.16.0`
- TypeScript `5.9.3` exact-pinned
- Playwright `1.62.1`
- Chromium `151.0.7922.34`
- Chromium tree root-owned under `/opt/muxia/playwright-browsers`
- exact-path AppArmor `userns` profile preserves the browser sandbox
- `--no-sandbox` absent
- debug endpoints loopback only
- Electron dependency absent
- residual MUXIA Chromium after verification: zero

One repair child, `MX-050-R1`, absorbed the undeclared TypeScript compiler, Ubuntu AppArmor userns restriction, and Windows-only physical legacy-evidence scope. No second repair child was created.

## Restricted operator GUI

The GUI layer completed PASS.

- XFCE 4.18
- xrdp 0.9.24-4 + xorgxrdp 0.9.19-1
- listener: `127.0.0.1:3389` only
- access: SSH local port forwarding
- direct public RDP: false
- operator password changed by MUXIA: false
- dedicated profile: `/var/lib/muxia/profiles/chatgpt-linux-a/browser`, mode `0700`

## MX-051 result

MX-051 completed PASS.

- manual ChatGPT authentication: operator-controlled normal Chromium
- credential/cookie/token values read by MUXIA: false
- automated prompt submission or consumer-web output extraction: false
- first sanitized state: `READY / COMPOSER_READY`
- post-restart sanitized state: `READY / COMPOSER_READY`
- same profile reused: true
- browser process identity changed: true
- debug endpoint: ephemeral loopback only
- text canary: exact response `MUXIA_LINUX_TEXT_OK_1`, Founder-attested
- image canary: operator-downloaded PNG, 865,504 bytes
- image SHA-256: `ae8717b508327af34ff00d7b820cf5764d689c2d2d9e8ee6909188bd8b7dc440`
- durable artifact lineage: `chatgpt-linux-a`, job `SUCCEEDED`

A headless post-login observation classified `BLOCKED / PROTECTION_CHALLENGE`. The run stopped fail-closed. No bypass was attempted. The proof then used the already authenticated headed XFCE session and passed twice across restart.

## MX-052 result

MX-052 completed PASS using a loopback-only synthetic fixture; no provider network or Windows GUI dependency was used.

- participants: `chatgpt-linux-b` through `chatgpt-linux-e`
- control/authenticated profile A excluded: true
- four unique logical owners and leases: PASS
- duplicate lease rejection: 4/4 PASS
- concurrent workload overlap: 2,005 ms
- per-profile storage isolation: PASS
- artifact/log lineage isolation: PASS
- job completion: 4/4 `SUCCEEDED`
- debug endpoints: loopback only
- observed aggregate browser RSS: 4,754,768 KiB across 49 processes
- deterministic teardown: PASS
- residual B–E browser processes: 0
- leases released/browser PIDs cleared: 4/4
- final profile state: 4/4 `READY`
- profile directory mode: 4/4 `0700`

## Verification

Final source regression:

- Windows: core 49/49 + parity 5/5 = 54/54 PASS
- Linux: core 49/49 PASS
- Linux parity: 2 PASS + 3 explicit Windows-only physical-evidence SKIP
- false success: zero

Canonical receipts:

- `company/muxia/receipts/MX-050-linux-bootstrap.receipt.json`
- `company/muxia/receipts/MX-050-GUI-operator-layer.receipt.json`
- `company/muxia/receipts/MX-051-sanitized-state-restart.receipt.json`
- `company/muxia/receipts/MX-051-image-artifact.receipt.json`
- `company/muxia/receipts/MX-051-linux-single-profile-parity.receipt.json`
- `company/muxia/receipts/MX-052-linux-four-profile-isolation.receipt.json`

## Stop boundary

The exact authorized scope is complete. MX-060 and all later tasks remain `BLOCKED` pending separate Founder authorization after receipt evaluation.

Still excluded and untouched: Executive, Division01, OAUTH, Atlas, Hermes production, Proxima, Aether, Linux MCP deployment, Cloudflare, marketplace submission/publication, spend, cutover, and Windows live `C:\DIE`.

## PUB-001 revalidation — 2026-08-27

B06 was revalidated before publication/merge. The initial checkpoint was `b7d18d732974a4dc3e77df67a2afc2cfd8a721f9` on both the clean Windows staging clone and `/srv/die`, with the remote feature branch at the same SHA and `origin/main` at `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`.

Windows revalidation remained 54/54 PASS. The first fresh-shell Linux core run exposed a reproducibility gap: four browser-launch tests timed out because the shell did not inherit the B06-pinned `PLAYWRIGHT_BROWSERS_PATH=/opt/muxia/playwright-browsers`. This triggered `STOP_ON_FIRST_FAILURE` and exactly one repair child, `PUB-001-R1`.

`PUB-001-R1` adds only `company/muxia/scripts/linux/pub001-revalidate.sh`, which pins the existing B06 runtime/browser-root environment and then runs build, core, and parity regression. It does not change the browser driver, AppArmor policy, sandbox posture, profile state, or provider behavior. Repair implementation commit: `2c7a1699fa1988c02f2c455b8c4e613db212db3e`.

Final canonical Linux run from `/srv/die` at that commit: core 49/49 PASS; parity 2 PASS + 3 explicit Windows-only SKIP; marker `PUB001_LINUX_REVALIDATION_PASS`. Durable receipt: `company/muxia/receipts/PUB-001-b06-revalidation.receipt.json`.
