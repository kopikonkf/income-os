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


### Founder decision — Grok removed from Factory critical path / Factory Console ratified

- `FA-W014` Grok Level-2 remains `DEFERRED` and optional. Its current SuperGrok/platform gate is outside Factory control; no spend or bypass is authorized.
- `FA-W019` is redefined and accepted against the current proven autonomous pool: Qwen, ChatGPT, Gemini, Manus and Duck.ai. Grok is not required for Factory progression.
- `FA-W010` clean-room GenWHITE observable-capability benchmark is now READY; purchase/account action remains prohibited unless separately Founder-authorized.
- New `FACTORY_CONSOLE` track `FA-C000..FA-C013` is canonical. Console is a Founder-operated control plane over Factory Core, not a provider/browser/orchestration engine.
- GUI shell/design can begin early on synthetic data; production queue/provider authority remains gated on Factory Core and later canaries.


### FA-015 — DONE / PASS — shopping-bag six-mode Blueprint v2 fixtures

- Added six positive semantic fixtures: PHOTO, ISOLATED_OBJECT, ICON, OUTLINE, PATTERN and ANIMATION.
- Each compiles deterministically through FA-013 to its intended raster/vector/procedural/motion producer and master/derivative recipes.
- Identity checks prove six unique semantic IDs/fingerprints while all twelve packaging derivatives retain the parent semantic asset.
- Registry and marketplace profile revisions are pinned at `1.0`; Adobe Stock is the evidence-pinned compatibility target in these fixtures.
- Factory Asset regression: 48/48 PASS.
- `FA-019` is now READY for positive + negative cross-family Blueprint v2 acceptance.


### FA-019 — DONE / PASS — Asset Blueprint v2 acceptance

- Positive: all six shopping-bag semantic modes compile to intended native producers and deterministic delivery recipes with registry/profile revisions pinned at `1.0`.
- Negative: six cross-family fixtures fail closed with typed errors; raster/vector/motion family boundaries cannot be bypassed by changing extensions or delivery intent.
- Identity: six semantic assets remain distinct while packaging derivatives retain the parent semantic ID.
- Full Factory Asset regression: 53/53 PASS.
- Newly READY frontiers: `FA-020` derivative recipe/receipt schemas, `FA-025` vectorizability gate, `FA-031` native producer contract, and `FA-100` provider capability/generation contract.
- Factory Console remains staged: `FA-W010` clean-room benchmark is READY; `FA-C001` waits for that benchmark, while later Console binding waits for Factory Core as designed.


### FA-W010 — DONE / PASS — GenWHITE clean-room capability benchmark
- Publicly observable Auto-Pilot, auto-download/save-load, 2K/4K, style/consistency/background controls mapped to Factory-owned requirements.
- Queue internals, pause/resume semantics, retry/rate-limit telemetry and backend mechanism remain UNKNOWN.
- No purchase/account action/proprietary-code access. `FA-C001` is now READY.


### FA-020 — DONE / PASS — derivative recipe and receipt contracts
- Strict schemas pin master hash, recipe/version, marketplace profile revision, output spec, idempotency, QA and compatibility.
- PASS cannot hide decode/hash/magic failure or UNKNOWN compatibility; packaging derivatives cannot mint semantic identity.
- Factory regression 58/58 PASS. `FA-021` and `FA-023` are READY.


### FA-025 — DONE / PASS — vectorizability gate
- Deterministic gate returns NATIVE_VECTOR, TRACE_ELIGIBLE or NOT_VECTORIZABLE with evidence/reason codes.
- Photorealistic, complex, font-dependent, unauthorized and incomplete raster inputs fail closed.
- Factory regression 63/63 PASS. `FA-026` and `FA-027` are READY.


### FA-031 — DONE / PASS — native producer dispatch contract
- Shared request/receipt contract covers procedural vector, motion, layered-template and 3D native producers with cancellation/idempotency/failure semantics.
- PASS requires a native editable producer output; raster conversion cannot masquerade as native master.
- Factory regression 73/73 PASS. `FA-032` and `FA-040` are READY.


### FA-100 — DONE / PASS — provider capability and generation contract
- Provider-neutral CAPABILITY, GENERATE_REQUEST, GENERATE_RESULT and HEALTH envelopes cover SESSION_API/BROWSER_CDP/HYBRID/OFFICIAL_API.
- PASS requires zero post-dispatch operator actions plus validated provider-original durable bytes; typed failures cannot include fake artifacts.
- Vendor cookie/session/RPC/endpoint/raw-wire fields are rejected. Current Qwen/ChatGPT/Gemini/Manus/Duck pool fits the same contract.
- Factory regression 83/83 PASS. `FA-101` and `FA-103` are READY.


### FA-C001 — DONE / PASS — Factory Console capability matrix
- GenWHITE-observable patterns are translated into Factory-owned requirements; unsupported queue/retry/rate-limit/recovery internals remain UNKNOWN.
- Five primary surfaces are fixed: Blueprint, Batch, Queue, Providers and Output.
- GUI remains a control plane only. `FA-C002` is READY.


### FA-C002 — DONE / PASS — Factory Console PRD / information architecture
- Founder workflows and five-view IA are explicit, with normalized job/provider/capacity/QA states and synthetic fixture contract.
- Prototype implementation is a zero-dependency static HTML/CSS/JS shell; live execution remains out of scope.
- `FA-C004` is READY.


### FA-C004 — DONE / PASS — Factory Console synthetic GUI shell
- Zero-dependency static HTML/CSS/JS shell exposes Blueprint, Batch, Queue, Providers and Output views over deterministic synthetic fixtures.
- Queue controls are SIMULATED only; live dispatch is locked; current five-provider pool plus optional/deferred Grok are visible.
- Output gallery keeps semantic count distinct from derivative count.
- Factory regression 92/92 PASS; JS syntax PASS. Headless browser smoke was unavailable in Architect service context and is not claimed.
- FA-C005 is READY.


### FA-C005 — DONE / PASS — real Blueprint editor + compile preview + batch intent
- Console now serves loopback-only with a real `/api/compile` bridge to canonical `blueprint_compiler.py` and identity fingerprints.
- All six canonical asset types compile from editor templates; invalid family/format edits fail closed.
- Master/resolution/delivery/style controls preserve semantic identity unless semantic fields/type change; packaging fingerprint changes independently.
- `/api/batch-intent` requires a successful compile, bounds quantity to 1..1000, separates semantic count from derivative count, and remains `SIMULATED_ONLY`.
- Factory regression 107/107 PASS; loopback HTTP compile PASS; no provider dispatch/credential/production-queue/marketplace action.


### FA-101 — DONE / PASS — provider profile + lease contract
- Credentials remain opaque references; duplicate/cross-profile ownership fails closed.
- Regression 112/112 PASS. `FA-102` is READY.


### Factory Core + Console control batch — DONE / PASS
- `FA-101` provider profile/lease: DONE; opaque credentials and single ownership.
- `FA-102` observed capacity ledger: DONE; dated evidence only, stale -> UNKNOWN, guessed quota forbidden.
- `FA-103` provider policy gate: DONE; five current providers allowed by dated route evidence, Grok deferred; unknown/stale blocks.
- `FA-104` deterministic router: DONE; policy + AVAILABLE capacity + capability hard gates with rationale.
- `FA-105` queue/retry/resume/reconciliation: DONE; idempotent jobs, max two retries, crash RUNNING -> READY, no false success.
- `FA-C003` normalized Console/Core API: DONE; vendor/browser/credential wire fields rejected.
- `FA-C006` governed Queue controls: DONE; START/PAUSE/RESUME/CANCEL/RETRY call FA-105 locally, provider dispatch remains disabled.
- Final regression before publication: 159/159 PASS. `FA-107` is READY; `FA-C007` still waits for FA-107, and `FA-C008` waits for FA-030 + FA-106.


### FA-107 — DONE / PASS — sanitized Factory observability
- Attempts, unique masters, QA assets, derivatives, packages, failures, resources and economics remain distinct.
- Secret/auth/browser fields are recursively rejected. Regression 174/174 PASS. `FA-C007` is READY.


### FA-C006 mirror runtime hotfix + FA-107 -> FA-C007 — DONE / PASS
- Standalone Console mirror no longer assumes repo-depth `parents[3]`; runtime root resolves by marker and mirror sync now includes lib/schemas/registries/fixtures.
- `FA-107` sanitized observability is DONE: attempts, masters, QA, derivatives, packages, failures, resources and economics stay separate; secrets are rejected recursively.
- `FA-C007` Providers dashboard is DONE: policy/capacity/router truth is served through `/api/providers`; evidence is explicitly SYNTHETIC_OBSERVED_FIXTURE, guessed quotas are absent, and Grok remains optional/deferred.
- Final regression: 184/184 PASS.


### Derivative Engine unlock batch — FA-021/022/023/024/026/027/028 DONE / PASS
- Raster derivative worker, deterministic PDF/preview packaging, color/alpha/DPI/metadata policy, derivative QA, native SVG/EPS exporter, gated trace fallback and dry-run package composer are complete.
- Full Factory regression: 224/224 PASS.
- `FA-029` remains BLOCKED because `FA-001` Linux five-master inventory is still WAITING_OPERATOR/read-only evidence gated.


### FA-001 — DONE / PASS — five current Linux production masters inventoried read-only
- Five newest final production manifests were cross-checked against actual files: exact path, PNG magic/MIME, 6144x4096 dimensions, bytes and SHA-256 all match 5/5.
- Job/blueprint lineage is recorded. No Linux file, service, queue or state was modified.
- `FA-029` is READY.


### FA-029 — DONE / PASS — five-master Asset Derivative Engine canary
- Five current Linux production masters were copied read-only to isolated Windows canary storage; source hashes match FA-001 inventory 5/5.
- 20 JPEG/WebP/TIFF/PDF outputs generated; 20/20 second-pass hashes match; 20/20 derivative QA PASS; 5/5 dry-run packages PASS.
- Duplicate package bytes are suppressed (2 manifest entries -> 1 physical file). Vector gate returns fail-closed NOT_VECTORIZABLE for all five current raster masters because trace was not authorized.
- No Linux mutation, provider call, upload or publication action occurred. `FA-030` is READY.


