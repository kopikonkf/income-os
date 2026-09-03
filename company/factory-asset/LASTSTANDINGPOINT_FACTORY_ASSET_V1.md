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

Current Level-2 frontier: `FA-W014` — Grok autonomous backend original-byte local save. FA-W013 Gemini is DONE/PASS; Manus and Duck.ai remain sequenced behind Grok.

### FA-W011 — DONE / PASS — Level-2 autonomous backend contract

- Canonical contract: `company/factory-asset/contracts/windows-autonomous-provider-backend-v1.json` v1.0.0.
- Zero-touch checkpoint is `dispatch_committed_at`: operator authentication/recovery is allowed before it; after it, **operator actions must equal zero** until terminal state.
- Level-2 PASS transports: `SESSION_API`, `BROWSER_CDP`, `HYBRID`, `OFFICIAL_API`. `BROWSER_OPERATOR` is explicitly Level-2 non-PASS.
- PASS requires bounded real generation/completion, backend-acquired provider-original bytes, MIME/magic/dimensions/decode/SHA-256 validation, atomic content-addressed durable save, post-save hash/reopen, typed receipt and no security/policy bypass.
- Default retry budget is at most two retries / three total attempts; timeout and cancellation are terminal and cannot be relabeled as success.
- Twelve mandatory negative acceptance cases cover manual download, URL-only/download failure, status-without-artifact, timeout, invalid bytes, hash mismatch, post-dispatch auth/protection, retry exhaustion and dedupe.
- No `D:\OAUTH` source mutation and no live provider call occurred in FA-W011.
- Receipt: `company/factory-asset/receipts/FA-W011-autonomous-provider-backend-contract.receipt.json`.

### FA-W013 — DONE / PASS — Gemini autonomous backend original-byte local save

- Founder/operator completed authentication **before dispatch only** in the dedicated `D:\OAUTH\browser-profiles\gemini-backend` profile; acceptance preflight then returned `READY` on loopback CDP `127.0.0.1:9333`.
- Exactly one new bounded authenticated acceptance attempt was committed. Backend prompt dispatch, completion detection, original-byte acquisition, validation and durable save completed with **operator_actions_after_dispatch = 0**.
- Job: `gemini-634d52e07eca4f2aa3fc0d028a9ef6c9`; attempt: `attempt-407aabdebbff461c9aba74e7f934b939`.
- Prompt SHA-256: `a450e24f12533528a03e3c3ad14d40bebe26cc6e30c221929806e5256ad166d9`; plaintext prompt is not required in the canonical receipt.
- `dispatch_committed_at`: `2026-09-03T08:49:30.081665Z`; generation completed at `2026-09-03T08:49:54.135837Z`.
- Original acquisition: **provider browser download event captured automatically by backend**; no manual download, URL copy, browser recovery, screenshot or output-folder move occurred after dispatch.
- Artifact: `D:\ASSETS\OAUTH\sha256\c0\gemini_c04c5d7651d2133d338307627b60b2eba09069d90f9fdc8873f2c76a52a0c52d.jpg`.
- Strict + independent recheck: JPEG, 1408x768, 401,525 bytes, magic `ffd8ffe000104a4649460001`, decode/reopen PASS, SHA-256 `c04c5d7651d2133d338307627b60b2eba09069d90f9fdc8873f2c76a52a0c52d`.
- Post-acceptance canonical regression scope: **23/23 PASS**. A broad unscoped `pytest -q` also exposed pre-existing duplicate staging-package collection errors under `staging/gemini` and `staging/mimo`; these are not part of the canonical FA-W013 23-test regression scope and were not silently described as green.
- Historical anonymous BROWSER_CDP attempt remains terminal FAILED/AUTH_REQUIRED and was not relabeled.
- Receipt: `company/factory-asset/receipts/FA-W013-gemini-autonomous-backend.receipt.json`.

## OAUTH safety

- `D:\OAUTH` HEAD remains `c2fb61467138a24156b3d61c991882ebcdd59086`.
- Dirty count after scoped W002/W004 deploy: 67.
- Pre-existing unrelated dirty work is preserved; target-excluded digest remained identical before/after each scoped deployment.
- OAUTH server root HTTP 200; `/health` HTTP 200.
- No reset, stash, clean or credential/session export occurred.

## Next Windows frontier

`FA-W014` is now the next Windows frontier at `READY` for **Grok autonomous backend original-byte local save**. FA-W013 Gemini is DONE/PASS. Do not execute Grok in the same FA-W013 acceptance run.

