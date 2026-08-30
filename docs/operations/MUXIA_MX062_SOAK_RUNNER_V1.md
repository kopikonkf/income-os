# MUXIA MX-062 24-hour Soak Runner v1

Date: 2026-08-30
Task: `MX-062`
Lifecycle status after this readiness batch: `READY` — not DONE until a real elapsed 24-hour receipt passes.

## Purpose

This runner restores the pre-soak implementation described in the prior Chapter #4 session as a durable Git artifact. It is intentionally incapable of satisfying MX-062 with a shortened run.

## Hard gates

- minimum elapsed duration: exactly 86,400,000 ms (24 hours);
- fixed sample interval: 60,000 ms;
- required expected-sample coverage: at least 95%;
- append-only SHA-256 sample hash-chain;
- sample sequence, prior hash, wall-clock order, and elapsed-time order are verified;
- clock rollback/tampered chain fails closed;
- any non-zero failure counter makes the final receipt FAIL;
- no `--duration`, `--hours`, `--minutes`, or interval override exists.

## Synthetic non-production probe

Every sample exercises the actual persistent MUXIA core registries inside an isolated root:

1. create a synthetic READY profile;
2. acquire its filesystem lease;
3. prove a second owner cannot acquire the lease;
4. transition the synthetic profile/job to RUNNING;
5. simulate a dead process and run canonical crash recovery;
6. require job `FAILED`, profile `READY`, lease released;
7. run a separate synthetic artifact job through `QUEUED -> ASSIGNED -> RUNNING -> VERIFYING`;
8. write/register a tiny synthetic PNG;
9. require durable artifact receipt/hash before `SUCCEEDED`;
10. reopen registries and verify persisted recovery/artifact state;
11. scan persistent state JSON for credential-like key names.

The runner imports no provider, ChatGPT, or Playwright code and does not inspect an authenticated browser profile.

## Failure counters

The final receipt aggregates:

- `profileCorruption`;
- `credentialLeakage`;
- `duplicateOwnership`;
- `recoveryMismatch`;
- `artifactMismatch`;
- `clockRollback`;
- `chainTamper`.

All must remain zero for PASS.

## Linux execution

Build from canonical source first:

```text
cd /srv/die/company/muxia
npm ci
npm run build
```

Install the restart-safe service template as root, passing the existing Linux runtime user:

```text
sudo ./scripts/linux/mx062-install-soak.sh <runtime-user>
```

The installer resolves the actual absolute Node 24 binary with `command -v node` and renders that path into the systemd unit; it does not assume `/usr/bin/node`. The installer deliberately does **not** start the soak. Start is an explicit operator action:

```text
sudo systemctl start muxia-mx062-soak@<runtime-user>.service
```

The service uses:

- source: `/srv/die/company/muxia` read-only;
- production MUXIA root declared as `/var/lib/muxia` only so the runner can reject accidental reuse;
- isolated soak state: `/var/lib/muxia-soak/mx062-soak-v1`;
- final receipt: `/var/lib/muxia-soak/mx062-soak-v1.receipt.json`.

`Restart=on-failure` resumes from the existing hash-chained ledger after process/service interruption. A tampered ledger cannot resume.

## Acceptance boundary

Publishing this runner does not complete MX-062. `MX-062` remains `READY` until all of the following exist from a real Linux execution:

- elapsed time >= 24 hours;
- coverage >= 95%;
- zero failure counters;
- valid chain through final sample;
- complete resource/failure receipt;
- post-run canonical validation.

Only then may `MX-062` transition to DONE and open `MX-070`.