### FA-030 — DONE / PASS — Asset Derivative Engine v0.1 acceptance
- 39/39 targeted derivative tests and 226/226 full Factory regression PASS.
- FA-029 real five-master canary seals 20/20 outputs, rerun idempotency, QA, packages, dedupe and fail-closed vector-gate evidence.
- Zero master overwrite/false success; receipt lineage 100%; non-destructive disable/rollback documented.
- `FA-106` is READY.


### FA-106 — DONE / PASS — content-addressed master ingestion staging
- Actual five-master staging: 6 attempts -> 5 unique SHA-addressed blobs; duplicate attempt reuses bytes while keeping a separate receipt.
- All staged records remain `STAGED_NOT_CANONICAL`; the proposal requires `DIE_STATE_MANAGER` as physical writer. No direct canonical state mutation occurred.
- Regression 231/231 PASS. `FA-109` and `FA-C008` are READY.


### FA-C008 — DONE / PASS — actual output gallery lineage / derivative / QA
- `/api/outputs` serves five FA-029 semantic masters and 20 derivatives with recipe/hash/dimensions, QA/compatibility, lineage and duplicate suppression.
- Output evidence remains visibly `STAGED_NOT_CANONICAL` until State Manager commit; derivative count never inflates semantic count.
- Regression 237/237 PASS.


### FA-109 — DONE / PASS — Factory Core synthetic acceptance
- Integrated synthetic runner proves routing/capacity/policy, lease, retry, crash recovery, dedupe ingestion, sanitized observability and zero false success with zero live-provider calls.
- Regression 238/238 PASS. `FA-C009` is READY.


### FA-C009 — DONE / PASS — Console to Factory Core synthetic E2E
- Queue UI now exposes an explicit synthetic E2E trigger through `/api/synthetic/e2e`.
- One request proves policy/capacity routing, retry -> success, crash RUNNING -> READY, content-addressed output ingestion, sanitized observability and zero false success.
- Live provider calls remain zero. Regression 243/243 PASS.


### FA-032 — DONE / PASS — procedural pattern native producer
- Seeded recipes generate editable SVG native tiles and deterministic tiled PNG previews; same request is byte-identical across reruns.
- Raster masquerade/unknown parameters fail closed; cancellation yields typed FA-031 receipt. Regression 249/249 PASS. `FA-033` is READY.


### FA-040 — DONE / PASS — deterministic motion producer contract
- Motion contract pins semantic ANIMATION/TIMED_FRAMES, seed, duration/FPS/frame count, dimensions, renderer version, video target and audio policy.
- Raster conversion masquerade/static motion/frame drift/invalid targets fail closed. No renderer execution is claimed in FA-040. Regression 258/258 PASS. `FA-041` is READY.


### FA-033 — DONE / PASS — pattern seam, tile and editability QA (2026-09-04)

- Base origin/main: `010478eda06c29bdbaae5349ee8b9418db694236`.
- Direct Codex -> SSH -> Linux checkout `/home/kopiko/die-worktrees/fa033-pattern-qa-20260904`, branch `codex/fa-033-pattern-qa-20260904`.
- Read-only QA validates actual SVG/PNG lineage, editable diamond paths, exact tile bounds, continuous seams, independent geometry rendering and every preview repeat.
- Both canonical FA-032 fixtures pass. Broken seams, raster/font/script masquerades, malformed paths and resealed preview pixel drift fail closed; master/preview bytes and timestamps remain unchanged.
- Compatibility is scoped to FA032_PATTERN_TILE; marketplace compatibility stays UNKNOWN and no semantic identity is minted.
- Linux acceptance: 32 targeted tests; 290 Factory tests; 6 one-canon tests; validator 11/11; high-confidence secret hits 0; diff-check PASS.
- Receipt: `company/factory-asset/receipts/FA-033-pattern-qa.receipt.json`; exact commands: `FA-033-linux-validation.json`.
- Graph delta is FA-033 READY -> DONE only. No dependent node unlocked or advanced.
- Any other graph node started: No.
- Next existing READY eligible task: FA-041, information only; STOP.

### Factory Orchestration v2 task-graph plan — CANON PLANNED
- Added FA-129..FA-140 under `FACTORY_ORCHESTRATION`: expression planning, motion capability, provider-original intake, marketplace derivative planning, producer dispatch, cognition routing, conditional upscale, IP/brand signal gate, metadata/package readiness, mandatory postproduction, Hermes v2 wiring and synthetic acceptance.
- Two-router invariant: semantic asset-expression routing happens before Blueprint/producer; packaging derivative routing happens after master. Motion/pattern are semantic products, not post-hoc raster conversions.
- FA-120 scale harness and FA-200 governed canary now depend on FA-140 so scale/acceptance cannot bypass orchestration v2.
- FA-034 was reconciled to READY because Codex already completed FA-033.


### FA-041 — DONE / PASS — real Remotion motion producer fixture
- Remotion 4.0.520 + managed Chrome renders the exact FA-040 composition to MP4 H.264 yuv420p: 1080x1080, 30 FPS, 180 frames, exactly 6.000s, no audio stream; frame-90 PNG preview is emitted.
- Independent renders are binary-identical for both MP4 and preview. Native FA-031 receipt validates; `conversion_from_raster=false`.
- Temp cleanup passes after success and injected failure. Scope is local acceptance only / zero spend; production automation licensing is not asserted.
- `FA-042` is READY for codec/container/frame-integrity and compatibility QA.


### FA-042 — DONE / PASS — motion codec/container/frame and visual-integrity QA
- Real FA-041 MP4: H.264/yuv420p, 1080x1080, 30 FPS, 180 frames, exactly 6.000s, no audio; five sampled frames decode and prove non-blank/non-frozen change.
- Mislabeled, truncated, technically-valid blank and technically-valid frozen fixtures all fail closed with typed reasons.
- Adobe Stock pinned MP4/H.264 profile = COMPATIBLE; Dreamstime/Vecteezy/MotionElements remain UNKNOWN where exact current profile evidence is absent.
- `FA-043` is READY for Motion Engine v0.1 acceptance.


### FA-043 — DONE / PASS — Motion Engine v0.1 acceptance
- FA-040 contract + FA-041 real renderer + FA-042 adversarial QA are sealed with explicit resource bounds, typed cancellation, retry and cleanup hardening.
- Retry first attempt leaves zero partial state; second attempt reproduces accepted master/preview hashes and re-passes motion QA.
- Marketplace compatibility remains evidence-bounded; no provider/upload/publication authority.


### FA-034 / FA-129 / FA-131 — DONE / PASS — Codex Linux lane (2026-09-04)
- Explicit Founder-directed batch in isolated Linux checkout `/home/kopiko/die-worktrees/fa034-129-131-20260904`; integrated Architect FA-043 from `origin/main` before final verification.
- FA-034: both native SVG pattern fixtures regenerate byte-identically, pass seam/editability/preview QA and produce exact SVG/PNG internal packages retaining one semantic asset. EPS remains uncertified because its existing exporter loses fill colors.
- FA-129: schema, evidence-scoped validator and same-seed zero/one/multiple fixtures separate semantic expansion from delivery; forced expansion and duplicate semantic IDs fail closed.
- FA-131: actual-byte JPEG/PNG/WebP/TIFF intake records MIME/magic/dimensions/alpha/size/hash, immutable snapshots and normalized staged evidence; corrupt/mislabeled/conflicting artifacts fail closed.
- Linux targeted: FA-034 56 passed in 1.82s; FA-129 40 passed in 0.68s; FA-131 64 passed in 1.39s. Factory regression: 416 passed, 1 warning in 10.70s. One-canon: 6 passed in 1.45s; validator 11/11 PASS.
- Receipts: `FA-034-pattern-engine-v0.1-acceptance.receipt.json`, `FA-129-asset-expression-plan.receipt.json`, `FA-131-provider-original-intake.receipt.json`; commands in `FA-034-129-131-linux-validation.json` under `company/factory-asset/receipts`.
- Dependency reconciliation only: FA-130, FA-132, FA-133, FA-134, FA-135, FA-136 become READY. No downstream implementation started; FA-133 dependencies now all DONE, including Architect-owned FA-043.
- No production runtime, provider, credential, marketplace or spend action. Intake is STAGED_NOT_CANONICAL; State Manager remains the sole canonical writer.


### FA-133 — DONE / PASS — semantic producer dispatch router
- Frozen FA-129 expression + exact Blueprint hash routes PHOTO/ISOLATED_OBJECT to FA-104 provider routing, PATTERN to Procedural Pattern v0.1 and ANIMATION to Motion Engine v0.1.
- Generic ICON/OUTLINE native-vector routes remain recognized but blocked until an accepted engine exists.
- Every route is direct-from-Blueprint; post-hoc static-to-pattern/motion conversion is forbidden.


### FA-134 — DONE / PASS — Blueprint reuse and cognition router
- Compatible fixed Blueprint -> Hermes reuse with zero Division01/Executive calls.
- Division01 AUTHOR/REVISE only for missing/stale/incompatible/material semantic work; Executive CHALLENGE only for new-family/material strategy/cannibalization/escalation.
- Neither actor is a per-image gate or gains Worker/provider authority.


### FA-132 — DONE / PASS — marketplace-aware derivative delivery planner
- Provider-original JPEG can be reused for JPEG delivery; PNG/alpha formats are converted only as required by Blueprint/marketplace profile.
- Alpha-bearing input -> JPEG requires FLATTEN_WHITE; JPEG->PNG does not invent transparency. UNKNOWN marketplace profiles block package.
- Duplicate delivery variants collapse and semantic asset count remains one.


