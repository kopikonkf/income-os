# DIE Asset QA Engine v1 — Runtime + Platform Preflight

Date: 2026-08-30
Tasks: QA-001C, QA-001D, QA-001E, QA-001F, QA-001
Status: EXECUTION CANON

## 1. Runtime boundary

Canonical reusable implementation: `bridge/income_os_bridge/asset_qa.py`.

Executable entrypoint: `bin/die_asset_qa.py`.

The first-class component has two explicit scopes:

- `UNIVERSAL`: invokes the proven `m001_asset_qa.evaluate_manifest()` behavior through a compatibility adapter and promotes the result into `die.asset.qa.v1`.
- `PLATFORM_PREFLIGHT`: validates one prepared asset/package against one exact dated platform QA profile before any irreversible submission action.

The original `bridge/income_os_bridge/m001_asset_qa.py` remains intact as the compatibility implementation. Promotion does not reinterpret a missing visual review as lineage failure and does not create aesthetic/commercial PASS.

## 2. Deterministic promotion

`evaluate_m001_manifest()` executes the legacy gate first and translates its receipt into stable defect codes and first-class routes. Existing M-001 behavior remains authoritative for batch PASS/FAIL/BLOCKED_REVIEW and legacy routing. Canonical translation maps only `T1_PASS` to `PASS`; quarantine, recovery, review and market-fit routes retain their meaning.

Hard-veto translation is explicit for artifact integrity, lineage, rights, safety and watermark states. Missing visual evidence maps to `REVIEW_REQUIRED_VISUAL` and remains non-waivable review work, never synthetic PASS.

## 3. Platform profile interface

Schema: `company/schemas/die.asset.qa-platform-profile.v1.schema.json`.

Canonical dated profiles:

- `company/contracts/qa-platform-profiles/adobe-stock.v1.json`
- `company/contracts/qa-platform-profiles/dreamstime.v1.json`
- `company/contracts/qa-platform-profiles/123rf.v1.json`
- `company/contracts/qa-platform-profiles/vecteezy.v1.json`
- `company/contracts/qa-platform-profiles/motionelements.v1.json`

Magnific is intentionally absent because it is a production/recovery service, not a licensing marketplace.

Each profile pins `profile_version`, `effective_date`, `checked_at`, and the supporting source document. Required categories are format, minimum megapixels, metadata, AI disclosure, similarity/distinctness, account eligibility, content restrictions and upload/package constraints.

The current profile facts are derived only from the existing supporting matrix checked on 2026-08-24: `docs/pipeline/MATRIX_6_PLATFORM_TOS_STRICTNESS.md`. This QA batch does **not** refresh or upgrade that supporting input into a new live platform-contract claim.

Every requirement is either `KNOWN` with evidence refs or `UNKNOWN` with null value. Unknown top-level/requirement fields are rejected. Any required category whose status is `UNKNOWN` emits `PLATFORM_PROFILE_UNKNOWN_REQUIREMENT` as a HARD_VETO and routes `BLOCK_SUBMISSION`.

Therefore the canonical profiles are safe to execute now even when account/technical rules are incomplete: incomplete knowledge blocks irreversible submission rather than inventing a default.

## 4. Metadata/package preflight

`evaluate_platform_preflight()` validates:

- package/mission/batch/Blueprint/asset identity;
- exact Blueprint and asset SHA-256 syntax;
- platform/profile match;
- positive megapixels and declared raster format;
- metadata shape (`title`, `description`, `keywords`, `ai_disclosure`);
- `PREPARED_NOT_SUBMITTED` state;
- `submission_authorized=false` at the QA boundary;
- every KNOWN machine-checkable profile requirement;
- explicit UNKNOWN profile requirements.

The QA package input is deliberately **not** declared the final common Submission Engine schema. `SUB-001A` still owns that later route/package-state contract. QA consumes the minimum preflight fields it needs without stealing SUB authority.

## 5. CLI

Universal compatibility evaluation:

```text
python bin/die_asset_qa.py m001-universal --manifest <manifest> --workspace <root> --output <receipt> --min-assets <n> --max-assets <n>
```

Platform preflight:

```text
python bin/die_asset_qa.py platform-preflight --package <prepared-json> --profile <dated-profile> --output <receipt>
```

Exit codes: `0=PASS`, `2=BLOCKED/BLOCKED_REVIEW/input error`, `3=deterministic FAIL`.

## 6. Authority boundary

Asset QA v1 never:

- performs subjective aesthetic/commercial QC;
- waives a hard veto;
- grants submission/publication authority;
- logs in to a marketplace or consumes account credentials;
- submits/publishes an asset;
- spends money;
- mutates creative semantics.

`QA-001 = DONE` proves an executable, receipt-driven universal + platform-preflight engine. It does not prove QC acceptance, marketplace eligibility, submission, marketplace review, licensing or revenue.

## 7. Acceptance

QA-001C: reusable first-class engine wraps current M-001 behavior without semantic drift.

QA-001D: dated/versioned five-marketplace profile interface exists; unknown fields/requirements fail closed.

QA-001E: metadata/package/Blueprint/hash/profile preflight executes before irreversible submission and emits first-class receipts.

QA-001F: regression covers legacy parity, rights hard-veto, missing visual review, corrupt raster, duplicate binary, strict profile shape, UNKNOWN profile blocking, metadata failure and known-profile PASS fixture.

QA-001: the engine is executable and receipt-driven while QC and submission authority remain separate.
