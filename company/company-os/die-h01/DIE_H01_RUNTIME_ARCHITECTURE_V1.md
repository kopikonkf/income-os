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

## 21. H01-302 progress-aware Architect worker completion standing

H01-302 adds `architect_worker_completion.py` as the production-safe completion supervisor for the H01-301 dispatcher. Rendered chat text is never completion authority. The supervisor holds the browser/profile through intermediate checkpoints, tracks durable Mission progress plus metadata-only UI activity, and ingests terminal result/artifacts only from Mission Control durable state. `DONE` and `VERIFYING` require the owner final checkpoint at progress 100 with `result` and `artifacts`; the dispatch-bound `MC005_ARCHITECT_RESULT_*` marker remains correlation evidence only.

The default no-progress stall window is 5,400 seconds, with a hard 300-second minimum stall floor, 300-second Mission observer outage grace and 30-second marker reconciliation window. UI response growth or a visible generating control counts as positive activity and prevents an aggressive cut. Browser exit, lease loss/expiry, auth wall, true stall or prolonged observer outage return `RECOVERY_REQUIRED`; they never synthesize DONE and never make scheduler/provider decisions. Browser/profile cleanup remains deterministic in `finally`.

The CDP driver now emits metadata-only `OBSERVATION` JSONL (`assistant_nodes`, `assistant_chars`, generating control, composer/auth and marker correlation) without raw assistant text, cookies or session material. A real Chrome fixture proved SUBMITTED -> OBSERVATION -> Browser.close with exit code 0 and root process gone. The current H01-302 Mission attempt was independently classified from a sanitized live snapshot as `WAIT / ACTIVE_PROGRESS_AWARE`, demonstrating that an active durable checkpoint keeps the worker alive.

The live Windows Mission Control code was reconciled read-only: its Architect adapter already preserves `PROTOCOL_ACTIVE` for fresh heartbeats within 5,400 seconds after observer timeout, and `mission.task.complete` writes the progress-100 result/artifact checkpoint before releasing ownership. H01-302 does not mutate that separate control-plane repository or create a second scheduler. H01-303 remains READY; H01-304 stays blocked until H01-303 is DONE.

## 22. H01-102 Blueprint -> Master Instruction -> Prompt Composer v2 standing

H01-102 freezes a three-layer SVG production-intent pipeline. `die.h01.svg-blueprint.v2` is the provider-independent WHAT: it binds the H01-101 queue/source identity to the fixed `VECTOR / VECTOR_OBJECT / SINGLE / CLEAN_STOCK_VECTOR_V1` contract and carries commercial use, subject anatomy/components, recognition anchors, viewpoint, proportions, material/color/texture, visual hierarchy, vector style/editability, complexity, stock/IP constraints and the native-SVG output contract. Provider/model/transport/prompt knobs are invalid Blueprint concerns.

`die.h01.svg-master-instruction.v2` is a deterministic provider-neutral intermediate contract with ordered SUBJECT, COMMERCIAL, COMPOSITION, VECTOR_STYLE, COMPLEXITY, RIGHTS_AND_STOCK and SVG_OUTPUT sections plus Blueprint/Master hashes. `svg_prompt_composer_v2.py` then applies only a provider formatting profile and DIE-internal character budget. Every Master clause must survive verbatim; budget overflow fails closed instead of truncating semantics. Provider-specific phrasing therefore changes the provider-prompt hash without changing Blueprint or Master identity.

The SVG contract is bounded by the accepted H01-103 engine: at most 1,048,576 bytes, 512 geometry elements, 8,192 sampled points, 32,768 path characters and group depth 64; supported geometry is `g/path/rect/circle/ellipse/line/polyline/polygon` with M/L/H/V/C/S/Q/T/A/Z command families and relative equivalents. Script, external refs, embedded raster, foreignObject, text and unsafe style/defs/symbol/use structures remain forbidden. `web-ai-adapter` stays the default ingress and native MCP is optional. Compilation grants no provider-call, submission or publication authority.

The queue-linked `book` canary (`H01-SVGQ-CAND-0829866`) compiles deterministically across all current formatting profiles with zero semantic omissions and inside each internal budget. H01-104 is READY after H01-102 + H01-103 and owns the generalized provider-independent native-SVG request/receipt boundary.

## 23. H01-104 provider-independent native-SVG request / receipt standing

