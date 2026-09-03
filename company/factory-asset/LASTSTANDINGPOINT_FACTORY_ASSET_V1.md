# LASTSTANDINGPOINT â€” Factory Asset Level Up v1

**Date:** 2026-09-03  
**Lane:** WINDOWS_OAUTH_LAB  
**Current income-os base after FA-W002 canonicalization:** e9a26de50d23eb866b9fefaac394df686a01b9e8
**Session-start income-os main:** 5bbbd6a3db08552786e0e3f2ff7efc43eb29a71e

## Windows standing

### FA-W002 â€” DONE / PASS

- Existing September 3 real Qwen evidence was reused; **new live Qwen calls = 0**.
- Primary artifact: `D:\ASSETS\OAUTH\2026-09-03\qwen_032a7cf1.png` â€” PNG, 2048x2048, 3,821,821 bytes, SHA-256 `54f54a263a09e3246a0b9414b665f8ab232fa7bf04f51d786ffc008921929105`, decode/reopen PASS.
- Second artifact: `D:\ASSETS\OAUTH\2026-09-03\qwen_192aa4c7.png` â€” PNG, 2048x2048, 3,629,969 bytes, SHA-256 `7ff36bf614b399e017e2fea942ac15af2373b341d93d648f250ab0e9923a8901`, decode/reopen PASS.
- Hardened Qwen persistence is merged in `web-ai-adapter` PR #1, merge `a301fd7e9c90931566ae877c976c3fbf0f65bdd1`.
- Strict magic/MIME/dimensions/decode validation, SHA-256 content addressing, atomic save, dedupe and non-silent failures are implemented.
- Real-artifact replay and deterministic tests PASS.
- Text/chat baseline remains PASS by FA-W000; FA-W002 did not modify the Qwen text adapter.
- Receipt: `company/factory-asset/receipts/FA-W002-qwen-image-proof.receipt.json`.

### FA-W004 â€” DONE / PASS

- Real operator-controlled ChatGPT generation completed in authenticated Brave profile `jarvis_aco`; the implementation/preflight profile `factory-asset-chatgpt-primary` was not falsely claimed as the generation profile.
- Prompt SHA-256: `0c93230f694582d9f16c0f90e8437da39c5dc14f6db30e6bebb6e09545a0c1c3`.
- Provider original: `D:\ASSETS\OAUTH\2026-09-03\ChatGPT Image Sep 3, 2026, 06_17_24 AM.png`.
- Strict validation: PNG, 1254x1254, 776,389 bytes, decode/reopen PASS, SHA-256 `05d8135e4e6bebc3f7dc7baca49cd3a70e768e096bafdbb9e0fa96b734fa1e65`.
- Content-addressed local save: `D:\ASSETS\OAUTH\sha256\05\chatgpt_05d8135e4e6bebc3f7dc7baca49cd3a70e768e096bafdbb9e0fa96b734fa1e65.png`.
- Actual acceptance transport is truthfully classified `BROWSER_OPERATOR`: manual consumer-web generation/download plus automated strict local validation. This is not claimed to be Proxima-like autonomous prompt-to-download.
- Common proof contract v1.1 adds `BROWSER_OPERATOR` so policy-compliant manual original-download evidence is not mislabeled as CDP automation.
- Receipt: `company/factory-asset/receipts/FA-W004-chatgpt-image-proof.receipt.json`.

### FA-W005 â€” DONE / PASS

- Founder/operator supplied a real Gemini provider-original JPEG from the authenticated consumer web UI using the shared prompt in `prompt.txt`.
- Strict validation: JPEG, 1024x1024, 359,349 bytes, decode/reopen PASS, SHA-256 `cd866318223134624f0852e2ef5ddac421544469145272cb6339c57a62fd1012`.
- Content-addressed local save: `D:\ASSETS\OAUTH\sha256\cd\gemini_cd866318223134624f0852e2ef5ddac421544469145272cb6339c57a62fd1012.jpg`.
- Actual proof transport: `BROWSER_OPERATOR`; the legacy inaccessible URL/403 fallback path was not used.
- Receipt: `company/factory-asset/receipts/FA-W005-gemini-image-proof.receipt.json`.

### FA-W006 — DONE / PASS