### FA-136 — DONE / PASS — automated rights/brand/watermark/text signal gate
- Exact master hash binds detector observations. Confirmed watermark/trademark/brand/safety signals BLOCK; unresolved or incomplete detector evidence requires REVIEW_REQUIRED.
- Automated PASS never grants human rights clearance; Founder QC remains mandatory.


### FA-137 — DONE / PASS — metadata and package readiness
- Actual provider-original fixture -> deterministic JPEG/WebP -> exact hash-bound metadata -> FA-028 dry-run package = PACKAGE_READY.
- Rights review, missing/tampered derivative, unknown marketplace or missing AI disclosure all fail closed.
- No rights clearance/upload/publication authority.


### FA-135 — DONE / PASS — conditional upscale/recovery adapter
- Native-sufficient master = NOOP; dimension shortfall = UPSCALE_REQUIRED; classified technical defect = RECOVERY_REQUIRED.
- Rights/safety/lineage/integrity uncertainty never recoverable. Source immutable, rerun idempotent, failure leaves no partial output.
- Production model SHA pin required; RealESRGAN Linux production not yet certified by this task.


### FA-138 — DONE / PASS — mandatory postproduction readiness state machine
- Durable atomic exact-order state machine reaches WAITING_FOUNDER_QC only after package readiness.
- Source/active master plus derivative/metadata/package hashes are lineage-bound; upscale active-master transition is explicit.
- State skipping, stale revision, event collision, unresolved rights review and invalid failure resume all fail closed.
- Final status is PARKED_HUMAN_GATE, not Founder QC completion.


### FA-130 — DONE / PASS — motion capability / temporal value gate
- Motion requires evidence-supported noun x product expression x temporal verb x buyer utility plus meaningful change over time.
- Static-equivalent/decorative motion -> STATIC_ONLY; incomplete/unmodeled -> RESEARCH; noun alone never authorizes animation.
- FA-139 becomes READY when all canonical dependencies are DONE.


### FA-139 — DONE / PASS — Hermes Factory orchestration v2 wiring
- Live runtime no longer hardcodes `final/asset.png` or jumps directly from ARTIFACT_CREATED to Founder QC.
- Legacy L0 raster production bridges to Asset Expression/Blueprint v2 and then runs FA-131/135/132/024/136/137/138.
- Listing alias is seed-noun + semantic-mode + short active-master hash; metadata/submission-fields sidecars include title/description/keywords/AI disclosure. Immutable masters are not renamed.
- Binary IPTC/XMP injection is explicitly not claimed; follow-up FA-141 added after FA-140.
- Telegram milestones are idempotent and durable postproduction states are resumable.


### FA-140 — DONE / PASS — Factory orchestration v2 synthetic acceptance
- Provider-original PNG and JPEG both traverse Factory v2 to WAITING_FOUNDER_QC with human-friendly listing filenames.
- Native Pattern SVG/PNG and Motion Engine MP4 routes accepted; EPS remains uncertified.
- Cognition reuse/escalation, conditional upscale/no-op, QA, rights signals, metadata/package readiness, Telegram, crash/retry and fail-closed controls pass with zero live provider/network calls.
- FA-141 becomes READY for binary IPTC/XMP injection/read-back; current metadata remains sidecar/submission-fields only.


### FA-140A — DONE / PASS — Linux Factory v2 live activation and production recovery
- Dedicated pinned Factory Python and stable Hermes cron shim are live.
- PRODSEED000025 recovered from immutable drift, frozen cognition transport and Runtime MCP outage; Executive revision converged NO_VETO.
- Live headphones artifact -> RealESRGAN 6144x4096 -> JPEG/WebP derivative QA -> metadata succeeded. Rights detectors unavailable correctly park at WAITING_FOUNDER_RIGHTS_REVIEW.
- Next direct production tick started PRODSEED000035 tree, proving human rights-review parking no longer blocks cadence.


### FA-141 — DONE / PASS — binary IPTC/XMP metadata + Founder notification surface
- JPEG marketplace derivative copies receive XMP APP1 + IPTC-IIM APP13 title/description/keywords/AI disclosure; immutable masters stay unchanged.
- Post-injection SHA is re-pinned, read-back must exactly match, derivative QA reruns, and package evidence uses the new hash. Unsupported formats stay sidecar-only.
- Real PRODSEED000025 headphones JPEG 6144x4096 canary passed exact XMP/IPTC read-back and QA.
- Success-path Telegram is reduced to PRODUCTION_STARTED / ARTIFACT_CREATED / WAITING_FOUNDER_QC plus cron STARTED response. Backend rights/package state remains durable; failure alerts remain enabled.

- FA-141 Linux live canary also PASS under `die-hermes` using Factory venv on a copy of PRODSEED000025 JPEG: XMP/IPTC exact read-back, technical QA PASS, output SHA `211f28375a4c...`, production workspace untouched.


### FA-140B — DONE / PASS — author-stage cognition recovery
- Live PRODSEED000035 tree repaired false NEED_REVIEW-without-author state back to NEED_AUTHOR, AUTHOR R01 validated, Executive R00 returned NO_VETO, and card reached BLUEPRINT_READY.

### FA-140C — DONE / PASS — MUXIA shared-workspace export recovery
- Live tree workspace/provider repaired to `2770 die-runtime`; MUXIA exported `source-original.png` SHA `33847b68...` on the same card.
- Tree reached WAITING_FOUNDER_QC with 6144x4096 active master, human listing `tree-photo__531ef32b.jpg`, FA-141 XMP/IPTC PASS, rights review preserved fail-closed.
- Telegram success milestones are exactly PRODUCTION_STARTED / ARTIFACT_CREATED / WAITING_FOUNDER_QC; resolver reports NO_ACTIVE_CARD and production cron remains `0 */3 * * *`.

### FA-120 — DONE / PASS — synthetic throughput and backpressure harness (2026-09-05)
- Executed from fresh isolated Linux checkout `/home/kopiko/die-worktrees/fa120-throughput-20260905-1914`; publication rebase used current `origin/main` after FA-303 and FA-200 merged. `/srv/die`, production cron, MUXIA profiles, credentials, queues, databases and active artifacts were not mutated.
- 5,000 unique synthetic jobs completed as 5,391 attempts with peak active queue depth 256 and 647 admission-backpressure observations; all four fairness tenants completed exactly 1,250 jobs with zero round-robin violations.
- Retry injection produced 390 retries with max 2/job; provider-profile lease contention failed closed; 217/217 duplicate submissions reused the original idempotent job and conflicting reuse was rejected.
- Persisted queue snapshot/reload recovered an in-flight RUNNING job to READY exactly once. Synthetic disk accounting hit 63 high-watermark pauses and 63 resumptions; modeled peak 53,673,984 bytes stayed below the 53,687,091-byte high watermark without allocating modeled payload bytes.
- Provider calls performed: **zero**. FA-120 does not import provider adapters/network clients and did not touch Cluster Broker, provider-readiness registry/probes, browser profile/runtime or live provider surfaces.
- Validation: focused FA-120 `3 passed`; Factory regression `619 passed, 1 warning` (PyPDF2 deprecation only). Receipt: `company/factory-asset/receipts/FA-120-synthetic-throughput-backpressure.receipt.json`.
- Dependency reconciliation only: FA-304 is now READY because FA-302 + FA-303 + FA-120 are DONE; **no FA-304 implementation was started**. FA-121 remains BLOCKED because FA-117 is still READY, not DONE.

---

## 2026-09-05 - FA-117 two-provider bounded pool DONE/PASS

- Exactly one live Qwen generation and one live ChatGPT/MUXIA generation completed sequentially on shared Cluster A; zero operator actions after dispatch and no secret reads.
- Qwen: BROWSER_CDP fallback (SESSION_API remains primary contract, not falsely claimed live here), 1664x928 PNG, SHA `9e9db716...bf6c358`; ChatGPT: BROWSER_CDP/MUXIA, 1254x1254 PNG, SHA `fc345bf3...62127f0`.
- Provider-original strict decode PASS; 4 intake attempts -> 2 unique staged masters with duplicate reuse 2/2; canonical truth remains false pending DIE State Manager.
- Shared-profile lease contention is blocked; live intervals do not overlap; both observed SUCCESS capacity events classify AVAILABLE.
- Browser footprint exposed startup tab creep: raw restore 10 pages, `enforceTabBudget` closed 2 -> 8/8. FA-304 must fail closed for `open_pages > max_tabs` and key capacity by provider+cluster.
- FA-121 and FA-202 become READY. No submission/publication/spend authority granted.

### FA-304 — DONE / PASS — cluster-aware provider router with capacity/backpressure (2026-09-05)
- Implemented in fresh isolated Linux worktree `/home/kopiko/die-worktrees/fa304-cluster-router-20260905` from canonical `origin/main`; no `/srv/die`, production cron, production queue/DB, Cluster A profile, credentials or active artifacts were mutated.
- Router is control-plane only: it does not launch Chromium, open tabs or call providers. Browser candidates consume a fresh FA-302 `cluster-tab-lease-snapshot`, keyed to the candidate cluster, and emit `requires_tab_lease=true`; the execution layer must still acquire the broker-backed tab lease.
- Fresh FA-303 readiness and explicit observed capacity keyed by **provider + cluster** are required. `UNKNOWN`, missing, stale or mis-keyed readiness/capacity fail closed; CHECKPOINT/AUTH_REQUIRED/UNAVAILABLE affect only that provider so healthy siblings remain routable.
- Qwen `SESSION_API` is the preferred eligible route from the canonical cluster registry and does **not** consume browser-tab capacity. `BROWSER_CDP` remains a fallback/other-provider transport and is scored with cluster/provider tab load.
- Provider+cluster selection uses asset capability, readiness, explicit capacity, per-route queue pressure, recent failures, latency and browser-tab load. Synthetic two-cluster fixture chooses the lower-load cluster without provisioning or mutating a real Cluster B. FA-117 startup evidence is enforced: `open_pages > max_tabs` is an immediate browser-route rejection even when active leases are lower.
- Retry state is idempotent by job idempotency key + retry-event ID, bounded to 2 retries, caches repeated failed retry events, rejects conflicting intent reuse and fails closed on retry after dispatch commit.
- Validation after rebasing onto merged FA-117: focused FA-304 `7 passed`; full Factory regression `641 passed, 1 warning` (PyPDF2 deprecation); one-canon pytest `6 passed`; one-canon validator `11/11 PASS`, secret scan 0. Receipt: `company/factory-asset/receipts/FA-304-cluster-aware-provider-router.receipt.json`.
- Dependency reconciliation only: FA-305 becomes READY because FA-300 + FA-304 are DONE. **No FA-305 implementation/auth/bootstrap was started.** FA-306 and FA-C016 remain blocked on their other dependencies. Canonical FA-117/FA-121/FA-202 updates from merged main were preserved; FA-304 did not edit or execute those tasks.
---