## Engineering lease

Any income-os publication must acquire `income-os.repo-write` plus the task-specific Factory Asset lease and release both in `finally`. Do not preempt the Linux hourly runner.

## 2026-09-03 Windows Level-2 continuation: Grok -> Manus -> Duck.ai

### FA-W014 — DEFERRED / PROVIDER_CAPACITY_UNAVAILABLE

- Founder age confirmation was already complete before this continuation.
- Fresh Grok `BROWSER_CDP` preflight was READY: authenticated page, composer available, no sign-in gate, no visible hCaptcha.
- A fresh bounded retry was committed at `2026-09-03T14:58:21.422782Z` with `operator_actions_after_dispatch = 0`.
- Provider terminated immediately in `HIGH_DEMAND`: `Grok is under heavy usage right now`.
- No provider-original bytes were acquired and no artifact was saved; this attempt is **not PASS**.
- The historical Founder-interrupted generation remains excluded from PASS.
- Founder explicitly authorized continuing to Manus when this retry remained blocked by provider capacity. This is a sequencing override only; the Level-2 acceptance boundary is unchanged.
- Receipt: `company/factory-asset/receipts/FA-W014-grok-autonomous-backend.receipt.json`.

### FA-W015 — DONE / PASS — Manus autonomous backend original-byte local save

- Manus `BROWSER_CDP` preflight was READY on the existing authorized browser profile with no visible hCaptcha or login gate.
- One bounded job was committed at `2026-09-03T14:59:30.840023Z`; `operator_actions_after_dispatch = 0` through terminal state.
- A first `520x293` `files.manuscdn.com` WebP was detected and correctly rejected as Manus Desktop UI artwork, preventing a false-positive receipt.
- The backend subsequently acquired the actual provider-generated artifact from `private-us-east-1.manuscdn.com` before deadline.
- Provider-original artifact: PNG, `1920x1920`, `1,747,032` bytes, SHA-256 `39c545d2646502553737e5096d90fd2e5060fa46d71bea02a99b72ed50ee52a2`.
- Atomic content-addressed save: `D:\ASSETS\OAUTH\sha256\39\manus_39c545d2646502553737e5096d90fd2e5060fa46d71bea02a99b72ed50ee52a2.png`.
- Decode/reopen and post-save SHA-256 verification PASS.
- Receipt: `company/factory-asset/receipts/FA-W015-manus-autonomous-backend.receipt.json`.

### FA-W017 — READY / latest bounded attempts NOT PASS

- Duck.ai current browser UI exposed `5.6 Luna` and the image lane as `GPT Image 2`; the historical text-only `/duckchat/v1/chat` route is still not counted as image proof.
- The backend did produce a provider-delivered JPEG data URI (`1254x1254`, SHA-256 `659da1be155fea7b043b2c71530e422dd457aadf40fb1c59208cc9119e690552`), but acquisition/save for that attempt did not complete inside its recorded deadline, so it is not Level-2 PASS.
- A later same-attempt provenance check observed the same hash re-rendered in the DOM; that prior artifact was explicitly excluded rather than mislabeled as a new generation.
- The subsequent committed retry ended `BOUNDED_COMPLETION_TIMEOUT` without a new-hash provider artifact before deadline; `operator_actions_after_dispatch = 0`.
- Wrapper-created duplicate backend processes were stopped and are not counted as provider-committed attempts unless the provider UI surfaced a corresponding submitted message.
- Receipt: `company/factory-asset/receipts/FA-W017-duckai-autonomous-backend.receipt.json`.

## Current Windows frontier after this continuation

`FA-W015` is DONE/PASS. `FA-W014` is DEFERRED on temporary Grok provider capacity, not auth. `FA-W017` is the active READY frontier for one fresh bounded Duck.ai retry under the remaining default provider-committed attempt budget. No Grok or Duck failure has been relabeled as PASS.


### 2026-09-03 FA-W014 Grok Imagine preflight — DEFERRED / SPEND_REQUIRED

- Founder-directed route `https://grok.com/imagine` was opened in the owned authenticated CDP profile.
- Authentication was valid and the Imagine composer existed, but the route presented `Upgrade to SuperGrok` / `Unlock your creativity with Imagine` before any generation dispatch.
- No provider generation attempt was committed on this route; `dispatch_committed_at` remained unset and no post-dispatch operator action occurred.
- This is recorded as `SPEND_REQUIRED / SUPERGROK_UPGRADE_GATE`, not as PASS and not as a provider-capacity failure.
- The earlier Grok chat-route committed attempt remains terminal `FAILED / PROVIDER_CAPACITY_UNAVAILABLE / HIGH_DEMAND` and is not relabeled.