H01-104 freezes `die.h01.native-svg-request.v1` and `die.h01.native-svg-receipt.v1` as the provider-independent execution boundary between H01-102 prompt compilation and downstream SVG validation/postproduction. The request binds queue/source/semantic identity to Blueprint SHA-256, Master Instruction SHA-256 and exact provider-prompt SHA-256 while treating `provider_id` / `provider_profile` as data, not schema specialization. `WEB_AI_ADAPTER` is preferred/default; `NATIVE_MCP` is allowed but explicitly optional.

Logical idempotency excludes ingress transport. `ExactlyOnceLedger` therefore permits one dispatch commit for a provider/semantic/prompt generation identity; an alternate ingress after commit fails `E_ALREADY_DISPATCHED`. The journal is a local dispatch guard only and never selects tasks, providers, retries or routes; Mission Control remains the sole scheduler. Terminal receipts require a matching dispatch commit, replay identically, and reject conflicting terminal evidence.

A `SUCCEEDED` receipt requires `SVG_SOURCE_TEXT` from `DIRECT_PROVIDER_SVG_SOURCE`, `native_editable=true`, `conversion_from_raster=false`, `embedded_raster=false`, preserved provider-response/candidate hashes, and H01-103 validation `PASS` with canonical SVG SHA-256. Raster tracing, screenshots, SVG wrappers around raster, post-hoc vectorization, or unvalidated output cannot claim native-SVG success. Failure/timeout/block/cancel receipts preserve provider result/error metadata without inventing success.

The queue-linked book fixture remains explicitly synthetic/non-live. Its candidate passed H01-103 as editable geometry (3 geometry elements, 31 sampled points) and proves contract compatibility only; provider promotion/live canaries remain H01-107. H01-104 performs no provider call, route promotion, submission, publication, `/srv/die` mutation, Atlas mutation or second-scheduler work.

## 24. H01-303 per-worker Git/worktree/lease isolation standing

H01-303 adds `architect_worker_isolation.py` as the fail-closed parallel engineering workspace gate. Before local repository mutation, a worker must resolve exactly to `/home/kopiko/die-sessions/<task_id>`, match an `OPEN` H01-003 lifecycle receipt, keep both its Git dir and common Git dir outside protected `/srv/die`, and acquire an exclusive host-local claim for that resolved mutable worktree. A second worker cannot claim the same checkout, while different task worktrees may safely share non-live Git object/ref storage.

Dependency and merge readiness are checked against `refs/remotes/origin/main`, never the worker branch. This prevents an unmerged local task-graph edit from unlocking downstream work and keeps Mission Control plus canonical Git as graph authority. The isolation layer does not schedule work, mutate Mission state, or change Founder authority.

Remote repository mutation continues to use the existing control-plane `bin/die_engineering_lease.py` pair `income-os.repo-write + company-os.<task_id>`, acquired immediately before publication and released in `finally`. A conflicting global repo-write lease fails closed. H01-303 explicitly forbids a Linux shadow publication lease root because split coordination would permit concurrent writers. With H01-302 and H01-303 both DONE, H01-304 becomes READY but retains `FOUNDER_REQUIRED`; H01-303 does not start that canary.

## 25. H01-120 Semantic Family v1 standing

H01-120 freezes `DIE_H01_SEMANTIC_FAMILY_V1.md` plus `contracts/h01-semantic-family.v1.schema.json` as the canonical semantic grouping boundary. A Family is a grouping of at least two canonical semantic members and uses exactly one class: `TAXONOMIC`, `FUNCTIONAL`, `CONTEXTUAL`, `VARIANT`, or `SYSTEM`. Every member preserves its canonical Object Atlas subject linkage and carries `identity_effect=NONE`; family membership does not rewrite standalone noun/object identity.

The contract explicitly separates `SEMANTIC FAMILY -> DESIGN SET -> DERIVATIVE BUNDLE -> LISTING PACKAGE`. File-format/size exports such as SVG/PNG/JPEG/WebP therefore remain derivatives of one semantic asset and cannot manufacture a multi-member Family. The schema hard-codes these boundaries and the acceptance suite rejects conflation cases.

Family identity is deterministic: `FAM-V1-<CLASS>-<24 uppercase SHA-256 hex>` is derived from family version, class, semantic key and sorted canonical Object Atlas subject IDs. Source evidence is mandatory and auditable. Rights classification is one of `GENERIC_UNRESTRICTED`, `REVIEW_REQUIRED`, or `BRAND_RESTRICTED`; the Family artifact itself grants no production/submission/publication authority, and restricted systems cannot auto-qualify for production.

Legacy Division01/production-cognition `family_id` fields remain historical commercial/candidate grouping evidence and are not silently reinterpreted as Semantic Family v1. H01-121 and H01-122 become READY from H01-120 completion; H01-123 remains dependency-blocked until H01-111, H01-121, and H01-122 are DONE.