## 2026-09-05 - PROD-HB001 Hermes production IDLE heartbeat hotfix

- `die-production-cycle-v1` was not stalled: 12:00/15:00/18:00 UTC runs completed `ok`, but all three durable outputs were `silent (empty output)`.
- Live resolver shows 17 parked human-gated cards and `NO_ACTIVE_CARD`; deterministic seed selector shows `NO_ELIGIBLE_SEED` with 17 used eligible seeds. Telegram diagnostic delivery currently succeeds.
- Root cause: production runtime suppressed every `IDLE` result, so seed-pool exhaustion looked like a dead scheduler.
- Hotfix makes deterministic ticks always emit JSON; idle heartbeat includes `PRODUCTION_RUNTIME_IDLE`, observed time, `provider_call_performed=false`, parked count, and `REPLENISH_APPROVED_U1_VALIDATED_SEED_POOL` for seed exhaustion. Cron cadence remains `0 */3 * * *`.
- FA-121 is NOT wired into this cron; it remains a separate governed 24-hour live-load acceptance.
- Validation: 31 focused PASS; 641 Factory PASS; 6 one-canon pytest PASS; validator 11/11 PASS; secret scan 0.

---

## 2026-09-05 - FA-202 governed routed master + derivative family DONE/PASS

- Frozen FA-200/FA-201 semantic asset `FASA-SHOPPING_BAG_FULFILLMENT_ISOLATED` routed through one bounded ChatGPT/MUXIA Cluster A generation. Deterministic prompt SHA `30890313f7cf29cabbaa327c503343c847837dcd8ef9aadd8e2904387a555992`; one live provider generation only.
- Provider original: PNG 1254x1254, 1,197,046 bytes, SHA `f3aa28b40885e9a4a684a3836704aeab26f41aa4dc6c34ebc25e8e944f0959f7`; immutable through postprocessing.
- Pinned RealESRGAN x4 -> exact 4096x4096 PNG active master SHA `5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06`. Adobe JPEG, PNG preview and WebP preview all QA PASS with semantic identity effect NONE.
- Safe rerun proved byte-for-byte idempotency: same MUXIA generation receipt, zero provider call, upscale/master/staging reused, all 3 derivatives reused. One semantic asset, 3 packaging variants.
- Truth boundary: no independent visual/commercial classifier is claimed here; exact-expression lineage is the frozen semantic route + deterministic prompt + hashes. FA-203 owns technical/registry QA. Rights remain REVIEW_REQUIRED; canonical truth false pending DIE State Manager; no upload/publication/spend.
- FA-203 READY. FA-121 remains separate and was not started.

### FA-305 — WAITING_FOUNDER / implementation PASS — governed Cluster B provisioning (2026-09-05)
- Built `cluster-provisioning.v1.json`, `cluster_profile_provisioning.mjs`, and the visible no-CDP `muxia-cluster-auth-handoff.mjs`. Canonical Cluster B target is `cluster-b` / `web-ai-cluster-b`, but the canonical profile was **not** created and Cluster B was **not** added to the active routing registry before auth/readiness verification.
- Real temporary-profile proof: profile started with exactly 0 entries; one real headless Chromium broker owned it on loopback; max-tabs 8 preserved; a second broker was rejected before browser launch and the primary owner lock remained intact; broker stop released the lock. This exposed and fixed a broker cleanup bug so an instance that never acquired the lock can no longer remove another owner's lock.
- No source profile is accepted by the provisioner. Cluster A profile/session material was not accessed, copied, inspected, exported, hashed or compared. No provider calls, provider logins or spend occurred.
- Path/ownership guards fail closed on symlink traversal and owner mismatch. Pre-auth rollback removes only transaction-created roots with no active broker lock. Once auth handoff begins, automatic rollback is forbidden because Founder-created session material may exist.
- Founder handoff contract: visible stable browser, `about:blank`, broker fully stopped, no CDP/remote-debugging or automation attachment. After Founder closes the browser, one broker must restart and FA-303 provider readiness must be verified before full FA-305 PASS.
- Validation: focused FA-305 + broker regression `8 passed`; full Factory `651 passed, 1 warning` (PyPDF2 deprecation); one-canon pytest `6 passed`; validator `11/11 PASS`, secret scan 0.
- **Boundary:** task graph state is `WAITING_FOUNDER` with semantic boundary `WAITING_FOUNDER_AUTH`. FA-306 remains BLOCKED. FA-121/FA-202 and Hermes observability surfaces were not executed or modified by this lane.
---

## 2026-09-06 - FA-203 governed canary registry + technical QA DONE/PASS

- Reverified FA-202 live bytes without provider calls. Master PNG 4096x4096 SHA `5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06` technical QA PASS; all three derivatives QA PASS.
- RealESRGAN x4 recovery evidence remains hash-pinned; Adobe JPEG is technically compatible with evidence-pinned Adobe Stock raster delivery. Package remains NOT READY because metadata + rights belong to FA-204.
- Added deterministic `DIE_STATE_MANAGER` Factory writer. Commit produced canonical registry revision 1 with 1 semantic asset / 1 physical master; identical commit replay returns IDEMPOTENT_REUSE. Conflicting semantic rebind fails closed; physical duplicate bytes are deduped.
- Capacity evidence is historical observed ChatGPT/Cluster A SUCCESS, retained as acceptance evidence and explicitly not eligible for current routing because stale. Orchestration stops at TECHNICAL_QA_PASS; FA-204 is next.
- Validation: 22 focused; 656 Factory; 6 one-canon pytest; 11/11 validator; secret scan 0.

---

## 2026-09-06 - FA-204 WAITING_FOUNDER_RIGHTS_REVIEW
- Metadata/keywords/GENERATIVE_AI disclosure are hash-bound to the canonical master and three derivatives. XMP+IPTC listing JPEG readback PASS without mutating the FA-202 canonical JPEG.
- Rights are fail-closed: text/logo/watermark/safety detector runtimes are unavailable, so all four detector states remain INCOMPLETE and package remains PACKAGE_BLOCKED(RIGHTS_REVIEW_REQUIRED). No empty PASS evidence was fabricated.
- Orchestration stops at METADATA_READY with rights REVIEW_REQUIRED; State Manager registry revision 2 records the enrichment idempotently. FA-205 remains BLOCKED.
- Validation: 41 focused; 661 Factory; 6 one-canon pytest; 11/11 validator; secret scan 0.

### FA-121 — READY / implementation PASS / live window not started (2026-09-06)
- Dedicated stability lane implemented separately from `die-production-cycle-v1`: `fa121-stability-canary.v1.json`, durable runner, broker-leased provider worker, and dedicated systemd broker/tick/timer units. Production seed selection, FA-202 artifact family and FA-203/204/305/306 surfaces were not used or modified.
- Pre-dispatch budget is frozen in canon before any live call: exactly 24h, tick every 5m, one generation slot every 2h, max 12 provider generations total / 6 per provider, queue limit 1, no catch-up burst, max 2 **pre-dispatch** retries and zero retry after dispatch commit.
- Live route truth is explicit: ChatGPT `BROWSER_CDP`; Qwen canonical primary remains `SESSION_API` but FA-121 live executor is `BROWSER_CDP` fallback while SESSION_API capacity is UNKNOWN. Packaging derivatives never count as provider generations.
- One attempt must route through FA-304 then acquire an FA-302 cluster tab lease before dispatch. Provider readiness is probed via FA-303 without reading cookies/storage. CHECKPOINT/AUTH_REQUIRED/UNAVAILABLE fail only that provider; the healthy sibling remains routable. RATE_LIMITED/timeouts enter bounded local cooldown and never trigger post-dispatch retry.
- Attempt journals persist dispatch-commit state. A restart before commit counts no generation; a restart after commit counts exactly once as observed/unknown and forbids re-dispatch of that logical slot. Duplicate committed generation fails closed.
- Profile integrity is metadata-only (`directory/type/symlink/uid/gid/mode/inode/device`); profile contents and secret values are never read, copied, exported, hashed or compared.
- Validation: focused FA-121 `6 passed`; full Factory `667 passed, 1 warning` (PyPDF2 deprecation); one-canon pytest `6 passed`; validator `11/11 PASS`, secret scan 0; MUXIA TypeScript build PASS; Node/Bash syntax PASS. Provider calls so far: **0**.
- Next legitimate action is publication of this setup, deploy from merged canon to `/opt/factory-asset/fa121-runtime`, initialize `/var/lib/factory-asset/fa121-stability`, start the dedicated broker/timer, then publish exact `RUNNING` start/end/scheduler identity. No FA-121 DONE/PASS claim exists yet.
### FA-121 — IN_PROGRESS — observed 24h provider stability canary running (2026-09-06)
- Runtime-exit defect reproduced before dispatch: an `init` oneshot wrote durable state but failed to exit within 5s while the broker remained READY. PR #248 / merge `e9882298c88a31ecc366e3fab1bb3dba9c694590` adds explicit disconnect of only the `connectOverCDP` client transport; it does not close the broker-owned Chromium.
- Live-safe post-deploy regression executed `init`, `status`, `reconcile`, and `tick-before-start`; every oneshot exited, broker owner PID stayed `640348`, pages stayed <=8, zero leases leaked, and provider calls remained 0. Focused hotfix 7 PASS; Factory 668 PASS + one-canon 6 PASS; validator 11/11 / secret scan 0.
- Configured pre-hotfix window `2026-09-06T05:53:37.354Z -> 2026-09-07T05:53:37.354Z` is **not acceptance evidence**: timer disabled/inactive, heartbeat_count 0, provider generations 0. State and observation-gap marker are archived under `/var/lib/factory-asset/fa121-stability/`.
- Fresh observed unattended window: **2026-09-06T06:55:01.139Z -> 2026-09-07T06:55:01.139Z**. Dedicated systemd identities: `die-fa121-cluster-broker.service`, `die-fa121-stability-tick.service`, `die-fa121-stability.timer`; control loopback `127.0.0.1:39121`. Timer is enabled/active.
- First timer-fired slot completed normally, not as catch-up: Qwen `cluster-a` actual transport `BROWSER_CDP` / FALLBACK; SESSION_API remains primary contract but live candidate was rejected `CAPACITY_UNKNOWN`. Qwen readiness HEALTHY; ChatGPT sibling DEGRADED; lease acquired/released; 0 pre-dispatch retries; generation budget now 1/12. Provider-original PNG 1,324,473 bytes SHA `d4a845815aa3d01d202ad80efba7ed9af50e859a9f9b6195c3cbaa891462eced`.
- Current safety: broker READY single owner PID 640348, max_tabs=8, active leases 0, profile integrity metadata check PASS, credential/cookie/token reads false, spend/submission/publication false. **Do not mark DONE before 2026-09-07T06:55:01.139Z and durable 24h evidence evaluation.**