### FA-W017 — DONE / PASS — Duck.ai autonomous backend original-byte local save

- A fresh bounded Duck.ai `BROWSER_CDP` retry was committed at `2026-09-03T15:42:36.713306Z`; `operator_actions_after_dispatch = 0` through terminal PASS.
- Provider-original bytes were acquired automatically from the provider-delivered image data URI in the owned browser DOM; no manual click, refresh, completion confirmation, download or file placement occurred after dispatch.
- Fresh artifact: JPEG, `1254x1254`, `55,152` bytes, SHA-256 `f2b213037b06e9e46d20e51994bff8eb339d20c1f2beffd681cafa296dc917bf`.
- Atomic content-addressed save: `D:\ASSETS\OAUTH\sha256\f2\duckai_f2b213037b06e9e46d20e51994bff8eb339d20c1f2beffd681cafa296dc917bf.jpg`.
- Decode/reopen, byte count and post-save SHA-256 verification PASS; an independent second recheck also matched exact bytes/hash/dimensions.
- Historical Duck hashes `4086a14f...` and `659da1be...` remain historical-only and were not reused as fresh proof.
- `FA-W019` remains blocked only because `FA-W014` Grok Level-2 is unresolved; ChatGPT/MUXIA `FA-W016` remains explicitly non-blocking.

## 2026-09-03 Browser-CDP unification decision

### FA-W016 — DONE / PASS — ChatGPT standalone shared BROWSER_CDP

- Founder chose a uniform Browser-CDP lane for browser-backed web-chat-AI while keeping `web-ai-adapter` independently runnable.
- Canonical `web-ai-adapter` PR #4 merged as `c0b0fd803301d0e78c3a108a6a7de164acfa7314`.
- ChatGPT no longer requires the prior operator-only FA-W004 image boundary for Level-2: the standalone adapter attaches to the reusable authenticated CDP profile, submits automatically, acquires provider-original bytes through the authenticated browser context, validates and atomically saves them.
- Accepted canonical-source run: `dispatch_committed_at=2026-09-03T17:02:39.629718Z`, `operator_actions_after_dispatch=0`, PNG `1254x1254`, `735850` bytes, SHA-256 `55da7f72825ebbfe2cfacf75b28660164be5a87b986182d05f74584dda0ffb9a`, independent hash/decode/reopen PASS.
- One earlier committed source-candidate attempt ended `BOUNDED_COMPLETION_TIMEOUT` and remains terminal FAILED; it was not relabeled.
- `web-ai-adapter` remains the OpenAI-compatible/provider-normalization layer. `BROWSER_CDP` is the shared browser transport boundary. MUXIA is the later shared Chromium/profile runtime substrate, not a competing provider adapter.

### New Windows/OAUTH tasks from the architecture decision

- `FA-W018 = READY`: add Qwen `BROWSER_CDP` fallback while preserving proven `SESSION_API` as primary.
- `FA-W020 = BLOCKED on FA-W018`: leverage MUXIA as shared Browser-CDP runtime without duplicating provider/OpenAI normalization or browser ownership.
- `FA-W021 = BLOCKED on FA-W020`: prove standalone `web-ai-adapter` and MUXIA-backed modes can coexist so production can stay on the known-good standalone path during MUXIA hardening and switch only after green acceptance.
- `FA-W019` remains independently blocked by Grok Level-2 (`FA-W014`); ChatGPT and Qwen fallback do not lower or rewrite that five-provider acceptance boundary.


### FA-W018 — DONE / PASS — Qwen BROWSER_CDP fallback

- Qwen SESSION_API remains the default/primary transport. QWEN_IMAGE_TRANSPORT=BROWSER_CDP selects the explicit browser fallback.
- web-ai-adapter PR #5 merged as 99409665122ff6ca5467c38b41d8630b59471f53.
- The earlier committed browser attempt timed out because the visible Qwen CDN image was a resized preview using x-oss-process; that attempt remains FAILED.
- The adapter now preserves the signed CDN key while removing the preview transform to fetch provider-original bytes.
- Fresh accepted run: zero operator actions after dispatch, PNG 1664x928, 1,395,714 bytes, SHA-256 95b2dc3e3e587c729cdf18cf96c93dc7130c015bfba9f6a3597c2dd7444368eb, atomic content-addressed save and independent decode/reopen/hash PASS.
- FA-W020 is now READY: leverage MUXIA as the shared Browser-CDP runtime while keeping standalone web-ai-adapter available.


