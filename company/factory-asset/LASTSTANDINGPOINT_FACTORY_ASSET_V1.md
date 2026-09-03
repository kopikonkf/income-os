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

## OAUTH safety

- `D:\OAUTH` HEAD remains `c2fb61467138a24156b3d61c991882ebcdd59086`.
- Dirty count after scoped W002/W004 deploy: 67.
- Pre-existing unrelated dirty work is preserved; target-excluded digest remained identical before/after each scoped deployment.
- OAUTH server root HTTP 200; `/health` HTTP 200.
- No reset, stash, clean or credential/session export occurred.

## Next Windows frontier

`FA-W007` is the next Windows frontier. Founder/operator has already supplied the Manus provider-original artifact for validation; no additional live call is required to evaluate that existing artifact.

## Engineering lease

Any income-os publication must acquire `income-os.repo-write` plus the task-specific Factory Asset lease and release both in `finally`. Do not preempt the Linux hourly runner.