## 26. H01-122 Family / Set rights-routing gate standing

H01-122 adds `DIE_H01_FAMILY_SET_RIGHTS_GATE_V1.md`, `contracts/h01-family-set-rights-candidate.v1.schema.json`, and `lib/family_set_rights_gate.py` as the pre-production semantic rights-routing boundary for Semantic Family and future Design Set candidates. It complements the existing FA-136 post-artifact OCR/logo/watermark signal gate; passing H01-122 never bypasses downstream artifact rights/QA controls or Founder-controlled submission authority.

The gate aggregates constituent rights fail-closed across `GENERIC_UNRESTRICTED < REVIEW_REQUIRED < UNKNOWN < BRAND_RESTRICTED`. The declared candidate class must equal the strongest constituent class, every constituent must point to present evidence, and brand-restricted aggregates require explicit `RIGHTS_EVIDENCE`. A caller therefore cannot downgrade a set containing a restricted family to a normal generic candidate.

`BRAND_RESTRICTED` preserves discovery but deterministically returns `BLOCK_NORMAL_STOCK -> RESTRICTED_RIGHTS_REVIEW`; `REVIEW_REQUIRED` and `UNKNOWN` return `RIGHTS_REVIEW_HOLD`; only fully generic candidates may return `PASS_TO_NEXT_GATE -> NORMAL_STOCK_CANDIDATE`. Even that pass grants no production, submission, publication, legal-clearance, or gate-bypass authority. Derivative bundles and listing packages are outside the candidate schema.

H01-120 Semantic Family v1 adapts directly without rewriting family/Object Atlas identity, while the same envelope can later be produced by H01-123 Design Set composition. H01-122 does not start H01-123. With H01-122 DONE, H01-123 remains blocked because H01-111 and H01-121 are not DONE in current canon.

## 27. H01-121 deterministic taxonomy-first Family mapper standing

H01-121 maps eligible Object Atlas standalone subjects into candidate `TAXONOMIC` Semantic Family v1 artifacts without rewriting standalone identity. Live `category_path` is empty for all 43,005 eligible rows, so the mapper does not invent taxonomy from noun spelling. It groups only exact shared stored `wordnet_synsets[0]` evidence, preserves `candidate_seeds.id` as canonical family member identity, and leaves single-member primary synsets standalone. Synset punctuation is deterministically slugged only for schema-safe semantic keys while the original synset remains intact in definition/evidence.

The live read-only canary produced 14,718 candidate families containing 41,658 members, with 1,347 standalone singletons and maximum family size 34. Full family JSONL SHA-256 is `d89fb71efa3fb8d791712b2b7c0c513f4392bd8fa68422599f114b102095d0e8`; source projection fingerprint is `0e6996366d5201f11163af36b9c49ab6fd36e1b08854b88942216416cc933a56`. Object Atlas DB SHA-256 was unchanged before/after (`e56bdbbba1e70cca74f5f1b59439802d929f66a9fcb730278bc67d637901bf2e`).

Every family retains one taxonomy evidence record plus one Object Atlas record per member, defaults to `rights_class=REVIEW_REQUIRED`, and grants no production/submission/publication authority. Duplicate subject/raw IDs and normalized canonical-name collisions fail closed. Alias collisions are observations only with `merge_authorized=false`; shared synset evidence never authorizes canonical noun collapse. H01-122 remains independent and owns the brand/trademark rights gate.

This execution is Worker A of Founder-authorized H01-304 parallel canary attempt #2. It is isolated to browser resource `architect-primary`, branch `canary/h01-121-parallel-20260912` and `/home/kopiko/die-sessions/H01-121` under H01-303 mutable-worktree claim. Worker B's canonical H01-122 merge was preserved during publication reconciliation; H01-122 and `/srv/die` remained outside Worker A's mutation boundary.


## 2026-09-12 - H01-105 DONE/PASS via Mission Control reviewed canonical writeback

Mission Control task `H01-105` completed through automatic canonical intake, owner execution and no-review completion. Canonical graph transitions: `H01-105 READY->DONE`. Receipt: `company/company-os/die-h01/receipts/H01-105-mission-control-auto-acceptance.receipt.json`. No external marketplace submission, spend, credential mutation, or live-load authority was granted by this writeback.

## H01-304 two-worker parallel Architect canary acceptance

