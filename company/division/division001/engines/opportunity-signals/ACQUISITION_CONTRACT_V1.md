# Division01 Opportunity Signals Acquisition Contract v1

Status: CANONICAL CONTRACT
Task: OE-001C
Owner: Division-01 Digital Asset Intelligence

## 1. Purpose

Define how Opportunity Signal adapters may acquire evidence without expanding authority, violating platform boundaries, or turning consumer-session access into hidden scraping infrastructure.

This contract authorizes **no specific platform adapter by itself**. Each adapter must pin a dated acquisition policy profile.

## 2. Policy classifications

### `ALLOWED_BOUNDED`

A documented public/official surface may be queried using the specific bounded method declared by its adapter/profile.

### `OPERATOR_REQUIRED`

Acquisition requires an operator-controlled interaction. Automation may ingest a sanitized evidence artifact/receipt after the operator action, but may not replace the required human interaction.

### `OFFICIAL_API_ONLY`

Only the documented official API or an equivalent explicitly authorized first-party export may be used.

### `SYNTHETIC_ONLY`

No live collection is authorized; fixtures only.

Unknown policy is fail-closed and therefore cannot produce an accepted live signal receipt.

## 3. Allowed acquisition methods

A receipt may identify one of:

- `OFFICIAL_API`
- `PUBLIC_WEB_DOCUMENT`
- `PUBLIC_SEARCH_UI`
- `CONTRIBUTOR_UI`
- `MANUAL_OPERATOR`
- `OPERATOR_EVIDENCE_IMPORT`
- `SYNTHETIC_FIXTURE`

The method must match the pinned policy classification. `OFFICIAL_API_ONLY` requires `OFFICIAL_API`; `OPERATOR_REQUIRED` requires `MANUAL_OPERATOR` or `OPERATOR_EVIDENCE_IMPORT`; `SYNTHETIC_ONLY` requires `SYNTHETIC_FIXTURE`.

## 4. Explicitly forbidden

Opportunity Signals collectors MUST NOT:

- extract cookies, session tokens, OAuth tokens, private API credentials, or browser secrets;
- call private/internal backend endpoints discovered from a consumer session;
- bypass CAPTCHA, anti-bot, access control, protective challenges, or rate limits;
- use stealth/fingerprinting evasion to conceal automation;
- automate a surface when its policy profile requires an operator;
- infer that submission eligibility implies search/data-collection permission;
- persist raw sensitive account/session data in signal receipts;
- scrape private dashboards merely because a browser profile is authenticated;
- fabricate source counts, rankings, trends, or timestamps when collection fails.

On protection challenge, auth requirement, policy ambiguity, or collection failure: stop and emit no live signal. The adapter may emit a separate diagnostic receipt, but not a fabricated Opportunity Signal.

## 5. Consumer ChatGPT / MUXIA boundary

Consumer ChatGPT profiles remain operator-controlled acquisition lanes under the MUXIA policy boundary. Opportunity Signals does not grant unattended prompt submission/output scraping, cookie extraction, token extraction, private backend calls, CAPTCHA bypass, or stealth.

If ChatGPT is used for research cognition, its derived interpretation is not a raw Opportunity Signal. The underlying governed source evidence must remain separately referenced.

## 6. Platform submission matrix is not acquisition permission

`docs/pipeline/MATRIX_6_PLATFORM_TOS_STRICTNESS.md` governs dated platform/content/submission concerns. It does **not** automatically authorize search-result collection or automation. Each Opportunity Signals source adapter needs its own acquisition policy profile.

## 7. Receipt hygiene

Accepted live receipts must pin:

- collector identity;
- source ID and source reference;
- acquisition method;
- acquisition policy profile ID/version;
- observation/record/expiry timestamps;
- evidence label and confidence;
- normalized value/unit;
- optional evidence artifact SHA256;
- zero or explicitly authorized collection cost.

No raw credential/session value is a valid receipt field.

## 8. Failure semantics

Fail closed on:

- unknown source policy;
- method/policy mismatch;
- stale receipt at evaluation time;
- observation timestamp after recording timestamp;
- expiry not later than recording timestamp;
- malformed subject/value;
- synthetic evidence presented as live;
- missing collector/source provenance.

The canonical semantic validator is `validate_signal_receipt.py`.
