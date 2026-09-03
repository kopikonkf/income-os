# Factory Asset OAUTH Provenance Autopsy v1

**Task:** FA-002
**Date:** 2026-09-03
**Source tree:** `D:\OAUTH` / `kopikonkf/web-ai-adapter`
**Observed HEAD:** `bc155d4279b9a5eefe98113ed64ca32e221a59dc`
**Mode:** READ-ONLY provenance analysis
**Runtime/provider calls performed:** NONE
**Credential values read or published:** NONE

## 1. Scope and safety boundary

This autopsy classifies the Windows OAUTH laboratory into `KEEP`, `EXTRACT`, `REWRITE`, and `RETIRE` boundaries for later Factory integration. The dirty `D:\OAUTH` tree was not reset, cleaned, stashed, copied wholesale, or modified. Raw HAR/session dumps and credential values were not opened or published. The existing text/chat path is treated as a protected baseline and must remain green before and after every future image-provider repair.

The local Git origin is configured with inline authentication material. The value was not read or copied; only the existence of inline authentication was confirmed through a sanitized remote inspection. Remediation belongs to FA-004/FA-005, not this task.

## 2. Repository standing

- `D:\OAUTH` is a dirty experimental tree with many modified tracked provider/wire-protocol files and many untracked research/capture artifacts.
- Canonical `tests/` currently contains no test files.
- Image and text adapters share common core abstractions under `src/core/` and credential loading under `src/utils/auth_store.py`.
- Credential files are resolved from `<PROJECT_ROOT>/credentials/<provider>.json`; this autopsy inspected only code paths, never credential values.
- The current image smoke harness targets `http://127.0.0.1:8456/v1/images/generations` and exercises Qwen, Grok, Gemini, ChatGPT, Manus, Claude and Duck.ai sequentially.

## 3. Protected text/chat baseline

The following text/chat providers are explicitly outside the image-repair mutation scope and must be regression-protected:

| Provider | Existing text transport signal | FA-002 disposition |
| --- | --- | --- |
| Qwen | session cookie + direct `httpx` web-session transport | KEEP baseline; do not break while hardening image lane |
| Gemini | session cookie + direct `httpx` web-session transport | KEEP baseline; do not break while repairing image acquisition |
| Duck.ai | browser/CDP UI transport; anonymous/zero-account flow | KEEP baseline separately from image capability research |
| Other tracked text providers | existing experimental adapters in `src/providers/` | KEEP as unrelated baseline unless a later scoped task says otherwise |

FA-W000 must record a sanitized regression baseline before any provider image repair. No image task may claim success if the existing text/chat path regresses.

## 4. Image-provider provenance matrix

| Provider | Observed code transport | Observed live standing | Provenance disposition | Required next proof |
| --- | --- | --- | --- | --- |
| Qwen | `SESSION_API`: credential/session cookie loaded locally; generation through direct `httpx` + SSE; URLs/base64 parsed and bytes downloaded | HTTP 200 in ~33.4s with large base64 image payload | **EXTRACT** the minimal session transport, SSE parser and byte acquisition; **REWRITE** save/validation/dedupe/error contract; do not copy credential/session material | FA-W002 after common proof contract; original bytes saved, reopened, MIME/magic/dimensions/bytes/SHA-256 validated; text regression green |
| ChatGPT | `HYBRID` candidate: direct `httpx` plus Playwright CDP fallback at a hard-coded local CDP endpoint | failed because CDP endpoint was unavailable | **EXTRACT** only differential behavior and original-byte acquisition concepts; **REWRITE** browser/session ownership, CDP endpoint injection, typed failures and save contract | FA-W003 differential autopsy against proven Proxima/MUXIA, then FA-W004 bounded original-byte proof |
| Gemini | `SESSION_API` candidate: cookie + direct `httpx`; response parser supports inline base64 and URL acquisition | generation returned HTTP 200 / image URL, but no durable original bytes; prior URL path hit 403 | **EXTRACT** response parsing and inline-data handling; **REWRITE** acquisition path to fail closed when original bytes are unavailable | FA-W005 must acquire durable original bytes through an evidenced allowed route; URL-only is failure |
| Grok | WebSocket generation candidate plus HTTP download fallback; code documents `wss` imagine transport | live harness timed out/no image and returned failure | **REWRITE / RE-PROVE**. Preserve capture-derived clues as local evidence, but do not promote current route as working | FA-W006 must prove one supported evidenced route end-to-end; guessed endpoint loops or protection bypass are prohibited |
| Manus | direct HTTP session/canvas candidate with bounded create/send + `GetCanvas` polling + CDN download | polling reached 300s without image artifact | **EXTRACT** bounded polling/artifact parser concepts; **REWRITE / RE-PROVE** trigger semantics and fail-closed byte acquisition | FA-W007 must produce a durable artifact with bounded polling and original-byte validation |
| Duck.ai | text adapter uses browser/CDP; image adapter currently calls Duck chat endpoint through `httpx` and attempts to interpret output as image | current live image harness failed; native image capability is not evidenced | **RETIRE from image-success path** unless capability is later evidenced. KEEP the text adapter separately | FA-W008 either proves a supported native image route or records `UNSUPPORTED_CAPABILITY` |