- Founder/operator supplied a real Grok provider-original JPEG from the authenticated consumer web UI using the shared prompt in `prompt.txt`.
- Strict validation: JPEG, 784x1168, 102,354 bytes, decode/reopen PASS, SHA-256 `18087c41cf26d783edcb4c6630e9325dc15973f1e1cac9bb0858ce51f0e4ebdd`.
- Content-addressed local save: `D:\ASSETS\OAUTH\sha256\18\grok_18087c41cf26d783edcb4c6630e9325dc15973f1e1cac9bb0858ce51f0e4ebdd.jpg`.
- EXIF signature metadata is present as supporting provenance but its raw signature blob is intentionally not copied into canonical receipts.
- Actual proof transport: `BROWSER_OPERATOR`; no guessed endpoint loop or protection bypass was used.
- Receipt: `company/factory-asset/receipts/FA-W006-grok-image-proof.receipt.json`.

### FA-W007 — DONE / PASS

- Founder/operator supplied a real Manus provider-original PNG from the authenticated consumer web UI using the shared prompt in prompt.txt.
- Strict validation: PNG, 1920x1920, 788,616 bytes, decode/reopen PASS, SHA-256 53768478e5ef09498f5df735f89e71f49bbbcfe39a89ec1f9f24abbf840923a.
- Content-addressed local save: D:\\ASSETS\\OAUTH\\sha256\\a5\\manus_a53768478e5ef09498f5df735f89e71f49bbbcfe39a89ec1f9f24abbf840923a.png.
- Actual proof transport: BROWSER_OPERATOR. The task acceptance is clarified so browser-operator original export proves Windows capability; any future SESSION_API create/poll route must remain bounded and cannot pass on status without artifact.
- Receipt: company/factory-asset/receipts/FA-W007-manus-image-proof.receipt.json.

### FA-W008 — DONE / PASS

- Founder/operator supplied a real Duck.ai provider-original JPEG using the shared prompt in `prompt.txt`.
- Founder/operator reports the current Duck.ai UI model label as `gpt5.5 luna`; this label is recorded as operator-observed, not independently verified by Architect transport.
- Strict validation: JPEG, 1254x1254, 42,740 bytes, decode/reopen PASS, SHA-256 `4086a14f2b8bca067941bd5f377ec675caff1c9ae77b92a40dc221f49d492cf9`.
- Exact VPS file hash matches the file uploaded by Founder in ChatGPT, eliminating local-vs-chat artifact ambiguity.
- Content-addressed local save: `D:\ASSETS\OAUTH\sha256\40\duckai_4086a14f2b8bca067941bd5f377ec675caff1c9ae77b92a40dc221f49d492cf9.jpg`.
- Actual proof transport: `BROWSER_OPERATOR`; the prior text-only endpoint is not counted as image proof.
- Receipt: `company/factory-asset/receipts/FA-W008-duckai-image-proof.receipt.json`.

### FA-W009 — DONE / PASS — Six-provider Windows acceptance

- Six of six provider proofs are terminal PASS: Qwen, ChatGPT, Gemini, Grok, Manus and Duck.ai.
- Acceptance-time local recheck reopened all six exact VPS files and recomputed SHA-256; every hash matches its canonical provider receipt.
- Qwen transport is `SESSION_API`; ChatGPT, Gemini, Grok, Manus and Duck.ai are `BROWSER_OPERATOR`.
- PASS means each provider has real-generation provider-original bytes saved durably on the Windows VPS with MIME/magic/dimensions/positive-byte/SHA-256/decode evidence.
- This does **not** claim that all six are fully autonomous like Proxima: five browser lanes currently use operator generation/manual provider-original download followed by automated strict local ingestion.
- Receipt: `company/factory-asset/receipts/FA-W009-six-provider-windows-acceptance.receipt.json`.

## Founder decision — Autonomous backend candidacy pivot

Founder approved the next Windows/OAUTH phase on 2026-09-03:

