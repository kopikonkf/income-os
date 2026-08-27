# MUXIA-B04 — PROVIDER / WINDOWS PROOF

Status: BLOCKED AT MX-032 / FAIL-CLOSED AS DESIGNED
Date: 2026-08-27
Batch: `MUXIA-B04 — Provider/Windows Proof`
Intended chain: `MX-031 -> MX-032 -> MX-033 -> MX-034`
Execution rule: `STOP_ON_BLOCKER`

## Executive result

B04 did not fail by producing an unsafe workaround. It stopped exactly where the provider-policy and state-machine contracts require.

`MX-031` was already complete before B04. The first live ChatGPT Windows probe then exposed a real production compatibility issue: the dedicated MUXIA profile reached a protection interstitial with page title `Just a moment...` rather than a composer or normal login page.

The initial detector v1 classified that page as `UNKNOWN`. This was repaired as `MX-031-R1` by adding bounded page-title observation and explicit protection-title classification. No bypass, stealth, CAPTCHA solving, token extraction, or provider-private API behavior was added.

After repair, the same live probe classified deterministically:

```text
state   = BLOCKED
reason  = PROTECTION_CHALLENGE
signal  = protection-title
url     = https://chatgpt.com/
```

Because MX-P03 and MX-031 require fail-closed behavior on provider protection states, MX-032 stopped before submitting any canary prompt. MX-033 and MX-034 therefore remain dependency-blocked and were not started.

## Dedicated MUXIA proof profile

B04 used a new MUXIA-only profile root:

`C:\DIE\workspaces\MUXIA-B04\muxia-root\profiles\chatgpt-a\browser`

It did **not** import or copy:

`C:\Users\aethers\AppData\Roaming\proxima`

This preserves the MX-P01 rule that legacy Proxima browser/session state is not bulk-cloned into MUXIA.

## Live probe sequence

```text
MUXIA Chromium driver
  -> dedicated chatgpt-a profile
  -> navigate https://chatgpt.com/
  -> no prompt submitted
  -> no Output extracted
  -> detector v1: UNKNOWN
  -> selector-only diagnostic
  -> title = "Just a moment..."
  -> MX-031-R1 repair
  -> detector v1.1 live reprobe
  -> BLOCKED / PROTECTION_CHALLENGE
  -> STOP
```

The diagnostic inspected only page title plus counts/visibility of a bounded set of login/composer selectors. It did not dump page body, chat history, cookies, tokens, localStorage, sessionStorage, or credential material.

## MX-031-R1 — minimal repair

Observed defect:

A Cloudflare-style protection interstitial may expose no known login/composer selectors and can therefore look like `UNKNOWN` if title is ignored.

Repair:

- add bounded `title` to provider page snapshot;
- recognize `Just a moment...`, Cloudflare attention-required, browser-checking, and security-verification titles as `PROTECTION_CHALLENGE`;
- add current likely login/composer selector variants;
- preserve `BLOCKED > AUTH_REQUIRED > READY > UNKNOWN` priority;
- preserve sanitized observation contract;
- add no bypass behavior.

Detector version after repair:

`chatgpt-state-detector-v1.1`

Targeted detector verification after repair:

`11 passed / 0 failed`.

## MX-032 — Windows text canary parity

Status: `BLOCKED`.

Blocker:

`LIVE_CHATGPT_PROTECTION_CHALLENGE`.

The text canary was not executed. No prompt was submitted and no consumer-web Output was extracted.

Resume condition:

An authorized operator-controlled MUXIA ChatGPT session must reach `READY` **without bypass/circumvention**. Only then may the bounded text canary be performed and manually confirmed under MX-P03.

## MX-033 / MX-034

- `MX-033 — Windows durable image parity`: NOT STARTED / dependency-blocked.
- `MX-034 — Windows restart persistence proof`: NOT STARTED / dependency-blocked.

The batch does not skip failed prerequisites merely to obtain a green end-to-end story.

## Full regression after repair

- TypeScript strict build: PASS;
- core tests: 36 passed / 0 failed;
- parity tests: 5 passed / 0 failed;
- total: 41 passed / 0 failed;
- orphan MUXIA test Chromium processes after suite: 0.

## Canonical receipts

- `company/muxia/receipts/MX-031-R1-cloudflare-title-repair.receipt.json`
- `company/muxia/receipts/MX-032-windows-text-canary.blocked.receipt.json`
- `company/muxia/batches/MUXIA-B04-provider-windows-proof.receipt.json`

## Boundary receipt

B04 performed no:

- CAPTCHA/protection bypass;
- stealth/fingerprint evasion;
- legacy profile import;
- cookie/token/session credential read;
- ChatGPT prompt submission;
- ChatGPT Output extraction;
- image generation;
- Proxima modification/restart/stop;
- production submission/publication;
- spend.

This is a valid batch outcome: the provider boundary was tested against reality and the system stopped safely when the real provider environment contradicted the optimistic path.

## 2026-08-27 — B04 resumed and completed

The earlier `BLOCKED_AT_MX-032` state remains valid historical evidence. B04 subsequently resumed through operator-controlled authentication bootstrap and completed all remaining proof nodes:

- MX-032-R1 DONE;
- MX-032 DONE;
- MX-033 DONE;
- MX-034 DONE.

Final B04 verdict: **PASS**.

Completion receipt: `company/muxia/batches/MUXIA-B04-provider-windows-proof.complete.receipt.json`.

The Windows proof now demonstrates: provider state detection, persistent authenticated profile, text parity under operator control, durable image artifact parity, and restart/session persistence with a new browser process identity.