## 5. Component-level KEEP / EXTRACT / REWRITE / RETIRE map

### KEEP

- `src/core/adapter.py` as the existing text/chat abstraction baseline.
- The concept of `src/core/image_adapter.py` as a provider-neutral image interface; later Factory normalization may replace fields, but the abstraction boundary is useful.
- Existing working text/chat adapters as regression baselines.
- Sanitized historical result summaries that establish what passed or failed.
- Raw captures only as local, access-controlled evidence; they are not publishable implementation assets.

### EXTRACT

- Qwen session transport mechanics, SSE collection, image URL/base64 parsing and byte acquisition behavior.
- Gemini inline-data/base64 response parsing and response-shape handling.
- ChatGPT original-byte/file acquisition behavior that is proven by comparison with Proxima/MUXIA, not the hard-coded browser topology itself.
- Manus bounded polling and typed artifact parsing concepts after the trigger path is re-proven.
- Grok capture-derived protocol observations only after a bounded live proof confirms them.

Extraction means clean-room transfer behind Factory contracts. It explicitly excludes credentials, cookies, raw authenticated captures, hard-coded Windows paths, local browser-profile assumptions and ad-hoc logging.

### REWRITE

- All image save paths currently tied to `D:\ASSETS\OAUTH`; output location must be injected by the common proof/Factory contract.
- Original-byte validation: MIME, magic bytes, decode/reopen, dimensions, byte count and SHA-256 must be mandatory.
- Content-addressed dedupe and idempotent save semantics.
- Provider-specific credential/session objects must remain opaque to Factory Core.
- Hard-coded CDP endpoints/profile assumptions must become explicit provider configuration/lease state.
- URL-only, screenshot-only, HTTP-200-only, text-only and swallowed-download outcomes must fail closed.
- Provider `print()` debugging that can expose URLs, session identifiers or auth context must become sanitized typed observability.
- The empty canonical `tests/` state must be replaced with unit/parser/negative/regression fixtures before promotion.
- The live harness must be split into deterministic regression tests and separately authorized bounded provider canaries.

### RETIRE

- Wholesale import of `D:\OAUTH` into Factory/Linux.
- Raw HAR/session dump/log files as canonical code or publishable receipts.
- Backup/scratch scripts and `.bak` provider implementations as production dependencies.
- Guessed/obsolete endpoints that have already returned 404 or lack evidence.
- Any image adapter that treats a text endpoint, URL-only response, screenshot or inaccessible remote asset as a successful generated image.
- Duck.ai image success claims unless native image generation is actually evidenced.
- Inline Git authentication after FA-005 remediation is completed.

## 6. Capture and evidence handling

The tree contains local raw provider captures, HAR files, session-derived text and live-test logs. They are evidence, not source code. Their existence and filenames may guide provenance, but their authenticated payloads must not be copied into `income-os`, Factory receipts or chat transcripts.

Promotion rule:

```text
raw local evidence
  -> sanitized protocol fact
  -> deterministic fixture with secrets removed
  -> provider contract test
  -> bounded authorized live proof
  -> clean Factory adapter
```

No raw authenticated artifact skips directly into the clean adapter.

## 7. Credential boundary

Current provider adapters load credentials through local provider-specific JSON files. Factory integration must preserve these principles:

1. Factory Core never receives raw cookies, session tokens or browser storage.
2. Each provider principal owns its own opaque auth/session capsule.
3. Credential copying between principals/providers is prohibited.
4. No credential value appears in Git, test fixtures, receipts or logs.
5. Inline Git authentication in the OAUTH repository is a separate security debt; FA-004 designs remediation and FA-005 executes it only with Founder/operator authority.

## 8. Regression and promotion gates

Before any provider repair:

- record sanitized text/chat baseline;
- pin provider transport class;
- pin current failing/success behavior;
- preserve `D:\OAUTH` dirty provenance.

After any provider repair:

- rerun the same text/chat regression;
- require a real generated image;
- require original bytes saved locally;
- reopen/decode the file;
- validate MIME/magic, dimensions, bytes and SHA-256;
- record typed failures without secret/auth leakage.

A responsive endpoint is not an image proof.

## 9. FA-002 acceptance verdict

**PASS.**

The Qwen/Gemini/ChatGPT/Grok/Manus/Duck.ai image code, test state, capture boundary, paths, transport classes and credential boundaries are now classified without reading or publishing secret values. The existing text/chat completion paths are explicitly protected. The dirty `D:\OAUTH` tree remains untouched.

## 10. Next Windows frontier opened by this task

- `FA-004` — Design OAUTH credential and Git remote remediation plan.
- `FA-W000` — Preserve OAUTH text/chat PASS and Qwen image baseline.

These may proceed as separate atomic tasks. Provider repair itself does not begin in FA-002.