### FA-W020 — DONE / PASS — MUXIA shared Browser-CDP runtime

- `web-ai-adapter` PR #6 merged as `cd102e8f3d473718adbc7c304df9a9babc4095e2`; browser-backed canonical adapters now support explicit `STANDALONE` or `MUXIA` runtime resolution.
- MUXIA remains browser lifecycle/profile/CDP owner; `web-ai-adapter` remains provider/OpenAI normalization. No duplicate browser engine was introduced.
- Physical proof used an isolated Linux MUXIA profile under `/home/kopiko`, not production profiles or queues. MUXIA emitted sanitized `DIRECT_SPAWN_LOOPBACK_CDP` status with browser PID `527610` and `127.0.0.1:33609`.
- Through an authenticated SSH local tunnel, Windows `web-ai-adapter` consumed the copied sanitized status and `ChatGPTImageAdapter.preflight()` reached provider-level `AUTH_REQUIRED`, proving successful attachment while correctly refusing to dispatch on an unauthenticated fresh profile.
- No cookie/token value was read or copied, no provider prompt was sent, and the isolated browser/tunnel were terminated after proof.
- Canonical MUXIA wrapper: `company/muxia/scripts/linux/muxia-webai-browser-runtime.mjs`.
- `FA-W021` is now READY for explicit coexistence + rollback-safe continuity proof.


### FA-W021 — DONE / PASS — standalone + MUXIA coexistence / rollback continuity

- Canonical MUXIA wrapper from FA-W020 was copied only into an isolated operator-home test tree and launched with a fresh temporary profile; live production profiles, queues and services were untouched.
- While the isolated MUXIA runtime was alive at remote loopback `127.0.0.1:45235`, standalone Windows `web-ai-adapter` remained `READY` on `127.0.0.1:9333`.
- Explicit `WEB_AI_BROWSER_RUNTIME=MUXIA` + sanitized status file resolved the MUXIA endpoint and reached provider-level `AUTH_REQUIRED`, proving attachment without credential copy or provider dispatch.
- Switching back to `STANDALONE` while MUXIA remained alive returned `READY`; after terminating the isolated MUXIA browser and SSH tunnel, standalone preflight remained `READY`.
- Therefore standalone production/lab operation can continue during MUXIA hardening, and cutover can remain explicit/reversible. No cutover was performed by this task.


### FA-013 — DONE / PASS — Asset Blueprint v2 validator/compiler

- Added concrete six-mode asset registry `asset-types.v1.json`: PHOTO, ISOLATED_OBJECT, ICON, OUTLINE, PATTERN, ANIMATION, all validated against the FA-010 registry schema.
- Compiler validates schema + asset family/native representation + producer + master format + family QA before producing a deterministic `die.factory-asset.production-plan.v1`.
- Deterministic recipes are selected for raster, native/procedural vector and motion masters/derivatives. Raster→SVG/EPS, raster/vector→motion, and unsupported motion derivatives fail before dispatch.
- Marketplace profile evidence is fail-closed: `COMPATIBLE` cannot be claimed against UNKNOWN/stale profiles, and an evidenced marketplace delivery format must actually be supported by the selected pinned profile.
- CLI smoke initially exposed a dynamic-import/dataclass bug; it was repaired and added as a permanent subprocess regression.
- Validation: Factory Asset tests 30/30 PASS, registry schema PASS, Python compile PASS, diff check PASS.
- `FA-014` remains READY. `FA-015` stays BLOCKED until FA-014 is DONE.


### FA-014 — DONE / PASS — semantic versus packaging identity invariants

- Added deterministic semantic fingerprint over asset type + normalized commercial use case + subject + intent.
- Added separate packaging fingerprint over master spec, derivatives and marketplace routing state.
- Format/resolution/preview/derivative/marketplace-route changes remain packaging variants and must retain `semantic_asset_id`.
- Reusing a semantic ID after changing commercial use case, subject, intent or asset type is rejected; a semantic variant also requires a separate `blueprint_id`.
- Derivative order is normalized and cannot create artificial packaging identity drift.
- Asset Blueprint v2 has no compression field, therefore compression cannot participate in semantic identity; represented file/format/resolution/preview fields are explicitly packaging-only.
- Validation: full Factory Asset test set 43/43 PASS.
- Both FA-013 and FA-014 are DONE; `FA-015` is now READY for six shopping-bag mode fixtures.
