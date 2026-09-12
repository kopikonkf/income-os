# DIE-H01 Provider-Independent Native SVG Request / Receipt v1

Status: H01-104 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Boundary

H01-104 defines one provider-independent execution envelope between H01-102 prompt compilation and downstream SVG validation/postproduction.

```text
Blueprint v2 + Master Instruction v2 + Provider Prompt v2
        ↓
Native SVG Request v1
        ↓
web-ai-adapter (DEFAULT) | native MCP (OPTIONAL)
        ↓
provider result / SVG candidate
        ↓
H01-103 validation
        ↓
Native SVG Receipt v1
```

The contract is not Claude-specific. `provider_id` and `provider_profile` are data fields; the schema and result semantics stay identical across eligible providers.

## Ingress

`WEB_AI_ADAPTER` is the required default/preferred ingress. `NATIVE_MCP` is an allowed optional transport and is explicitly not required. Ingress is chosen at dispatch commit, not embedded into semantic idempotency identity. Therefore switching transport cannot silently authorize a second generation for the same logical provider request.

## Lineage

Every request preserves:

- queue item / source candidate / semantic asset identity;
- Blueprint ID and SHA-256;
- Master Instruction SHA-256;
- exact provider prompt text, character count and SHA-256;
- provider target/profile;
- fixed native SVG output contract.

Every receipt repeats the Blueprint/Master/Prompt hash chain and the provider result metadata. Raw credentials, cookies, session bytes and Mission capabilities are outside this contract.

## Exactly-once provider authority

`idempotency_key` binds semantic/provider generation material but intentionally excludes request ID and ingress transport. `ExactlyOnceLedger` is a local dispatch guard, not a scheduler:

```text
RESERVED -> DISPATCH_COMMITTED -> TERMINAL
```

A repeated identical reserve is idempotent. Replaying the same committed dispatch is `UNCHANGED`. Attempting a different ingress/dispatch after commit fails `E_ALREADY_DISPATCHED`. A terminal receipt requires a matching prior dispatch commit and is itself idempotent; conflicting terminal evidence fails closed.

The ledger does not select tasks, providers, retries, or routes. Mission Control remains the sole scheduler/authority.

## Success boundary

A receipt may say `SUCCEEDED` only when all of these are true:

- provider result payload kind is `SVG_SOURCE_TEXT`;
- source kind is `DIRECT_PROVIDER_SVG_SOURCE`;
- `native_editable=true`;
- `conversion_from_raster=false`;
- `embedded_raster=false`;
- H01-103 validation status is `PASS` with canonical SVG SHA-256;
- provider response and extracted SVG candidate hashes are preserved.

A traced PNG/JPEG, embedded raster wrapped in SVG, screenshot, post-hoc vectorization, or unvalidated SVG can never claim native-SVG success under this contract.

## Failure boundary

`FAILED`, `BLOCKED`, `TIMEOUT`, and `CANCELLED` receipts preserve normalized provider result/error metadata without inventing SVG success or H01-103 PASS. Provider failure evidence stays honest and can be used by downstream scheduling policy without mutating the result into success.

## Provider result preservation

Receipt provider result includes normalized provider status, provider request/correlation ID when available, finish reason, typed error code/detail, response hash, payload kind, and candidate SVG hash. Provider-specific raw wire/session/cookie data is not canonicalized.

## H01-103 proof fixture

The synthetic contract fixture is explicitly non-live. Its book-like SVG candidate was run through the accepted H01-103 engine under H01-102 canary limits and passed as editable vector geometry:

- geometry count 3;
- path count 2;
- shape count 1;
- sampled points 31;
- render ink pixels at 512: 80,899;
- candidate SVG SHA-256 `5be66398af81d4b640a1a26acec79a6440d924edbad97328250796a005630d8b`;
- canonical SVG SHA-256 `2fd3eff13af373475f72cc55d040c53aae8383825e78cf89fcca1970a1e4678c`.

This proves contract compatibility only. It does not promote Claude or any other provider; live provider canaries belong to H01-107.

## Authority exclusions

H01-104 performs no provider call, submission, publication, route promotion, browser mutation, `/srv/die` mutation, or Atlas mutation. `web-ai-adapter` remains default ingress; native MCP remains optional. H01-105 owns deterministic postproduction, and H01-107 owns provider-by-provider live canaries.
