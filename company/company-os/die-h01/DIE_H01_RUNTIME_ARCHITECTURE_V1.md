# DIE-H01 Factory Runtime Architecture v1

Status: FOUNDER-APPROVED CANONICAL DESIGN / NOT LIVE
Date: 2026-09-11
Scope: H01 Factory Asset runtime only. DIE is global; `die-control` is the separate global control plane.

## 1. Boundary and naming

```text
DIE GLOBAL
├── die-control   Windows VPS: one global Mission Control + Universal MCP
├── die-h01       Linux VPS: Factory Asset execution plane
├── die-h03       H03 domain runtime
└── die-hNN       future Holdings
```

The dirty current `/srv/die` checkout is LEGACY LIVE / ROLLBACK. It must not be reset/pulled in place to catch GitHub canon. New H01 code is deployed from clean origin/main release roots, accepted, then cut over atomically. `/srv/die` remains rollback until the replacement proves a complete cycle.

## 2. Global Mission Control stays outside H01

H01 is intended to become a heavy 24/7 factory. A separate Windows failure domain keeps scheduling, observability and recovery alive when H01 is saturated, browser-degraded, rebooting or offline. Cross-VPS latency is not the hot path: Mission Control sends durable Work Cards and receives bounded checkpoints; browser actions, provider waits, SVG downloads, QA, conversion and storage remain H01-local.

SSH is engineering/break-glass. Normal business flow uses an authenticated H01 Runtime Gateway over a secure tunnel. Work state survives transient network loss and reconciles without duplicate execution.

## 3. Founder operator experience

H01 remains normally operable through XFCE/xRDP/VNC-style GUI. Backend automation may use separate displays, but it may not be opaque. Founder must be able to see active UDD/profile/provider/task state and open/mirror the active browser for diagnosis without SSH spelunking.

## 4. Brave fabric: 20 UDD x 5 profiles

Target shape:

```text
20 UDD shards x 5 persistent profiles = 100 profiles
s01 -> p001..p005
s02 -> p006..p010
...
s20 -> p096..p100
```

Canonical IDs are `h01-web-s01..s20`, `h01-web-p001..p100`, and `h01-web-owner-s01..s20`.

Hard invariant: **one UDD may run exactly one profile at a time, and that profile may run exactly one committed production tab/job at a time**. No sibling profile overlap and no simultaneous ChatGPT/Qwen/Claude tabs inside one leased profile.

```text
UDD IDLE
 -> round-robin eligible sibling profile
 -> spawn one Brave/profile
 -> one provider + one committed tab + one job
 -> provider-specific wait/completion detection
 -> acquire output + durable receipt
 -> close Brave
 -> optional safe cache janitor
 -> UDD IDLE
```

Therefore 100 persistent profiles do not mean 100 live browsers. Maximum topology is 20 UDD owners; accepted concurrency is increased only from measured evidence. Founder performs provider logins; automation never copies cookies/tokens/session secrets between profiles.

## 5. Brave anti-macet and resource policy

First prove one profile stable, then clone the safe baseline. Disable nonessential consumer features by managed policy where practical, retain security boundaries, and clean only regenerable caches while the UDD is closed. Authentication/session stores remain protected. Provider completion timing is provider-specific; long-thinking providers must not be cut by a generic short timeout.

Concurrency acceptance records renderer/process count, RAM, disk growth, provider stability and recovery at 1 -> 2 -> 4 -> 8 -> 10 active UDD owners before any further scale.

## 6. Supply-first SVG MVP

Live Object Atlas currently has exactly **43,005** `candidate_seeds` with `wave3_status=eligible`. The first sellable lane does not wait for Human Atlas, demand scraping, Product Expression expansion, Set generation or a giant style matrix.

```text
media  = VECTOR
mode   = VECTOR_OBJECT
form   = SINGLE
preset = CLEAN_STOCK_VECTOR_V1
source = eligible Object Atlas noun
```

One noun becomes one semantic SVG master. Derivative files are deliverables, not new semantic assets.

## 7. Blueprint and Prompt Composer v2

