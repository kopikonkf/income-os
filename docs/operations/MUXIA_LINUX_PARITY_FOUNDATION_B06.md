# MUXIA-B06 — LINUX PARITY FOUNDATION

Status: BLOCKED_AT_MX-050
Date: 2026-08-27
Execution policy: STOP_ON_FIRST_FAILURE
Chain: `MX-050 -> MX-051 -> MX-052`

## Current host capability

The current Windows VPS has no Linux execution substrate available to MUXIA:

- WSL: not installed;
- Docker: unavailable;
- Podman: unavailable.

The active ChatGPT Architect service principal is Administrator, but no OS-level installation was performed because enabling/installing WSL can alter Windows features and may require a reboot. Founder approval is required before that mutation.

## MX-050 preparation completed

Linux bootstrap artifacts were created:

- `company/muxia/scripts/linux/mx050-bootstrap.sh`
- `company/muxia/scripts/linux/mx050-runtime-smoke.mjs`
- `company/muxia/tests/core/linux-bootstrap-contract.test.mjs`

Bootstrap contract:

```text
Linux host
  -> Node.js >= 20
  -> npm ci
  -> playwright install --with-deps chromium
  -> TypeScript build
  -> Linux-only persistent Chromium smoke
  -> durable runtime smoke receipt
```

The Linux smoke explicitly refuses non-Linux hosts with `MX050_REQUIRES_LINUX:<platform>`. This prevents Git Bash/Windows path fixtures from being misreported as Linux runtime parity.

No Electron dependency is required by the bootstrap contract or package dependencies.

## Verification completed on Windows

Static/contract checks:

- Linux bootstrap contract test: PASS;
- Chromium-only requirement: PASS;
- Electron dependency absent: PASS;
- non-Linux runtime false-PASS rejection: PASS.

Full repository regression after MX-050 preparation:

- TypeScript strict build: PASS;
- core tests: 43/43 PASS;
- parity tests: 5/5 PASS;
- total: 48/48 PASS.

## Blocker

`LINUX_RUNTIME_UNAVAILABLE_ON_HOST`

MX-050 acceptance requires an actual Linux Playwright/Chromium execution target. Windows execution, Git Bash, and OS-neutral path fixtures are insufficient evidence.

## Resume conditions

Any one of the following creates a legitimate execution target:

1. Founder authorizes installation/enablement of WSL2 on this VPS, then a Linux distribution is installed and usable; or
2. Founder provides another reachable Linux host/runtime for MUXIA proof; or
3. another zero-cost Linux substrate is installed with explicit Founder authorization.

Recommended simplest path: WSL2 + Ubuntu on the current VPS, then run `company/muxia/scripts/linux/mx050-bootstrap.sh` inside WSL.

## Batch behavior

Because B06 uses `STOP_ON_FIRST_FAILURE`, MX-051 and MX-052 were not started.

No Linux parity claim has been made.