---

## 2026-09-06 - FA-204 visual-rights resolution DONE/PASS

- Previous `WAITING_FOUNDER_RIGHTS_REVIEW` remains preserved as registry revision 2. Added CPU-only rights runtime: Tesseract 5.3.4 + OpenAI CLIP RN50 (`afeb0e10...04b6762`), with deterministic thresholds and synthetic watermark/text-logo/graphic-logo/unsafe controls.
- Exact master `5630d1fd...70a06`: OCR consensus empty; logo score 0.104515 CLEAR; watermark score 0.118678 CLEAR; unsafe score 0.000200 CLEAR; source-IP risk score 0.002604 CLEAR. All text/logo/watermark/safety detector states COMPLETE.
- Self-test PASS proves the runtime is not an always-clear detector: watermark/text-logo/graphic-logo/unsafe controls are detected; synthetic branded trade-dress source-IP risk is 0.935102 STRONG_RISK and synthetic fictional-character source-IP risk is 0.999960 STRONG_RISK.
- Rights signal now PASS; automated source-rights preflight CLEAR while explicitly claiming neither legal clearance nor human rights clearance. Synthetic trademark hard-veto remains BLOCK.
- Package is `PACKAGE_READY` with package-plan SHA `e5912d1892f5faeedf0a931076ac8d34f7854e6ba12635f0c5840554a69a326b`. Orchestration revision 8 is PACKAGE_READY; State Manager revision 3 records explicit review->PASS rights resolution and idempotent replay.
- Final validation after FA-121 runtime-status reconciliation: 46 focused PASS; 673 Factory PASS / 1 PyPDF2 warning; one-canon pytest 6 PASS; validator 11/11 PASS; secret scan 0.
- FA-205 READY for Founder exact-hash QC. Automated rights PASS is not Founder approval and grants no submission/publication authority.

---

## 2026-09-06 - FA-205 Founder exact-hash QC APPROVED
- Founder manually reviewed the governed canary master and delivery/preview artifacts, including PNG, JPEG and WebP outputs, and explicitly returned `APPROVE`.
- Exact package hashes are pinned in `company/factory-asset/receipts/FA-205-founder-qc.receipt.json`; package state at review was `PACKAGE_READY`.
- This records Founder QC only. Submission, publication, marketplace upload and spend remain unauthorized.
- FA-205 DONE; FA-206 READY.

---

## 2026-09-06 - FA-206 Factory Asset Level Up v1 acceptance DONE/PASS
- End-to-end governed canary acceptance passes FA-200 selection -> FA-201 Blueprint -> FA-202 provider/master/derivatives -> FA-203 registry/QA -> FA-204 metadata/rights/PACKAGE_READY -> FA-205 Founder exact-hash APPROVE.
- Live bytes were re-hashed during acceptance: provider original, 4096x4096 master, Adobe JPEG, PNG preview, WebP preview and metadata-injected listing all remain exact. Metadata identity is verified through canonical `metadata_sha256`, not JSON formatting bytes.
- Rollback evidence PASS non-destructively: registry history preserves revision 1 commit, revision 2 REVIEW_REQUIRED/PACKAGE_BLOCKED and revision 3 PASS/PACKAGE_READY; revision-3 `prior_enrichment_sha256` points to revision-2 enrichment; provider original, staged master blob and canonical master remain retained and hash-stable. There is no external publication side effect to undo.
- Publication/submission/upload/spend remain outside scope and unauthorized. FA-121 24h soak is independent and remains IN_PROGRESS.

---

## 2026-09-06 - FA-305 Founder auth closed; Cluster B activation prepared
- Founder authenticated ChatGPT, Qwen, Grok, Gemini and Manus in the fresh canonical `web-ai-cluster-b` profile; Duck.ai requires no login. Visible no-CDP auth browser closed normally and provisioning state reached `AUTH_HANDOFF_CLOSED`.
- Ephemeral headless Cluster B broker proved READY single-owner on loopback, max_tabs=8 and second-owner rejection. Qwen/Gemini/Manus/Duck.ai are HEALTHY; ChatGPT is DEGRADED (`COMPOSER_NOT_READY`) without auth/checkpoint UI and remains non-schedulable on Cluster B until recovery.
- Canonical Cluster B registry/systemd activation prepared; FA-305 remains IN_PROGRESS until deployed live service is proven.
- Founder-approved future vector track FA-V001..FA-V007 is recorded only as future work; FA-V001 is DEFERRED and no Claude live action/login is authorized in this lane.
- Founder QC Delivery Contract v1 requires every `WAITING_FOUNDER_QC` alias under `qc/` to be `0640`, `die-runtime` group-readable and not world-readable. Legacy live aliases were reconciled 7/7 without changing bytes.

---

## 2026-09-06 - FA-305 DONE/PASS — canonical Cluster B active
- Founder-authenticated `web-ai-cluster-b` completed `AUTH_HANDOFF_CLOSED` with no CDP/provider automation and no Cluster A profile copy/import.
- PR #257 activated canonical Cluster B registry and headless service. `die-muxia-cluster-b.service` is enabled/active and broker is READY on loopback `127.0.0.1:39122`, max_tabs=8. Canonical second-owner attempt was rejected; controlled service restart changed browser owner PID 693865 -> 694238 and returned READY with zero active leases.
- Schedulable Cluster B provider subset: Qwen, Gemini, Manus, Duck.ai = HEALTHY. ChatGPT remains `DEGRADED_NOT_SCHEDULABLE` (`COMPOSER_NOT_READY`) with no auth/checkpoint UI; Grok remains deferred optional.
- FA-121 timer/broker remained active. No provider generation, secret-value read, spend, submission or publication occurred.
- FA-305 DONE/PASS; FA-306 READY.

---

## 2026-09-06 - FA-306 DONE/PASS — cross-cluster scheduler
- Added pure control-plane `multi_cluster_scheduler.mjs` over FA-304 routing and FA-302 per-cluster tab leases.
- Acceptance proves exclusive cross-cluster job queue leases, A/B/A/B fairness for equivalent healthy routes, provider@cluster and whole-cluster circuit isolation/cooldown recovery, max-2 pre-dispatch retries, idempotent retry events, explicit TTL reclaim, post-dispatch retry prohibition and exactly-one generation commit per `job_id`.
- Read-only live topology snapshot observed Cluster A (`39121`) and Cluster B (`39122`) both READY, max_tabs=8 and zero active leases; no live lease was acquired and FA-121 was not mutated.
- No provider generation, browser-owner action, secret read, spend, submission or publication occurred. FA-306 DONE/PASS. FA-307 remains BLOCKED only because FA-121 24h stability dependency is still IN_PROGRESS and FA-307 separately requires Founder live-provider authority.

---

## 2026-09-07 - FA-121 DONE/PASS — real 24h provider stability
- Fresh unattended observation window `2026-09-06T06:55:01.139Z -> 2026-09-07T06:55:01.139Z` completed and final evaluator returned PASS 8/8.
- 282 heartbeats covered 86,653,737 ms with maximum gap 340,011 ms (<900s acceptance cap). Profile metadata identity remained intact; zero secret leakage, duplicate committed generations or failure events.
- Six bounded Qwen generations succeeded over actual BROWSER_CDP fallback and retained six distinct original PNG hashes. Qwen then reached its per-provider cap of 6; with ChatGPT still DEGRADED/COMPOSER_NOT_READY, slots 6-11 correctly became `SKIPPED_NO_ELIGIBLE_ROUTE` with zero dispatch commits.
- Dedicated FA-121 timer and broker auto-stopped after `CLOSE_RUNTIME`. FA-121 DONE/PASS; FA-122 and FA-307 dependencies unlocked.

---

## 2026-09-07 - FA-307 bounded two-cluster live acceptance authorized / IN_PROGRESS
- Founder explicitly authorized execution after FA-121 and FA-306 reached DONE/PASS.
- Scope is exactly two concurrent heterogeneous broker-owned BROWSER_CDP generations: Qwen on Cluster A and Gemini on Cluster B. No pre-dispatch retries, spend, submission, publication or secret-value reads.
- Acceptance requires overlapping in-flight dispatches, two distinct original-byte hashes, unchanged profile metadata identity, max 8 tabs / 1 live lease per cluster, bounded combined Chromium process-tree RSS, zero lease leak, second-owner rejection, and controlled Cluster B restart recovery with no duplicate generation.