Blueprint is provider-independent WHAT. Master instruction/prompt logic is HOW. Prompt Composer v2 must preserve commercially important constraints: subject anatomy and recognition anchors, viewpoint, proportions, material/color/texture, visual hierarchy, vector style system, editability, bounded complexity, stock suitability, negative/IP constraints and explicit SVG output contract.

`web-ai-adapter` is default ingress. Native MCP is optional transport, not a Vector Factory dependency.

## 8. Native SVG intake and lineage

Founder Claude Sonnet 4.6 samples under `D:\\Dee_Workspace\\Claude_SVG` prove real native SVG generation and also prove current FA-321 parsing is too narrow. Real samples use shapes and geometry beyond `svg/g/path` plus M/L/H/V/Z.

```text
provider-original.svg  immutable + provenance/hash
        -> canonicalization / safety / geometry / render QA
canonical-master.svg   governed production master
```

Provider provenance such as C2PA is preserved on the original; canonical master carries explicit lineage.

## 9. Vector Postproduction v1 is the leverage core

A local deterministic CPU pipeline owns:

```text
SVG intake/canonicalizer
 -> safety/editability/geometry QA
 -> vector derivatives directly from vector master
 -> raster derivatives directly from vector master
 -> artifact reopen/render/read-back QA
 -> metadata/rights/package routing
```

Core V1: optimized SVG, true vector PDF, validated EPS, transparent PNG, WebP and JPG preview. TIFF/SVGZ/DXF are conditional. Never create vector PDF/EPS through PNG. `exit 0` is not artifact PASS.

## 10. Family / Set / Bundle vocabulary

Standalone nouns ship first. Future family design starts now but does not block production.

Initial semantic family classes: `TAXONOMIC`, `FUNCTIONAL`, `CONTEXTUAL`, `VARIANT`, `SYSTEM`.

```text
SEMANTIC FAMILY -> DESIGN SET -> DERIVATIVE BUNDLE -> LISTING PACKAGE
```

Brand/trademark families may be discovered but carry `rights_class=BRAND_RESTRICTED` and cannot silently route to normal stock production.

## 11. Demand intelligence is later and non-blocking

Object Atlas answers WHAT valid objects exist. Human Atlas and external market signals later enrich ranking, buyer/use-case context, family discovery, metadata and long-tail opportunities. Demand Engine may reorder the remaining queue but must not block initial conversion of the 43,005 eligible nouns.

## 12. Engineering workforce via browser sessions

A separate engineering-worker plane may use multiple authenticated ChatGPT Architect browser sessions. Each worker receives one Mission Control task, one principal/lease, one isolated worktree and a machine-readable completion marker/result. A dispatcher may lease separate engineering UDD/profile workers in parallel, observe durable Mission Control checkpoints/results, close completed browsers and advance dependency-ready tasks. Browser chat text alone never marks a task DONE.

This worker plane is an execution mechanism, not a second scheduler. Mission Control remains durable task truth and graph authority.

## 13. Cutover

Legacy `/srv/die`, Chrome/MUXIA browser runtime, Hermes and OpenCode remain rollback until clean H01 deployment proves: global MC -> H01 durable dispatch, visible Brave execution, native SVG generation, postproduction/read-back QA, Founder-QC-ready package, idempotent receipts and bounded shadow coexistence. Only then may legacy critical-path services be retired.

## 14. H01-003 engineering worktree lifecycle standing

H01-003 implements the foundation guardrail in `bin/die_h01_worktree.py`, with policy in `docs/operations/DIE_H01_EPHEMERAL_WORKTREE_V1.md` and regression coverage in `bridge/tests/test_h01_worktree_lifecycle.py`.

The helper deliberately does **not** attach engineering worktrees to `/srv/die/.git`. It maintains a separate bare anchor under `/home/kopiko/.local/state/die-engineering`, fetches current `origin/main` there, materializes exactly `/home/kopiko/die-sessions/<task>`, and keeps lifecycle receipts outside the worktree. This preserves `/srv/die` as legacy live / rollback while still allowing clean canon-based engineering.

