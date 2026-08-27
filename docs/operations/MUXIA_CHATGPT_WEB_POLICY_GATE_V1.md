# MUXIA CHATGPT WEB POLICY GATE V1

Status: MX-P03 COMPLETE / CURRENT CONSUMER-WEB AUTONOMOUS EXTRACTION BLOCKED
Date checked: 2026-08-27
Provider scope: OpenAI ChatGPT consumer web product
This is an engineering/compliance boundary, not legal advice.

## Decision

MUXIA may continue building provider-neutral browser/profile/session infrastructure, but **current OpenAI consumer Terms do not permit MUXIA to use ChatGPT web as an unattended programmatic output-extraction backend**.

The production architecture must therefore distinguish:

```text
MUXIA SESSION RUNTIME                     CHATGPT CONSUMER WEB OUTPUT AUTOMATION
---------------------                     -------------------------------------
profile lifecycle          ALLOW          automatic/programmatic extraction  BLOCK
browser process lifecycle  ALLOW          unattended download               BLOCK
operator login/recovery    ALLOW          rate-limit/protection bypass        BLOCK
manual acquisition         ALLOW          private backend reverse engineer    BLOCK
durable artifact ingest    ALLOW          credential/session extraction       BLOCK
```

Unattended programmatic prompt dispatch through the consumer web UI is held (`HOLD`) until OpenAI provides a supported interface/terms that clearly permit the intended automation or explicit policy clarification is obtained. The Terms explicitly prohibit automatic/programmatic extraction of data or Output; therefore separating automatic prompt entry from automatic output capture does not create a viable autonomous production contract.

## Current official sources

1. OpenAI Terms of Use — https://openai.com/policies/terms-of-use/
   - published/effective: 2026-01-01;
   - applies to ChatGPT, DALL-E, and other services for individuals;
   - account credentials may not be shared or the account made available to another person;
   - prohibits automatic/programmatic extraction of data or Output;
   - prohibits circumventing rate limits/restrictions and bypassing protective measures/safety mitigations;
   - prohibits reverse engineering underlying service components;
   - states that, as between the user and OpenAI and to the extent permitted by law, the user owns Output;
   - requires evaluation of Output, including human review as appropriate, before using/sharing it.

2. OpenAI Usage Policies — https://openai.com/policies/usage-policies/
   - effective version observed: 2025-10-29;
   - policies apply across OpenAI products/services and may be updated;
   - breaking/circumventing rules/safeguards can result in loss of access or other enforcement.

The Usage Policies update notice was active/current at the time of this check, so MUXIA treats provider policy as a versioned dependency rather than a one-time assumption.

## Important economic/legal distinction

Current Terms provide an Output ownership clause; this means the policy issue identified here is **not a blanket statement that generated output cannot be commercially used**.

The blocker is the **consumer web automation transport**: current Terms prohibit automated/programmatic extraction of Output and protective-measure/rate-limit circumvention. Output ownership does not waive those access restrictions.

## Allowed MUXIA V1 work under this gate

MUXIA may implement, test, and deploy the following provider-neutral infrastructure:

- local profile registry;
- one-owner profile lease;
- disposable Chromium process lifecycle;
- configurable profile roots;
- local/private health and observability;
- operator-controlled browser launch/takeover;
- operator authentication/recovery states;
- job preparation/queueing that pauses at the provider interaction gate;
- ingestion, validation, hashing, and receipts for output files acquired through an operator-controlled step;
- clean separation between provider adapter and core runtime;
- fail-closed `WAITING_OPERATOR` on authentication/protection ambiguity.

These capabilities do not authorize automated extraction from ChatGPT consumer web.

## Blocked MUXIA V1 implementation

Unless the governing terms/interface changes, MUXIA must not implement for ChatGPT consumer web:

- unattended automatic/programmatic Output scraping/extraction/download;
- reverse-engineered private backend/token/session API as the production transport;
- cookie/token/localStorage extraction for reuse outside the browser profile;
- CAPTCHA/proof-of-work/protection bypass;
- rate-limit or account restriction circumvention;
- automation stealth/fingerprint camouflage intended to evade protections;
- credential sharing across principals/workers;
- logic that treats repeated browser retries as permission to push through a provider block.

## Operator-controlled acquisition contract

For consumer ChatGPT web under the current gate:

```text
DIE job prepared
   -> MUXIA allocates dedicated profile
   -> browser/session presented to authorized operator
   -> operator performs/approves provider interaction and output acquisition
   -> output becomes a local file under MUXIA artifact boundary
   -> MUXIA validates/hash/receipts the local artifact
   -> job may proceed to VERIFYING/SUCCEEDED
```

If the provider requires authentication, CAPTCHA, suspicious-login confirmation, rate-limit recovery, or another protection step, state becomes `WAITING_OPERATOR` or `BLOCKED`; MUXIA does not solve or evade it.

## Future autonomous route

A fully unattended ChatGPT producer may be enabled only if at least one of the following becomes true:

1. OpenAI exposes a supported programmatic interface/product contract that permits the required generation/output retrieval workflow; or
2. OpenAI Terms/product documentation materially change so the intended consumer-web automation is clearly permitted; or
3. a different OpenAI business/enterprise agreement explicitly governs and permits the architecture.

Any such change requires a new provider-policy receipt and MUXIA ADR update. API/BYOK economics remain a separate Founder economic decision; this gate does not authorize spend.

## Re-check policy

Re-run this gate:

- before implementation of a ChatGPT execution/output adapter;
- before unattended production enablement;
- before MUXIA cutover;
- after material Terms/Usage Policy changes; and
- after changing the governing account/product agreement.

Default review interval while MUXIA is under development: 30 days.

## Machine-readable contract

`company/muxia/policies/chatgpt-web-boundary-v1.json`

Decision value:

`CONSUMER_WEB_AUTONOMOUS_EXTRACTION_BLOCKED`

## MX-P03 acceptance

- current official Terms checked: PASS;
- current Usage Policies checked: PASS;
- consumer-web output extraction boundary explicit: PASS;
- account credential sharing boundary explicit: PASS;
- rate-limit/protection bypass boundary explicit: PASS;
- reverse-engineering/private-backend boundary explicit: PASS;
- operator-assisted compliant path defined: PASS;
- future supported-interface escape hatch defined: PASS;
- no browser/provider/runtime mutation: PASS.