---

## 2026-09-07 - Scale-foundation discovery inserted before FA-308
- Live audit measured persistent browser profiles at 341 MiB (`chatgpt-linux-a`) and 349 MiB (`web-ai-cluster-b`), with Chromium shared once at 656 MiB. Current 100-profile footprint scenario is ~34.38 GiB including shared Chromium+MUXIA node modules, but this is not a provisioning target; 1 GiB/profile and 2 GiB/profile envelopes are retained as planning scenarios.
- FA-307 attempt #1 measured 4,739.25 MiB combined Chromium process-tree RSS for two concurrent clusters while staying within one lease/cluster and A=4/B=2 open pages. Therefore persistent profile count and active Chromium-owner concurrency are now separate capacity dimensions.
- Guest Linux remained resource-healthy while public management reachability intermittently black-holed; guest is private `192.168.25.13` with sshd on `:22`, so public `157.20.32.166:25013` is treated as an upstream NAT/filtering boundary to be hardened/observed before scale.
- Canon preserves `linux-mcp` Cloudflare ingress for Executive/Division01 MCP only; CDP/browser/wake/cluster broker routes remain forbidden. Public `*.aethers.biz.id` DNS was observed NXDOMAIN during this audit and is included in management-plane remediation scope.
- Added FA-310..FA-315 scale-foundation chain and made FA-315 an explicit prerequisite for FA-308. These tasks remain blocked behind FA-307 so the active frontier is not diverted from the two-cluster acceptance.

---

## 2026-09-07 - FA-307 attempt #1 preserved; fresh attempt #2 Qwen A + Manus B
- Attempt #1 Qwen@Cluster A + Gemini@Cluster B had two overlapping committed dispatches and passed all resource/profile/lease/recovery assertions, but Gemini timed out during original-byte acquisition after dispatch; overall acceptance remained FAIL. Qwen original SHA256 `95482edef77a7d62f689916a76a45955dc561f4f92fe58ab54e8d6a5e2b924ce`.
- No Gemini post-dispatch retry was performed. The full attempt #1 result is preserved at `company/factory-asset/fixtures/multi-cluster/FA-307-attempt-1-qwen-gemini-result.json`.
- Founder authorized completion of FA-307. Attempt #2 is a fresh bounded acceptance with new job identities: Qwen@Cluster A plus Manus@Cluster B, exactly two provider calls, zero retries, same profile/RAM/tab/lease/recovery gates.

---

## 2026-09-07 - FA-307 attempt #2 terminal; attempt #3 staged
- Attempt #2 Qwen@A + Manus@B is terminal FAIL without retry. Manus never dispatched because generic readiness reported `DEGRADED/COMPOSER_NOT_READY` before the proven Manus editor wait; Qwen independently committed once and later timed out. Recovery/profile/resource/lease safety remained bounded.
- Sanitized attempt #2 evidence is canonical at `company/factory-asset/fixtures/multi-cluster/FA-307-attempt-2-qwen-manus-result.json`.
- Attempt #3 uses new Qwen@A + Manus@B job identities. Manus pre-dispatch gating now fails immediately only on AUTH_REQUIRED/CHECKPOINT/UNAVAILABLE; otherwise it waits up to 20 seconds for the proven `.tiptap.ProseMirror` editor before any dispatch.

---

## 2026-09-07 - FA-307 attempt #3 terminal; attempt #4 Duck A + Manus B staged
- Attempt #3 is terminal FAIL without retry: Manus@Cluster B SUCCEEDED and persisted a 2,772,228-byte PNG SHA256 `0e3195e675c789835126b675a0e75d2142f689482ed28f81696422c1483465de`; Qwen@Cluster A timed out. Resource/profile/lease/recovery gates remained bounded.
- Read-only live readiness preselection observed Duck.ai@Cluster A HEALTHY/COMPOSER_READY, ChatGPT DEGRADED/COMPOSER_NOT_READY. Duck.ai is selected for fresh attempt #4 using FA-118-style Create Image + response/DOM original-byte extraction adapted to the broker lease.
- Attempt #4 uses fresh Duck.ai@A + Manus@B job IDs, exactly two provider calls and zero retries.

---

## 2026-09-07 - FA-307 attempt #4 terminal; attempt #5 Gemini A + Manus B staged
- Attempt #4 terminal FAIL: Duck.ai@A hit `E_HUMAN_CHALLENGE_REQUIRED` immediately after dispatch and was not bypassed; Manus@B SUCCEEDED with original SHA256 `6b6f763c4a6dd144055fd16be1849ffa34b13b2d7e8ee847d08e0b24d008e052`. Resource/profile/lease/recovery safety remained bounded.
- Broker-owned navigation preflight observed ChatGPT@A DEGRADED/COMPOSER_NOT_READY and Gemini@A HEALTHY/COMPOSER_READY with zero provider call and zero credential/token read.
- Fresh attempt #5 therefore uses new Gemini@A + Manus@B jobs, exactly two provider calls, zero retries. Gemini uses the canonical FA-114 download-control original-byte path adapted to broker leases.

---

## 2026-09-07 - FA-307 attempt #5 terminal; attempt #6 Gemini DOM-byte hardening staged
- Attempt #5 had two overlapping committed dispatches. Manus@B SUCCEEDED; Gemini@A reached its generated download control but Playwright `download.saveAs()` failed because the ephemeral download artifact vanished (`ENOENT`). This is classified as extractor failure, not a provider-generation failure.
- The released Gemini page no longer existed, so no false reconciliation was claimed and no retry was performed.
- Fresh attempt #6 uses new Gemini@A + Manus@B job identities. Gemini snapshots image sources pre-dispatch and, only after a new download control proves generation, first fetches fresh >=512px generated image bytes through the authenticated browser context; the browser download event remains fallback.

---

## 2026-09-07 - FA-307 attempt #6 terminal; attempt #7 Qwen A + Gemini B staged
- Attempt #6 terminal FAIL without retry: Gemini@A became AUTH_REQUIRED before dispatch, while Manus@B SUCCEEDED. This is a provider-session boundary, not an SSH or cluster failure.
- Cross-cluster zero-call navigation preflight then observed Qwen@A and Gemini@B both HEALTHY/COMPOSER_READY; no credential/token values were read.
- Fresh attempt #7 uses Qwen@A + Gemini@B. Qwen reuses the proven broker-owned FA-121 worker; Gemini runs on Cluster B/web-ai-cluster-b with the hardened post-download-control fresh DOM/browser-context original-byte path.

---

## 2026-09-07 - FA-307 attempt #7 terminal; attempt #8 Gemini download stream staged
- Attempt #7 terminal FAIL without retry: Qwen@A SUCCEEDED (1,374,952-byte PNG, SHA256 `017ef1229139c1a342cc6c0b797693fcbbe56235cf3d1221cc95900e5027c96f`) and parallel overlap passed; Gemini@B generated a download but `saveAs()` again lost the ephemeral Playwright temp artifact.
- Fresh attempt #8 keeps Qwen@A + Gemini@B. Gemini now consumes `Download.createReadStream()` directly into memory first, then tries `Download.path()`, `saveAs()`, and authenticated href fallback.

---

## 2026-09-07 - FA-307 attempt #8 terminal; attempt #9 Gemini network-byte capture staged
- Attempt #8 terminal FAIL without retry: Qwen@A SUCCEEDED again; Gemini@B generated but none of `createReadStream()`, path, or saveAs yielded stable Playwright download bytes before the ephemeral artifact disappeared.
- Fresh attempt #9 captures qualifying Gemini post-dispatch image response bodies (>=100KB, >=512px where dimensions are parsable). A response is eligible only after dispatch and is consumed only after a new download control proves that the current job generated an image. DOM/browser-context and download paths remain fallbacks.


---

## 2026-09-07 - FA-C010 DONE/PASS — bounded real-provider Factory Console canary
- Founder-authorized Console job `FCJOB-FA-C010-20260907-002` executed from isolated SSOT checkout `a1bae6761d2693a82b984b69f812fe00093bb61a` and routed through `FactoryJobQueue -> MultiClusterScheduler -> ClusterAwareProviderRouter -> BrokerTabLease -> GovernedProviderWorker -> ProviderOriginalIntake`.
- Exact live route: Qwen on canonical `cluster-b` / profile `web-ai-cluster-b`, actual transport `BROWSER_CDP` fallback; Qwen `SESSION_API` remains the primary contract and was not falsely claimed as the live executor. Readiness was `HEALTHY/COMPOSER_READY` before dispatch. Console never owned provider/browser GUI state.
- Exactly one generation commit was recorded: `8ab4f12f062b728cdfdc1dea2553db9a73666589fa5a565b58c263af9262ce6b`. Original bytes were extracted through the authenticated browser context (`provider_original_cdn_url_browser_context`) and staged as an immutable exact-copy PNG master: 1664x928, 1,417,392 bytes, SHA256 `adb63d2820b86c730d4a9dd41eb3cd29739c22c3a4c7fa3f1ff4f57b5b612d2f`.
- Console terminal state is `SUCCEEDED`; durable final result, provider-executor result and lineage are canonical fixtures. Preflight lease, generation lease and cross-cluster queue completion were all released. Cluster B broker owner PID stayed `736537`, active leases returned to 0, and Qwen provider state remained HEALTHY.
- Replay was explicitly `idempotent_replay=true` with `provider_call_performed=false`; no duplicate committed generation occurred. Earlier `FCJOB-FA-C010-20260907-001` is preserved as a pre-dispatch-only aborted control-plane attempt with zero provider call and zero dispatch commit and is not acceptance evidence.
- Truth boundaries: Cluster B auth was not touched; FA-121 state/broker was not touched; production runtime/lock/workspaces were not touched; credential/cookie/token values were not read; no account action, CAPTCHA/checkpoint bypass, spend, marketplace submission or publication occurred.
- Runtime deployment truth was preserved: live Cluster B broker ran from `/srv/die` SHA `5fc0646a1cb395d2be7dfaa7903c0bf31ef8ddd4`, a verified ancestor of Git SSOT `a1bae6761d2693a82b984b69f812fe00093bb61a`; no runtime-sensitive cluster/browser source changed between those revisions.
- Validation: focused Console+Factory Core 7/7 PASS; Linux Factory regression 721/721 PASS with only `test_fa121_oneshot_exit_live_safe.py` excluded by Founder scope; one-canon pytest 6/6 PASS; validator 11/11 PASS; high-confidence secret hits 0; Node syntax/Python compile PASS.
- `FA-C010 = DONE/PASS`. Dependency reconciliation only: `FA-C011 = READY`; no FA-C011 implementation or live batch execution was started.