Closure is destructive only to the ephemeral worktree and therefore fails closed unless the worktree is clean and its HEAD is already visible on a fetched remote ref. Remote publication remains separately serialized by the canonical engineering lease protocol. H01-003 completion does not itself deploy or cut over any runtime service.

## 15. H01-004 legacy-live rollback freeze

H01-004 classifies and freezes the protected `/srv/die` source state before V2 cutover. The legacy checkout remains pinned at `5fc0646a1cb395d2be7dfaa7903c0bf31ef8ddd4`; capture observed 17 tracked modifications and 11 non-ignored untracked files without reset, stash, clean, pull, service restart or source overwrite.

Relative to current canon `13399dd511fb649a41a94369c730315fc8fdb012`, 15 dirty/non-ignored files are already byte-identical to canon, 12 retain live-local divergence, and one OpenCode backup exists only in the legacy tree. Twelve systemd unit files reference `/srv/die`; 11 were active at capture. In particular, the active Cluster A/B brokers read the live `web-ai-clusters.v1.json`, whose live bytes diverge from current canon, so the dirty state is rollback evidence and must not be cleaned away.

The immutable source snapshot is `/home/kopiko/die-archive/legacy-live-snapshots/H01-004-legacy-live-20260912T041238Z.tar.gz` with SHA-256 `9f92ea28cdcbbb68ee730e0574e37ec91899b913d6f1d2ac68a1df2fed2a5422`. It is mode `0444` and filesystem-immutable. Its internal manifest and point-in-time consistency checks passed. Generated `node_modules`, build outputs, Python caches and test caches are recorded by hash/size manifest but are not promoted to source authority. The durable receipt is `company/company-os/die-h01/receipts/H01-004-legacy-live-snapshot.receipt.json`.

## 16. H01-005 data retention standing

H01-005 establishes `ACTIVE`, `ROLLBACK`, `ARCHIVE`, `REGENERABLE` and `DISPOSABLE` retention classes in `DIE_H01_DATA_RETENTION_V1.md`. The policy is intentionally conservative: a path being reconstructible does not authorize deletion; `DISPOSABLE` requires exact duplicate proof plus absence of live references.

The only deletion in H01-005 removed 2,044,108,449 bytes of proven DIE-203 duplicates: reconstructed transport chunks and one uncompressed migration staging DB that is exactly recoverable from its retained gzip archive. Post-delete SQLite quick checks passed, the 475,560-object seed library remained intact, and Object Atlas still exposes 43,005 Wave-3 eligible candidates. Production state, workspaces, artifacts, logs, rollback snapshots, raw source provenance, active staging and uncertain historical staging copies were retained.

## 17. H01-012 narrow Runtime Gateway standing

H01-012 freezes `DIE_H01_RUNTIME_GATEWAY_V1.md` as the logical cross-VPS boundary. The gateway is not a scheduler or general RPC surface. Exactly three business message classes cross the boundary: `WORK_DISPATCH`, `WORK_CHECKPOINT`, and terminal `WORK_RESULT`. Mission Control remains the one global scheduler and durable task authority on `die-control`.

Dispatch is store-before-ack and replay-safe by dispatch/idempotency/digest identity; H01 journals execution and outbound events locally, and transient WAN failure may not create a second execution. Checkpoint/result events are projected by a privileged control-side bridge onto canonical `mc-mission-v1` methods, while Mission lease/review capabilities remain ephemeral control-side authority and are not persisted on H01.

Brave lifecycle, CDP, UDD/profile paths, provider sessions/waits/retries, shell/filesystem operations, downloads, SVG bytes, QA/conversion, artifact bytes and cache operations remain H01-local. Per-click WAN orchestration is forbidden. H01-012 is contract-only: no gateway daemon, port, tunnel, browser or runtime cutover was changed.

## 18. H01-101 deterministic SVG production queue standing