- preserve `FA-W002` through `FA-W009` as Level-1 real-provider/original-byte capability evidence;
- treat Qwen `SESSION_API` as the already-proven zero-touch-after-dispatch backend reference;
- require a stricter Level-2 contract before Gemini, Grok, Manus and Duck.ai can become backend candidates;
- Level-2 PASS requires job/prompt dispatch -> bounded provider completion -> provider-original bytes -> strict validation -> atomic durable local save with **zero operator action after dispatch**;
- ChatGPT may use the existing MUXIA/server boundary later and is explicitly non-blocking for the five-provider Level-2 acceptance;
- GenWHITE purchase/account action is HOLD. GenWHITE remains a future clean-room observable capability benchmark, not a backend assumption or dependency.

Current Level-2 frontier: `FA-W011` — define the common autonomous provider backend contract. After that, execute Gemini -> Grok -> Manus -> Duck.ai in priority order.

### FA-W011 — DONE / PASS — Level-2 autonomous backend contract

- Canonical contract: `company/factory-asset/contracts/windows-autonomous-provider-backend-v1.json` v1.0.0.
- Zero-touch checkpoint is `dispatch_committed_at`: operator authentication/recovery is allowed before it; after it, **operator actions must equal zero** until terminal state.
- Level-2 PASS transports: `SESSION_API`, `BROWSER_CDP`, `HYBRID`, `OFFICIAL_API`. `BROWSER_OPERATOR` is explicitly Level-2 non-PASS.
- PASS requires bounded real generation/completion, backend-acquired provider-original bytes, MIME/magic/dimensions/decode/SHA-256 validation, atomic content-addressed durable save, post-save hash/reopen, typed receipt and no security/policy bypass.
- Default retry budget is at most two retries / three total attempts; timeout and cancellation are terminal and cannot be relabeled as success.
- Twelve mandatory negative acceptance cases cover manual download, URL-only/download failure, status-without-artifact, timeout, invalid bytes, hash mismatch, post-dispatch auth/protection, retry exhaustion and dedupe.
- No `D:\OAUTH` source mutation and no live provider call occurred in FA-W011.
- Receipt: `company/factory-asset/receipts/FA-W011-autonomous-provider-backend-contract.receipt.json`.

### FA-W013 — WAITING_OPERATOR — Gemini dedicated backend authentication

- Gemini Level-2 implementation is merged in `web-ai-adapter` PR #3, merge `65227657a10199da31be093f0a36a8d26447e1a3`, and scoped-deployed to `D:\OAUTH`.
- Current transport is `BROWSER_CDP` using dedicated profile `D:\OAUTH\browser-profiles\gemini-backend` on loopback `127.0.0.1:9333`; no cookie/session-token export is used.
- Deterministic + regression suite: **23/23 PASS**; server import PASS; unrelated dirty work fingerprint preserved.
- The historical `StreamGenerate` SESSION_API bootstrap is stale for current acceptance: `/app` returned 200 and `cfb2h` but no `SNlM0e`; no generation dispatch was committed on that diagnostic.
- One anonymous BROWSER_CDP attempt was committed before auth-state detection was corrected; Gemini returned text saying image creation was unavailable, with no image/download control. It is terminal FAILED/AUTH_REQUIRED and cannot be relabeled PASS.
- Preflight is now fail-closed: visible `Sign in` => `AUTH_REQUIRED` before dispatch.
- **Operator action required now:** sign in to Gemini in the already-open dedicated Gemini backend browser only; do not send a prompt and do not download anything. Leave the browser running and report `done`. No new Founder authorization is required.
- Receipt: `company/factory-asset/receipts/FA-W013-gemini-autonomous-backend.receipt.json`.

## OAUTH safety

- `D:\OAUTH` HEAD remains `c2fb61467138a24156b3d61c991882ebcdd59086`.
- Dirty count after scoped W002/W004 deploy: 67.
- Pre-existing unrelated dirty work is preserved; target-excluded digest remained identical before/after each scoped deployment.
- OAUTH server root HTTP 200; `/health` HTTP 200.
- No reset, stash, clean or credential/session export occurred.

## Next Windows frontier

`FA-W013` remains the sole Windows frontier at `WAITING_OPERATOR` for **pre-dispatch Gemini login only**. The dedicated browser worker is already running on loopback CDP. After login, Architect must re-preflight and perform the next distinct bounded attempt; Grok remains blocked until FA-W013 reaches a terminal state.

## Engineering lease

Any income-os publication must acquire `income-os.repo-write` plus the task-specific Factory Asset lease and release both in `finally`. Do not preempt the Linux hourly runner.
