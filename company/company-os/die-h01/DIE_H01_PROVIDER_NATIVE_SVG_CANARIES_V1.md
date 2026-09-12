# DIE H01 Provider Native-SVG Canaries v1

Status: H01-107 DONE / PASS
Date: 2026-09-12

## Purpose

H01-107 proves live SVG behavior provider-by-provider after the Claude baseline. All final canaries reuse the authenticated `h01-web-p001 / h01-web-s01 / 127.0.0.1:9201` runtime sequentially. The p002-p007 AUTH_REQUIRED attempts are retained only as superseded historical evidence; they were caused by an incorrect provider-to-profile assumption and do not define provider capability.

A provider is classified only from live output evidence as `NATIVE_SVG`, `TEXT_SVG`, `UNSUPPORTED`, or `DEFERRED`. No model capability claim promotes a route.

## Final live matrix

| Order | Provider | Surface observed | Final result | Evidence |
|---:|---|---|---|---|
| 1 | Claude | persisted authenticated web session | `TEXT_SVG / PASS` | 908-byte provider-original; H01-103 PASS |
| 2 | ChatGPT | persisted authenticated web session | `TEXT_SVG / PASS` | 793-byte provider-original; H01-103 PASS |
| 3 | Qwen | persisted authenticated web session | `TEXT_SVG / PASS` | late completion recovered by exact-conversation recheck; 1,453-byte provider-original; H01-103 PASS |
| 4 | Gemini | persisted authenticated web session | `NATIVE_SVG / PASS` | provider exposed `Download SVG`; exact 7,987-byte downloaded file preserved; H01-103 PASS |
| 5 | Grok | `Fast` | `UNSUPPORTED` | terminal assistant body contained only `Worked for 7s`; no usable SVG text/file after bounded recheck |
| 6 | Manus | `Manus 1.6 Lite` | `TEXT_SVG / PASS` | canonical prompt exceeded UI 3,000-char limit, so a 2,109-char semantic-equivalent prompt was used; 684-byte provider-original; H01-103 PASS |
| 7 | Copilot | `Smart` | `TEXT_SVG / PASS` | explicit `Submit message` click required after Enter did not commit; 676-byte provider-original; H01-103 PASS |
| 8 | Duck.ai | `5.6 Luna / Fast` | `DEFERRED` | no login required; remained actively generating through the 10-minute runtime bound; no complete SVG acquired before clean close |

Counts: `NATIVE_SVG=1`, `TEXT_SVG=5`, `UNSUPPORTED=1`, `DEFERRED=1`. Six acquired SVGs passed H01-103.

## Important provider-specific findings

### Qwen late completion

The first Qwen observer/runtime bound ended while the UI still showed active generation. That timeout was not accepted as a capability verdict. H01-107 reopened the exact persisted Qwen conversation on p001 without resubmitting the prompt. The final response had then completed and contained one clean SVG response leaf. H01-104A persisted it and H01-103 passed it. Therefore Qwen is `TEXT_SVG`, not `DEFERRED`.

### Gemini native file path

Gemini did not present the result as normal assistant SVG code text. The UI exposed `Copy SVG` and `Download SVG`, backed by an SVG preview surface. H01-107 used the provider's `Download SVG` control and preserved the downloaded bytes exactly as `provider-original.svg` before H01-103 validation.

H01-104A v1 is a text-acquisition core whose schema allows `ASSISTANT_DOM` and `CODE_BLOCK`. H01-107 does not falsely claim Gemini's downloaded file passed through that text extractor; its canary records `PROVIDER_FILE_DOWNLOAD / UI_DOWNLOAD_SVG` and validates the exact provider file directly with H01-103.

### Manus prompt limit

The canonical H01-102 prompt is 3,439 characters. Manus UI rejected that payload at `3439 / 3000` before dispatch, so this was not treated as provider capability failure. H01-107 used a 2,109-character semantic-equivalent prompt that preserved subject, composition, commercial intent, rights, vector style, complexity, allowed SVG geometry/commands, forbidden SVG features, and authority invariants.

### Grok bounded unsupported result

Grok Fast accepted the canonical prompt and reached a terminal UI state. After a bounded recheck, the assistant final body still contained only `Worked for 7s`; no complete SVG source, SVG file, blob/.svg link, or SVG download artifact existed. H01-107 therefore records `UNSUPPORTED / EMPTY_FINAL_RESPONSE` for this canary only. This is not a claim that every Grok model or future surface is globally incapable of SVG.

### Duck.ai timeout semantics

Duck.ai required no login and exposed `5.6 Luna / Fast`. It remained actively generating with `Stop generating` visible through the full 10-minute H01-025 runtime bound. Because the provider had not reached a terminal capability result, H01-107 records `DEFERRED / PROVIDER_TIMEOUT`, not `UNSUPPORTED`.

## Runtime hardening discovered by H01-107

A ChatGPT p001 pre-dispatch attempt exposed a transient CDP target with an empty URL after extra-page closure, causing `new URL("")` to fail. `brave_udd_runtime.mjs` now treats an empty/transient target URL as non-terminal and retries provider-origin/cardinality reconciliation for a bounded five seconds. Wrong non-empty origins still fail closed.

The text canary helper also now selects visible composer elements instead of hidden autosize textareas, supports provider-specific submit behavior, adds Duck.ai, and preserves provider-specific evidence without reading cookies, tokens, or session bytes.

## Safety and authority

Every final canary uses p001 sequentially. No concurrent sibling profile is required. No cookie/token/session bytes are read or exported. No provider is promoted by H01-107. Submission and publication remain unauthorized. Browser cleanup is verified for every canary; Duck.ai's runtime status is `FAIL` only because the durable provider result timed out, while process exit, CDP close, and UDD lock release all passed.
