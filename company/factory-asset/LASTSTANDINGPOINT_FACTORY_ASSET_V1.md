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
