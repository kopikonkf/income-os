# MUXIA CHATGPT PROVIDER STATE DETECTOR V1

Status: MX-031 VERIFIED / COMPLETE
Date: 2026-08-27
Provider: ChatGPT consumer web
Detector version: `chatgpt-state-detector-v1`

## Purpose

MX-031 teaches MUXIA to recognize a small, fail-closed set of visible provider states without submitting prompts, extracting Output, reading browser credentials, reverse engineering private endpoints, or bypassing protections.

## State contract

```text
BLOCKED
  > AUTH_REQUIRED
    > READY
      > UNKNOWN
```

Higher-priority risk/auth signals override a visible composer.

### READY

Requires a visible composer signal and no blocking/authentication signal.

### AUTH_REQUIRED

Authentication URL/login controls/login-only page signals map to `AUTH_REQUIRED` and require operator action.

### BLOCKED

Visible signals for any of the following map to `BLOCKED`:

- rate/usage limit;
- CAPTCHA/human verification/security challenge;
- account disabled/deactivated/suspended;
- access denied/unsupported region.

No automatic recovery or bypass is attempted.

### UNKNOWN

Unreadable/unrecognized page content maps to `UNKNOWN`, never READY. Operator action is required.

## Implementation

- `company/muxia/src/providers/contract.ts`
- `company/muxia/src/providers/chatgpt/state-detector.ts`
- `company/muxia/contracts/chatgpt-state-detector-v1.json`
- `company/muxia/tests/core/chatgpt-state-detector.test.mjs`

The detector gathers only bounded visible body text plus visibility of a small set of UI selectors. It returns sanitized signal labels, not page body content.

## Policy boundary

MX-P03 remains binding. MX-031 does not authorize unattended consumer-web prompt/output automation. The detector exists to route the browser/session safely:

- `READY` -> operator-controlled provider interaction may proceed;
- `AUTH_REQUIRED` -> `WAITING_OPERATOR`;
- `BLOCKED` -> `BLOCKED`/operator recovery;
- `UNKNOWN` -> fail closed / operator inspection.

## Acceptance method

MX-031 acceptance uses local fixture pages only. No ChatGPT network call is required to prove the classifier/state-routing behavior itself.

The integration test uses the MUXIA Chromium driver against local page content to exercise READY, AUTH_REQUIRED, BLOCKED, and UNKNOWN states.

## Final verification

MX-031 targeted detector suite: **10 passed / 0 failed**.

Full MUXIA regression after integration:

- TypeScript strict build: PASS;
- core tests: 35 passed / 0 failed;
- parity tests: 5 passed / 0 failed;
- total: 40 passed / 0 failed;
- orphan MUXIA test Chromium processes after suite: 0.

Atomic receipt: `company/muxia/receipts/MX-031-chatgpt-state-detector.receipt.json`.

MX-031 acceptance used only local fixture pages. Live ChatGPT DOM compatibility remains intentionally unproven until MX-032 operator-controlled canary; this prevents fixture success from being misrepresented as current live-site compatibility.


## 2026-08-27 — MX-031-R1 live compatibility repair

The first B04 live ChatGPT probe exposed a Cloudflare-style protection interstitial with title `Just a moment...` and no known login/composer selectors. Detector v1 classified this `UNKNOWN`.

Minimal repair `MX-031-R1` upgraded the detector to `chatgpt-state-detector-v1.1` by adding bounded page-title observation and explicit protection-title classification. After repair, the same live condition classifies `BLOCKED / PROTECTION_CHALLENGE` with signal `protection-title`.

No bypass, stealth, CAPTCHA solving, credential extraction, or Output extraction was added. Targeted detector tests after repair: 11/11 PASS.
