# MUXIA — PROXIMA BASELINE V1

Status: PINNED / READ-ONLY BASELINE
Date: 2026-08-26
Atomic task: MX-010
Purpose: establish the exact live Proxima baseline before MUXIA autopsy/refactor.

## Repository baseline

- repository working tree: `D:\V2 Proxima`
- remote: `https://github.com/kopikonkf/v2provima.git`
- branch: `main`
- HEAD/origin-main: `06b9c9bea212122e76ecfadb88f307378dd9bd7d`
- HEAD subject: `Merge pull request #9 from kopikonkf/architect/chatgpt-image-ui-readiness-v2`
- package: `proxima`
- package version: `5.0.0`
- package entrypoint: `electron/main-v2.cjs`
- start script: `electron .`
- Electron dependency: `^33.4.11`

Recent canonical lineage observed in Git:

- `06b9c9b` — merge PR #9 image-ui readiness v2
- `f2b76ce` — harden ChatGPT image UI readiness
- `e932a1f` — merge PR #8 free ChatGPT image export v1
- `c2a9679` — persist free UI image generations
- `c0c07eb` — multi-provider Proxima V2 baseline

## Live runtime baseline

- REST binding observed: `127.0.0.1:3211`
- listener owning PID at pin time: `6892`
- executable: `D:\V2 Proxima\node_modules\electron\dist\electron.exe`
- process type: Electron/Chromium GUI runtime
- `/v1/models`: HTTP 200
- `/health`: HTTP 404 (not a currently proven health endpoint)

The live model registry reported `chatgpt` enabled along with additional provider/model entries including Claude, Gemini, Qwen, DeepSeek, Mimo, Grok, Nemotron, Perplexity and others. This baseline does not claim that every advertised provider is currently authenticated or production-ready.

## Proven ChatGPT image/text evidence inherited from DIE canon

The existing `LASTSTANDINGPOINT.md` records the bounded free-Web-ChatGPT image path and post-fix proof:

- PR #8 / implementation `c2a9679...`: durable free ChatGPT UI image export established;
- PR #9 / implementation `f2b76ce...`: `chatgpt:image-ui` routing/readiness repaired;
- merged main now includes those changes at `06b9c9b...`.

Pinned prior governed image proof:

- artifact: `D:\proximav2-setup\artifacts\9fe55423eaed192b4e5e1d76f8ea74135b52667a622eaf24308b6b08eaa28318.png`
- bytes: `976345`
- SHA-256: `9fe55423eaed192b4e5e1d76f8ea74135b52667a622eaf24308b6b08eaa28318`
- independent receipt: `C:\DIE\workspaces\M001-U1-001\probe\PROBE_RECEIPT_POSTFIX-20260825T084836Z.json`
- normal text canary was also reported PASS after the image-ui readiness repair.

These are inherited baseline references, not newly generated assets in MX-010.

## Worktree preservation boundary

The live Proxima repository is **dirty** at baseline. Observed local changes include modifications under Electron/browser/provider files plus untracked provider/backup/wasm artifacts.

MX-010 does not classify, clean, stage, reset, discard, merge, or normalize any of them.

Canonical rule for MX-011 and later:

`LIVE PROXIMA DIRTY STATE = PRESERVE UNTIL CLASSIFIED`

No future worker may infer that these changes are trash merely because they are uncommitted.

## Legacy deployment split observed

Two different paths exist and must not be conflated:

- `D:\V2 Proxima` — Git repository and live Electron executable origin;
- `D:\proximav2-setup` — non-Git setup/artifact/runtime-support directory containing the durable artifact store and older copied runtime files.

The autopsy must determine which files are authoritative, copied, generated, stale, or runtime-owned before any migration.

## MX-010 acceptance evidence

- exact repository + remote pinned: PASS
- exact branch/SHA pinned: PASS
- package/entrypoint/Electron dependency pinned: PASS
- live listener/process pinned: PASS
- `/v1/models` read-only probe: PASS HTTP 200
- current proven ChatGPT image/text receipt references pinned: PASS
- live dirty worktree identified and preservation rule recorded: PASS
- secrets/cookies/session credential values requested/read: NO
- Proxima/browser/service/runtime mutation: NO

## Next atomic node

`MX-011 — Codebase KEEP/EXTRACT/RETIRE autopsy`

MX-011 is allowed to inspect source and classify relevant modules. It is not authorized by this baseline to refactor, clean the dirty worktree, stop/restart Proxima, alter browser profiles, or migrate runtime state.