---

## 2026-09-08 - FA-C011 DONE/PASS — Factory Console bounded batch and concurrency acceptance
- Deterministic Console batch `FCBATCH-FA-C011-20260908-001` executed from isolated Linux checkout at canonical base `912d585288614c0994741b7419163fa780f1ce76`; execution authority was `SIMULATED_ONLY`, with zero provider/browser calls.
- Twelve semantic jobs completed through five bounded waves with exactly three worker slots; peak concurrent RUNNING=3 and four backpressure events proved the worker cap while the queue continued progressing. Synthetic Factory Core routing selected Qwen for 6 jobs and ChatGPT for 6 jobs.
- Control/failure probes all passed: one RUNNING job paused and released ownership, resumed to READY and later SUCCEEDED; one RATE_LIMITED job entered RETRY_WAIT, retried once and SUCCEEDED; one non-retryable PROVIDER_ERROR ended FAILED while seven later jobs still succeeded. Final batch truth is 11 SUCCEEDED + 1 FAILED, not false all-success.
- Ownership/idempotency remained bounded: one competing RUNNING owner was rejected as DUPLICATE_OWNERSHIP, three duplicate submissions reused their existing jobs, and one conflicting idempotency-key reuse was rejected. The batch produced 14 attempts but exactly 12 unique semantic assets; retries, pause/resume and duplicate submissions did not inflate semantic count or synthesize a replacement for the failed asset.
- Durable Linux evidence is canonicalized under `company/factory-asset/fixtures/console-batch/`; final-result SHA256 `f7b80a74cb1ee7710b48626f4004185a4db36a622f001a1933999cdcd8e8746e`, terminal Console-state SHA256 `de2d04bc1112d20a61e08cdcc70ef6afcdffac05987a5a5293d58aa818d490f7`, timeline SHA256 `777296733c5f48a37a05ec5d93fac466ddcb04753e41842562c56a22482333ee`.
- Console exposes `POST /api/synthetic/batch-acceptance` for this governed acceptance surface. No credentials/cookies/tokens were read; spend/account/marketplace/production actions were zero.
- Validation: focused C011 + queue/C009 regressions 20/20 PASS; Factory regression 728/728 PASS with only the out-of-scope FA-121 live-broker oneshot omitted; one-canon pytest 6/6 PASS; validator 11/11 PASS; high-confidence secret hits 0; Python compile PASS.
- `FA-C011 = DONE/PASS`. Dependency reconciliation only: `FA-C012 = READY`; no FA-C012 restart/recovery implementation or execution occurred.


---

## 2026-09-08 - FA-C012 DONE/PASS — Console restart/recovery continuity
- Deterministic zero-provider acceptance ran from isolated Linux checkout at canonical base `dc7bda68282ba3763241f2806c93ae3f3d798b07`.
- Recovery snapshot contained READY, two RUNNING, PAUSED, RETRY_WAIT and SUCCEEDED truth. The uncommitted RUNNING job reconciled to READY with ownership cleared and `recovery_count=1`; the committed-dispatch RUNNING job was converted to PAUSED with `DISPATCH_RECONCILIATION_REQUIRED` and fenced from START/RESUME/RETRY, preventing duplicate dispatch after crash.
- Existing SUCCEEDED artifact hash survived exactly, PAUSED and RETRY_WAIT survived exactly, and crash recovery created no false success. Two fresh Console HTTP server instances loaded the same recovered Factory Core state and emitted identical normalized queue truth.
- Durable Linux evidence is canonicalized under `company/factory-asset/fixtures/console-recovery/`: final result SHA256 `db24598e3681772442adbee1c01f89b4881d21e3247b50aec25467f4b34b91d0`, recovery snapshot `ac4e46744a77b95f8c97c40a075690502e8da6c1ecc68dac85a00f9657ddeb8d`, reconciliation `d98c6921459267c748c89192c9f775a94a49fdf659d8ad4a1aa5be9d4859aef3`, UI state `686abafe5d024a0a2b871f2b79d88db821088838043515b4dc10d82195a60eca`.
- No provider/browser action, secret read, spend, account action, marketplace action or production runtime mutation occurred.
- Validation: focused recovery/queue/Console 31 PASS; Factory regression 736 PASS with only the out-of-scope FA-121 live-broker oneshot omitted; one-canon 6 PASS; validator 11/11 PASS; high-confidence secret hits 0; Python compile PASS.
- `FA-C012 = DONE/PASS`. `FA-C013` remains BLOCKED solely because `FA-124` is not DONE; no C013 Founder acceptance occurred.


---

## 2026-09-08 - FA-122 DONE/PASS — 20 unique masters/day bounded live-load acceptance
- Founder-authorized bounded live load used durable workspace `/home/kopiko/factory-asset-canaries/fa122-live-load-20260908-r1` with a pre-dispatch hard budget of 20 target unique masters, 24 maximum provider commits, 2 maximum concurrent generations, one live lease per cluster and 6144 MB combined browser-tree RSS cap.
- Final result: 20 terminal jobs, 20 committed generations, 20 successful provider originals, 20 unique SHA-256 masters, 20/20 technical-QA PASS, 0 provider failures, 0 exact duplicates and 0 dHash near-duplicate pairs. Cluster distribution was 10 on cluster-a and 10 on cluster-b.
- ChatGPT incident root cause was corrected from a misleading `DEGRADED/COMPOSER_NOT_READY` label to `CHECKPOINT/PROTECTION_CHALLENGE`: both existing profiles received the upstream `Just a moment...` protection interstitial with no composer, no auth UI and no writable editor. No bypass was attempted. Hotfix PR #275 (`e4b4bb73dbe932b5f7106ea06a4516fb561e7ee7`) adds protection-interstitial detection, writable-composer readiness, stronger ChatGPT selectors, verified fill + keyboard fallback, and broader send controls. While the challenge remains, routing fails closed to healthy sibling Qwen instead of stalling production.
- All 20 accepted live generations therefore used Qwen `BROWSER_CDP` fallback; `SESSION_API` remains Qwen's primary transport contract and was not falsely claimed as the live executor. Provider counts: Qwen 20, ChatGPT 0.
- Resource/capacity truth: maximum observed combined browser-tree RSS across the stepped run was 6011.93 MB < 6144 MB; max active leases remained 1 per cluster; max open pages A=3/B=1; profile metadata identity was preserved; final lease leakage was zero; no safety-bound violation occurred.
- Raw runtime evidence is hash-pinned from the VPS: plan `0a55c48c961e417d0c757c38eee5c9455db5da1750ce3bdcdf33e0aaa5ad0494`, progress-at-16 `9147f037634de60f5f98c75e0fc413b26a9a3e614aa906b4a05e3a30e615a4d5`, final live result `cd95fbd1e29510084118619a40837f8cb3ecf18104ddfc1c1914796831d2f153`, evaluator `495f008c2f8cb4dbc50b65790ef0365d15e2b7e0e9f0715815b5a0d4d82863c1`; compact canonical evidence is `company/factory-asset/fixtures/scale/FA-122-final-acceptance-evidence.json`.
- Authority boundaries: zero credential/cookie/token reads, zero spend, zero account actions, zero checkpoint/CAPTCHA bypass, zero marketplace/submission/publication action, production seed selection unused and derivatives never counted as masters.
- `FA-122 = DONE/PASS`; dependency reconciliation only: `FA-123 = READY`. No FA-123 downstream-capacity execution occurred in this acceptance run.
- Post-canonical Linux validation: focused FA-122/hotfix/canonical 22 PASS; Factory regression 747 PASS with one PyPDF2 deprecation warning and only the out-of-scope FA-121 live-broker oneshot excluded; one-canon 6 PASS; validator 11/11 PASS; secret hits 0; Node syntax/Python compile PASS.


---

## 2026-09-08 - ChatGPT Cluster B headed-broker recovery PASS
- Live diagnosis isolated the prior ChatGPT Cluster B `CHECKPOINT/PROTECTION_CHALLENGE` to broker browser mode, not lost auth. With the same `web-ai-cluster-b` profile and same VPS/network, headless Chromium stayed on `Just a moment...` for 25 seconds, while headed Chromium under Xvfb immediately reached `READY/COMPOSER_READY`. CDP remained in the automation stack, so CDP alone is not proven as the cause.
- No Founder login, challenge interaction, credential/cookie/token read, provider generation, spend, account action, submission or publication was required.
- `die-muxia-cluster-b.service` was recovered with a reversible headed-Xvfb execution path while preserving loopback CDP, single-owner broker semantics, max_tabs=8 and lease governance. Live broker owner after recovery was PID 758934.
- Zero-call live readiness after recovery: ChatGPT `HEALTHY/COMPOSER_READY`, composer visible+writable; Qwen `HEALTHY/COMPOSER_READY`; active leases returned to 0.
- Canonical current-state evidence: `company/factory-asset/fixtures/multi-cluster/FA-HOTFIX-chatgpt-cluster-b-headed-recovery.json` and receipt `company/factory-asset/receipts/FA-HOTFIX-chatgpt-cluster-b-headed-recovery.receipt.json`. Historical FA-305 headless evidence remains unchanged.
- Cluster B registry now promotes ChatGPT from `DEGRADED_NOT_SCHEDULABLE` to `ACTIVE` on the headed-Xvfb broker path. Cluster A headless broker remains unchanged because `chatgpt-linux-a` is also used by the production MUXIA headed runner and ownership convergence is a separate concern.
- Post-hotfix Linux validation: 14 focused PASS; Factory regression 747 PASS with one PyPDF2 deprecation warning and only the out-of-scope FA-121 live-broker oneshot excluded; one-canon 6 PASS; validator 11/11 PASS; secret hits 0.