H01-101 exports the Founder-locked 43,005 `candidate_seeds.wave3_status=eligible` rows into a deterministic read-only queue under `/var/lib/die/h01/queues/svg-standalone-v1`. Queue identity derives from the stable Atlas candidate ID, ordering is `raw_noun_id ASC, id ASC`, and the idempotency key binds candidate identity to the fixed `VECTOR / VECTOR_OBJECT / SINGLE / CLEAN_STOCK_VECTOR_V1` production contract.

H01-101 does not rewrite or re-rank Atlas. Wave-3 eligibility remains the source rights/isolated-object feasibility authority: all 43,005 exported rows have `ip_risk=none` and accepted suitability evidence. The 338 rows whose earlier Wave-2 source tier was `review` remain dispatch-eligible because Wave-3 explicitly promoted them to `eligible`; that lineage is preserved rather than overwritten.

The accepted queue contains 43,005 unique queue IDs and 43,005 unique idempotency keys. Its SHA-256 is `0f0ec826a81d888a2be3f0b4bd11d6327f7202963d70add639f2092cdf46beeb`; the source-selection fingerprint is `dd366a552e906a1bb626a2af2d24790a4dcc371b12a3cc8db506973d0d707086`. First export returned `CREATED`; repeated exports returned `UNCHANGED`. Object Atlas was opened read-only and its DB SHA/metadata remained unchanged.

## 19. H01-300 Architect browser-worker session standing

H01-300 freezes `DIE_H01_ARCHITECT_BROWSER_WORKER_SESSION_V1.md` as the engineering browser-worker boundary. One authenticated ChatGPT Architect browser session owns exactly one Mission Control task attempt, one principal, one task-scoped owner lease capability and one dispatch identity. Project context is recovered first for continuity, but current `mission.task.get` plus current canon remain authority; chat memory and rendered prose never mark a task DONE.

Repository engineering uses exactly one H01-003 isolated worktree at `/home/kopiko/die-sessions/<task_id>`, never `/srv/die`. Remote Git mutation remains separately serialized by `income-os.repo-write + company-os.<task_id>` acquired immediately before publication and released in `finally`; the Mission owner lease does not itself grant repository-write coordination.

The browser completion marker is exactly `MC005_ARCHITECT_RESULT_<dispatch_id>` and is correlation evidence only. It is emitted as the final non-whitespace line only after `mission.task.complete` returns durable success. Blocked work, owner-lease loss, browser closure, local commits or ordinary assistant claims must not emit a success marker or be interpreted as completion. Mission lease/review capabilities remain ephemeral and are forbidden from canonical receipts/results.

H01-300 is contract-only. Browser/CDP dispatch remains H01-301, progress-aware durable completion ingestion remains H01-302, and parallel worktree/Git/lease enforcement remains H01-303. Therefore H01-301 and H01-303 become READY after this contract; deeper canary/scaling tasks remain dependency-blocked.

## 20. H01-301 Architect browser/CDP dispatcher standing

H01-301 implements the bounded dispatcher under `company/company-os/die-h01/engineering/`. It leases one dedicated logical engineering browser resource, direct-spawns a headful browser with loopback-only CDP, injects the exact H01-300 Mission bootstrap once through the visible ChatGPT composer, observes only durable Mission task evidence, and closes the browser plus profile lease in `finally`. Browser executable/UDD/profile paths remain host-local bindings; cookies, tokens and session bytes are not read or promoted to canon.

The current H01-301 attempt itself provides live control-plane evidence: Mission Control delivered this session through `architect-browser-cdp-python` with dispatch `AD-MTXX60OV-4289E7`, and durable checkpoint `272` was written after bootstrap intake. A duplicate authenticated session for the same owner lease was intentionally not launched. Separately, the new CDP driver passed a real Chrome fixture proving spawn → loopback CDP → composer injection → submit → `Browser.close`, with browser root exit code 0 and no retained fixture UDD.

H01-301 is intentionally `CANARY_ONLY_UNTIL_H01_302`: observing one owned checkpoint is sufficient only for this dispatcher acceptance canary. Production-safe progress-aware terminal detection, stall recovery and result ingestion belong to H01-302. H01-303 remains independently READY for parallel Git/worktree/lease isolation.