H01-304 is DONE/PASS. The live canary used H01-121 on the Windows `architect-primary` global browser resource and H01-122 on the H01-local `h01-display12-cdp9100` resource, with isolated worktrees and branches. Both workers wrote durable Mission Control checkpoints and reached durable terminal completion without sharing a mutable worktree or mutating `/srv/die`. The canary also exposed and remediated browser-resource identity, lease-attempt reconciliation, and browser-submit acceptance defects. Durable Mission Control terminal state is authoritative; an exact rendered chat marker is supplemental evidence rather than a completion prerequisite. Receipt: `company/company-os/die-h01/receipts/H01-304-two-worker-parallel-architect-canary.receipt.json`. H01-305 is now READY to scale engineering workers only by dependency-ready graph width.


## 29. H01-305 dependency-ready graph-width planning standing

H01-305 adds the read-only `graph_width_planner.py` preflight plus its machine-readable runtime contract. It reads the canonical graph at `refs/remotes/origin/main`, admits only `READY` tasks whose declared dependencies are canonically `DONE`, applies exact Founder authorization to Founder-gated nodes, and orders candidates deterministically by priority descending then task ID ascending. Unknown dependency state fails closed.

The planner consumes observed active browser/resource leases and mutable-worktree claims, excluding conflicts with active coordination or with already-selected tasks. Mutable repository writers must declare an unambiguous owner; the canonical shared `income-os.repo-write` resource prevents two such writers from entering the same plan. It does not acquire leases, claim worktrees, create tasks, transition tasks, or write the graph. Its output is a proposal that Mission Control must durably schedule and lease under the existing H01-300 through H01-304 contracts.

Regression coverage proves dependency width, active resource/lease exclusion, worktree and shared repo-write collision, Founder-gate exclusion, deterministic ordering, malformed coordination fail-closed behavior and no durable-state mutation. Receipt: `company/company-os/die-h01/receipts/H01-305-architect-graph-width-scaling.receipt.json`. H01-305 does not mark any unrelated task complete or alter Mission Control durable truth.


## 2026-09-12 - H01-305 DONE/PASS via Mission Control reviewed canonical writeback

Mission Control task `H01-305` completed through automatic canonical intake, owner execution and no-review completion. Canonical graph transitions: `H01-305 READY->DONE`. Receipt: `company/company-os/die-h01/receipts/H01-305-mission-control-auto-acceptance.receipt.json`. No external marketplace submission, spend, credential mutation, or live-load authority was granted by this writeback.


## 2026-09-12 - H01-020 DONE/PASS via Mission Control reviewed canonical writeback

Mission Control task `H01-020` completed through automatic canonical intake, owner execution and no-review completion. Canonical graph transitions: `H01-020 READY->DONE`. Receipt: `company/company-os/die-h01/receipts/H01-020-mission-control-auto-acceptance.receipt.json`. No external marketplace submission, spend, credential mutation, or live-load authority was granted by this writeback.

## H01-011 die-control Windows acceptance standing

H01-011 accepts the target Windows `die-control` failure domain for downstream control-plane work without performing cutover. Live Mission Control 0.8.45 is healthy on loopback `127.0.0.1:8891` from pinned runtime release `0844f813122d390f822ad6dc252cd197178e95f2`; `mc-mission-v1` is live and H01-011 checkpoints were observed directly in the WAL-backed SQLite database with `PRAGMA quick_check=ok`.

Universal MCP 0.1.0 is healthy on `127.0.0.1:8793` with 46 exposed tools and active GitHub/SSH broker paths. Cloudflare Tunnel exposes `universal-mcp.aethers.web.id` and external HTTPS health returned 200, while Mission Control remains loopback-only rather than directly public. The live configured principal registry contains eight explicit accepted/deferred principals.

DIE State Manager sovereignty remains intact: current writer-domain conformance returns one logical `die-state-manager`, one sole physical writer and zero unauthorized global-store writers; a live deployed-Mission-Control scan found zero forbidden Company Truth store references. Mission Control SQLite remains control-plane state, not Company Truth.

Backup/recovery evidence also passes: six retained pre-v0.8.x Mission Control SQLite snapshots each return `quick_check=ok`, and MC-008I already proved real controlled Windows reboot recovery with durable task/review continuity. Runtime Boot/Watchdog remain installed and the watchdog reports successful runs. No raw active-WAL copy is promoted as a valid backup.

H01-011 performed no H03 rebind, Runtime Gateway deployment, Canonical Feeder start, Supervisor start, scheduler cutover, legacy retirement or `/srv/die` mutation. With H01-011 DONE and H01-012 already DONE, H01-013, H01-014 and H01-015 become READY but are not started by this task.