---

## 2026-09-08 - Headful-default browser protocol + Cluster B owner lifecycle PASS
- Permanent protocol is now explicit in the Web-AI cluster registry: production browser mode defaults to **headful or virtual-display headful**; headless is opt-in only after provider-specific acceptance. Browser mode and automation transport are provider-specific capabilities, not global assumptions. Interactive auth may use visible browser with CDP off when the provider's human verification flow requires it; challenges are never bypassed and instead fail closed to routing/escalation.
- PR #278's private Playwright connection-close experiment was reverted by PR #279, merge `d807f3efffed588824355f1a6e8d0386ba1f3c06`. Controlled follow-up proved the pre-#278 public `browser.close()` CDP-client disconnect remains stable for 60 seconds.
- Root cause of headed Cluster B owner exits after provider work was the tab lease release path: it closed the leased page, and when that page was the last headed Chromium window the browser exited. Lease release now recycles the page to `about:blank`; if recycle fails it ensures another standby page exists before closing the failed page.
- ClusterBrokerCore now enforces `READY` owner truth: live browser PID + connected Playwright browser are required. Owner PID death/browser disconnect transitions durable state to `OWNER_FAILED`, releases leases fail-closed, launcher exits non-zero, and systemd `Restart=on-failure` restores a new owner.
- Live owner-failure injection with zero leases: PID 766537 -> `OWNER_FAILED/OWNER_BROWSER_DISCONNECTED` -> control endpoint down -> systemd NRestarts incremented -> new READY owner PID 766876. No stale READY persisted.
- Final headed durability after tab recycle: owner PID 768282 remained READY/alive/stable for 60 seconds with lease=0 and open_pages=1. Sequential zero-call acceptance on the same owner then passed: ChatGPT `HEALTHY/COMPOSER_READY` -> release `page_recycled=true`; Qwen `HEALTHY/COMPOSER_READY` -> release `page_recycled=true`; owner remained 768282, active leases 0, open_pages 1, and remained READY 20 seconds later.
- Zero provider generations/prompts, zero credential/cookie/token reads, zero challenge bypass, zero spend/account/marketplace/submission/publication actions. Linux validation: 25 focused PASS, 750 Factory PASS, 6 one-canon PASS, validator 11/11 PASS, secret hits 0. Evidence: `company/factory-asset/fixtures/multi-cluster/FA-HOTFIX-cluster-headed-owner-lifecycle.json`; receipt: `company/factory-asset/receipts/FA-HOTFIX-cluster-headed-owner-lifecycle.receipt.json`.


---

## 2026-09-08 - Hermes production cognition timeout recovery PASS
- Production card `PRODSEED000113` (seed `SEED-000113`, binder) was stuck at `BLUEPRINT_REQUIRED` after request `COG-PROD_BP_AUTHOR_PRODSEED000113_R00` entered a sent-but-empty assistant placeholder state. Division01 browser remained READY/authenticated, but the ChatGPT turn exposed a visible Stop control with no assistant text.
- Hermes cognition cron accumulated 92 consecutive `E_TRANSPORT:E_RESPONSE_TIMEOUT` failures. Deterministic production runtime therefore correctly reported `WAITING_COGNITION / PRODUCTION_RUNTIME_IDLE`, but cognition had an anti-macet defect: transport timeout did not advance durable attempt state, so every run waited on the same R00 turn.
- Hotfix: expired or bounded-timeout `SENT_WAITING` turns are stopped; response timeout is converted into durable bounded author/review retry state. Author retry is bounded by `MAX_SEMANTIC_ATTEMPTS`; review retry remains bounded by `MAX_CONTEXT_RETRIES`; exhaustion fails closed to `WAITING_FOUNDER`. No compensating seed is created.
- Live recovery: R00 timeout was durably recorded at `2026-09-08T07:54:49Z`, advancing `author_attempt=1`; fresh R01 returned a valid Division01 Blueprint with SHA-256 `333b58dc58c39a2b882911dbc4634f359dea3d2ebf6e9111006e33da72553625`; Executive review returned `NO_VETO`; cognition reached `READY`, locked `BP-PROD-BINDER-ARTIFACT-001`, and triggered the same production card resume.
- Runtime recovery proof: MUXIA `chatgpt-linux-a` produced `provider/source-original.png`, SHA-256 `6cdc13e47c88be4a4bfffd2594e51bceb67bbed7c6b0cd134b3b33bbfe579f4a`, 2,023,759 bytes, 1536x1024, and entered Factory v2 postproduction. No Founder intervention, new seed, secret read, challenge bypass, spend, account action, marketplace action, submission or publication occurred.
- Validation: 25 focused Linux Python PASS; 13 Node roundtrip PASS; Factory regression 755 PASS; one-canon 6 PASS; validator 11/11 PASS; secret hits 0. Receipt: `company/factory-asset/receipts/FA-HOTFIX-hermes-cognition-timeout-recovery.receipt.json`.


---

## 2026-09-08 - Hermes production cognition timeout recovery PASS
- Incident: `PRODSEED000113` (binder) remained at `BLUEPRINT_REQUIRED` while production runtime emitted `PRODUCTION_RUNTIME_IDLE / WAITING_COGNITION`. Hermes cognition cron accumulated 92 consecutive `E_RESPONSE_TIMEOUT` failures because Division01 request `COG-PROD_BP_AUTHOR_PRODSEED000113_R00` had been submitted once but ChatGPT stayed on an empty assistant placeholder with the Stop control visible. Auth/session remained READY; no compensating seed was created.
- Hotfix bounds response-timeout recovery. A timed-out/expired `SENT_WAITING` turn with a visible Stop control is stopped; deterministic cognition converts the transport timeout into a durable versioned author/review retry attempt instead of retrying the same request forever. Author retries remain bounded by `MAX_SEMANTIC_ATTEMPTS=3`, review retries by `MAX_CONTEXT_RETRIES=3`; exhaustion fails closed to `WAITING_FOUNDER`.
- Live recovery: R00 timeout recorded `2026-09-08T07:54:49Z` -> `author_attempt=1`; R01 author response validated at `07:56:22Z` with Blueprint SHA `333b58dc58c39a2b882911dbc4634f359dea3d2ebf6e9111006e33da72553625`; Executive review R00 validated `NO_VETO` at `07:57:10Z`; cognition reached `READY`; production resumed the same durable card and reached `WAITING_FOUNDER_QC` with listing `qc/binder-photo__c706e45a.jpg`, metadata and submission-fields artifacts.
- No credential/cookie/token reads, challenge bypass, marketplace/submission/publication action, or compensating seed. Focused Linux validation: 25 Python PASS + 13 Node PASS. Receipt: `company/factory-asset/receipts/FA-HOTFIX-hermes-cognition-timeout-recovery.receipt.json`.
- Final Linux validation for Hermes cognition timeout hotfix: 755 Factory PASS, one-canon 6 PASS, validator 11/11 PASS, Node roundtrip 13 PASS, secret hits 0.


---

## 2026-09-08 - FA-123 downstream capacity PASS
- `FA-123 = DONE/PASS`. Linux deterministic downstream-capacity model executed 100 synthetic fixtures that are explicitly **not counted as production masters** and made zero provider calls. Live FA-122 evidence remained the production input baseline: 20 unique QA-passed masters, 100% QA pass rate, zero exact duplicates, zero near-duplicate pairs and zero provider failures.
- Technical QA modeled 100/100 PASS. Distinctness evaluated all 4,950 pairwise combinations with zero exact or near-duplicate pairs on the positive set; exact-duplicate and near-duplicate negative controls were both detected/quarantined at dHash threshold 4.
- Package path modeled 100/100 `PACKAGE_READY` and 100/100 dry-run package composition with two derivatives per modeled master. Linux benchmark: QA 1.185567s, distinctness 1.220279s, package 10.978208s, total 13.384054s. Raw computed 645,544/day is **synthetic local compute headroom only**, not a provider/end-to-end/human throughput claim. Automated modeled backlog at 100/day is 0; FA-120 queue evidence also remains 5,000 unique jobs with zero terminal failures.
- Founder QC is the explicit human boundary: current canonical sampling rate remains 100%, therefore 100 masters/day requires **100 Founder QC touches/day**. No measured Founder review service-rate exists, so human capacity remains `EXTERNAL_UNPROVEN`; sampling scenarios 25/10/5 touches per 100 are informational only and **not authorized**. No QC policy, submission, publication, marketplace, account or spend authority changed.
- Canonical evidence: `company/factory-asset/fixtures/scale/FA-123-downstream-capacity-evidence.json` (Linux source SHA256 `28afd9ab6ffc25ef7d0cefc88b77f584cd1aa3b894119763374303038fa843f9`). Receipt: `company/factory-asset/receipts/FA-123-downstream-capacity.receipt.json`.
- Dependency reconciliation: `FA-124 = READY`, but remains `FOUNDER_REQUIRED_FOR_LIVE_LOAD`; FA-123 does not authorize the 100-live-master canary.
- FA-123 final Linux validation: 761 Factory PASS, focused acceptance 10 PASS, one-canon 6 PASS, validator 11/11 PASS, secret hits 0.
