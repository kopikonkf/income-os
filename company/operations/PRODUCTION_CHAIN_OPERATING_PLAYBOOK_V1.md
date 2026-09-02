# PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1

Status: CANONICAL OPERATING PLAYBOOK
Scope: Digital Income Empire · Pillar E · Division 001 · Linux production chain
Audience: Hermes, Worker, Division01, Executive, Founder
Mode: RESULT-FIRST / VERTICAL-SLICE

## 1. Purpose

This playbook defines the default operational workflow that turns an approved Object Atlas noun seed into a real publish-ready asset without forcing each runtime actor to rediscover its role.

The objective is observable production:

`Object Atlas seed -> Hermes -> Division01/Executive only when needed -> fixed Blueprint -> Kanban -> Worker -> production provider -> real artifact -> upscale/recovery -> metadata -> rights/IP + QA -> QC -> Founder manual QC -> READY_FOR_MANUAL_PUBLISH -> manual publish`

The atomic task graph remains the long-horizon journey and milestone map for DIE Linux completion. It is not a reason to pause a normal production cycle unless a graph node represents a real missing runtime prerequisite for that cycle.

## 2. Operating doctrine

1. Ship real vertical slices before polishing architecture.
2. Generate per seed noun; manage portfolio and reuse at family level.
3. Governance is normally family/Blueprint/batch scoped, not per-image cognition.
4. Reuse a fixed Blueprint while its family, product expression, rights assumptions, provider compatibility and quality requirements remain valid.
5. Division01 is not called for every image. Call it when semantic authoring or revision is actually required.
6. Executive is not called for every image. Call it for new family promotion, material strategy/risk challenge, or explicit revision/escalation.
7. Hermes owns orchestration, state, Kanban, retries and notification. Hermes does not invent missing commercial semantics.
8. Worker executes bounded jobs. Worker does not redefine strategy or spawn other workers.
9. MUXIA and future providers such as OAUTH are production engines, not authority actors.
10. Founder is interrupted only for login/credential blockers, paid/spend actions, irreversible publication/submission/cutover, and final manual rights/QC decisions.
11. No production cycle may silently fail.
12. Every real artifact produced in the early operational phase MUST generate Telegram progress notifications to Founder through Hermes.

## 3. Production cadence

### 3.1 New-cycle cadence

Hermes may start at most ONE new seed production cycle every 3 hours.

Default schedule:

`0 */3 * * *` UTC

This cadence exists to protect provider limits and prevent uncontrolled queue growth.

### 3.2 What is NOT delayed by the 3-hour cadence

The three-hour rule limits only the creation of a new production cycle. Once a cycle exists, the following continue immediately without waiting for the next cron tick:

- Division01/Executive completion;
- Worker execution;
- provider generation;
- artifact detection;
- retry/recovery;
- upscale;
- metadata;
- QA/QC;
- Telegram progress reporting;
- Founder-QC package preparation.

If a prior production cycle is still active, Hermes continues/reconciles that cycle rather than starting another overlapping cycle unless parallelism has explicitly been enabled for the current production stage.

## 4. Selection unit: seed noun vs family

### 4.1 Atomic production input

The atomic production input is an approved Object Atlas seed noun.

Example:

`SEED-000029 -> shopping bag`

Hermes selects the next eligible seed from the canonical Object Atlas database through the deterministic read-only phase-0 selector:

`python3 company/die-agents/hermes/production_seed_selector.py`

The selector ranks approved `U1-raster` seeds by validated demand and excludes seeds already materialized in production workspaces. The production cron attaches this selector as an agent-mode preflight script, so its JSON stdout is injected before Hermes reasoning begins. Hermes MUST consume this injected selection before any ad-hoc repository/database discovery. `SELECTED` chooses the noun only; it does not authorize semantic invention, provider execution, submission or publication.

### 4.2 Family role

Family is a portfolio-management and Blueprint-reuse unit, not the lowest-level generation unit.

Family is used for:

- related-seed grouping;
- Blueprint reuse;
- semantic variation planning;
- duplicate prevention;
- portfolio balancing;
- sibling similarity/cannibalization control;
- batch scaling and production statistics.

Rule:

`Generate per seed noun. Manage and scale per family.`

### 4.3 Seed selection priorities

Hermes prefers a seed that is:

1. approved in Object Atlas;
2. not already active in another unfinished cycle;
3. not recently produced beyond the family variation policy;
4. compatible with an existing fixed Blueprint, or suitable for a new Blueprint;
5. useful for current portfolio balance;
6. not quarantined by prior hard rights/safety failures.

When several seeds are equivalent, Hermes chooses the least-recently-produced eligible seed.

## 5. Role responsibilities

## 5.1 Hermes — production orchestrator

Hermes owns:

- production-cycle scheduling;
- seed selection;
- family lookup;
- determining whether a reusable fixed Blueprint exists;
- routing semantic work to Division01;
- routing strategic review to Executive only when required;
- freezing the accepted Blueprint for execution;
- Kanban/card creation and state transitions;
- spawning Workers;
- monitoring Worker and provider completion;
- retries/recovery;
- artifact detection;
- triggering postprocess, metadata, QA and QC;
- assembling manual-publish package;
- Telegram milestone reporting;
- anti-stall follow-up.

Hermes MUST NOT:

- invent Division01 commercial semantics;
- silently alter a fixed Blueprint;
- grant spend, submission or publication authority;
- hide failed cycles;
- claim human rights clearance on behalf of Founder.

## 5.2 Division01 — semantic author

Division01 owns semantic authoring when a new or revised Blueprint is needed.

Division01 produces or revises:

- buyer/use-case interpretation;
- product expression;
- scene intent;
- master prompt semantics;
- banned/required visual elements;
- variation strategy;
- metadata semantic intent;
- family differentiation guidance.

Division01 is called when:

- no fixed Blueprint exists for the selected family/use case;
- the current Blueprint is stale or incompatible;
- QA/QC outcomes indicate semantic defects;
- family overlap requires new differentiation;
- Hermes has a bounded semantic question it may not answer itself.

Division01 is NOT called for every artifact generated from a still-valid fixed Blueprint.

## 5.3 Executive — strategic challenger

Executive is a second-line reviewer, not a per-image gate.

Executive is called when:

- a new family/Blueprint is being promoted into production use;
- Division01 proposes a materially new product expression;
- repeated QA/QC or market outcomes challenge the existing family strategy;
- portfolio cannibalization or strategic opportunity cost is material;
- an explicit escalation requires company-level review.

Executive does not author the Division01 Blueprint in place and does not grant production/submission/publication authority.

## 5.4 Worker — bounded executor

Worker receives a narrow Hermes job and executes it.

Typical Worker duties:

- validate bounded job input;
- prepare provider/MUXIA job request from the fixed Blueprint;
- execute deterministic compilation or transformation;
- write results only in assigned workspace;
- return structured result to Hermes.

Worker MUST NOT:

- invent missing commercial semantics;
- rewrite the fixed Blueprint;
- spawn Workers;
- publish/submit;
- access credentials unnecessarily;
- write outside its workspace.

## 5.5 MUXIA / alternate production provider

MUXIA and future engines such as OAUTH are interchangeable provider/production layers.

They may:

- open/use an assigned authenticated production profile;
- submit the fixed prompt/job;
- detect provider completion;
- extract original artifact bytes;
- return provider/job evidence.

They do not decide what should be produced and do not grant authority.

## 5.6 Founder

Founder retains:

- final manual visual QC during the early phase;
- human rights/IP clearance where required;
- spend approval;
- irreversible submission/publication decisions;
- account/credential actions;
- production-policy overrides.

## 6. Blueprint lifecycle

### 6.1 Reuse-first

Before requesting cognition, Hermes checks for a fixed Blueprint compatible with:

- seed family;
- intended product expression;
- provider capability;
- current rights/safety assumptions;
- required output quality;
- active marketplace route.

If compatible, reuse it.

### 6.2 New Blueprint path

If no reusable Blueprint exists:

`Hermes -> Division01 draft -> Executive challenge if required -> Hermes routes requested revision -> Division01 final -> Hermes freezes fixed Blueprint`

The Executive step is optional for routine continuation and required only where family-promotion or material challenge policy says so.

### 6.3 Fixed Blueprint

A fixed Blueprint contains enough information for deterministic production without repeated cognition:

- Blueprint/family identity;
- eligible seed scope;
- buyer/use-case;
- product expression;
- master prompt;
- required elements;
- forbidden elements;
- composition/quality requirements;
- variation rules;
- provider/output constraints;
- metadata intent;
- revision reason/history.

Once fixed, Worker and provider execute it without semantic improvisation.

## 7. Kanban and runtime states

Hermes creates one production card per production cycle.

Minimum state sequence:

`SELECTED`
`BLUEPRINT_REQUIRED` or `BLUEPRINT_READY`
`WORKER_QUEUED`
`WORKER_RUNNING`
`PROVIDER_RUNNING`
`ARTIFACT_CREATED`
`POSTPROCESSING`
`QA_RUNNING`
`QC_RUNNING`
`WAITING_FOUNDER_QC`
`READY_FOR_MANUAL_PUBLISH`
`MANUALLY_PUBLISHED`

### 7.1 Human-gated cards are parked, not global blockers

During the current throughput-observation phase, `WAITING_FOUNDER_QC` and `READY_FOR_MANUAL_PUBLISH` are terminal states for Hermes autonomous responsibility for that production cycle. The card remains durable and reviewable, but it is **PARKED_HUMAN_GATE** for production scheduling purposes.

A parked human-gated card:

- does not disappear or lose lineage;
- remains visible to Founder and the watchdog;
- may be resumed later when Founder provides an explicit decision;
- MUST NOT block selection of an independent eligible seed on a later production cadence slot;
- MUST NOT be repeatedly reported as if Hermes can autonomously advance it.

Only an **actionable unfinished card** takes precedence over new work. An actionable unfinished card is one for which Hermes/Worker/provider can still make progress under existing authority without Founder input. If all remaining cards are parked human gates and at least one eligible seed exists, Hermes MUST start one new seed in the available cadence slot.

Failure states:

`BLOCKED_LOGIN`
`BLOCKED_PROVIDER_LIMIT`
`BLOCKED_RIGHTS`
`BLOCKED_QA`
`BLOCKED_QC`
`FAILED_RETRYABLE`
`FAILED_TERMINAL`

Every state transition must be attributable to a real observable event. Kanban is operational state, not decorative documentation.

## 8. Worker and provider execution

1. Hermes creates the bounded job workspace.
2. Hermes dispatches Worker.
3. Worker returns provider/MUXIA job request.
4. Hermes marks `WORKER_RUNNING -> PROVIDER_RUNNING`.
5. Production provider submits the fixed prompt/job.
6. Provider completion must result in a real filesystem artifact.
7. Screenshot-only browser appearance is not final completion when original bytes are extractable.
8. Hermes records `ARTIFACT_CREATED` only after a real artifact exists.
9. Provider errors are retried according to bounded retry policy; login/rate-limit failures are reported, not hidden.

## 9. Postproduction

After the real artifact exists:

1. Detect dimensions/format.
2. If below route requirement and recoverable, upscale/recover.
3. Preserve original and final artifact lineage.
4. Compile title/description/keywords/metadata from seed + family + fixed Blueprint.
5. Run rights/IP preflight.
6. Run deterministic technical QA.
7. Run visual/commercial QC.
8. Package final asset and metadata for Founder manual QC.

Upscale is conditional. If native output already satisfies route requirements, skip unnecessary upscale.

## 10. Rights/IP and QC

Automated checks may identify:

- text;
- logo/trademark signals;
- watermark;
- obvious visual defects;
- dimensions/format;
- lineage;
- duplicates;
- safety signals.

Automated systems MUST NOT pretend to be Founder human visual rights clearance.

During the early production phase, a publish-ready artifact reaches:

`WAITING_FOUNDER_QC`

Founder checks the final image and either:

- approves -> `READY_FOR_MANUAL_PUBLISH`;
- rejects/recreate -> Hermes routes correction;
- flags rights issue -> `BLOCKED_RIGHTS`.

Manual publish remains outside autonomous authority until Founder changes that policy.

## 11. Mandatory Telegram reporting

During the early operational phase, Hermes MUST report production progress to Founder through the configured Telegram target.

Hermes uses the configured home target, currently reachable through:

`hermes send --to telegram ...`

No token, chat secret or credential value is written into this playbook.

### 11.1 Required messages

For each artifact/cycle, send:

1. `PRODUCTION_STARTED`
   - task/cycle id;
   - selected seed noun;
   - family if known;
   - Blueprint status;
   - intended provider.

2. `ARTIFACT_CREATED`
   - task id;
   - provider;
   - artifact filename/path basename;
   - dimensions;
   - generation duration if available.

3. `QA_QC_UPDATE`
   - PASS / BLOCKED / FAIL;
   - major reason only;
   - final dimensions;
   - QC score if available.

4. `WAITING_FOUNDER_QC`
   - task id;
   - final asset location;
   - only remaining human decision.

5. `READY_FOR_MANUAL_PUBLISH`
   - task id;
   - package location;
   - marketplace route/package status.

### 11.2 Failure message

Any cycle that cannot continue MUST send one concise failure message containing:

- task id;
- failed stage;
- retryable yes/no;
- short error/reason;
- next automatic action or Founder action required.

No silent production failure is allowed.

## 12. Production cron behavior

The dedicated production cron runs every 3 hours and is separate from Operator-v2 monitoring/watchdog jobs. Each tick derives continuity from durable Kanban/runtime state, not from the previous cron response; conversational run-to-run continuity is disabled so stale summaries cannot override current scheduling policy.

On each production tick Hermes:

1. reads this playbook;
2. checks whether an **actionable** unfinished production cycle should be continued first; parked human-gated cards (`WAITING_FOUNDER_QC`, `READY_FOR_MANUAL_PUBLISH`) are excluded from this blocking set;
3. if no actionable unfinished cycle blocks the slot, selects at most one eligible seed noun even when older parked human-gated cards still await Founder action;
4. sends `PRODUCTION_STARTED` Telegram message;
5. creates/updates Kanban;
6. obtains/reuses fixed Blueprint;
7. dispatches Worker;
8. runs provider generation;
9. continues postproduction immediately;
10. reports all required Telegram milestones;
11. parks the card at Founder gates instead of guessing approval; future cadence slots may start independent eligible seeds.

### 12.1 Material-progress outcome semantics

A production tick is a business-level success only when at least one observable material outcome occurred:

- a new eligible seed cycle was started;
- an actionable existing cycle advanced to a later durable state;
- a real artifact was created; or
- postproduction advanced an artifact to a new durable gate.

Merely re-reading an unchanged parked human-gated card is **not** material progress and MUST NOT be presented as a successful production cycle. If no material progress is possible, Hermes must emit an explicit `PRODUCTION_TICK_NO_PROGRESS` / `BLOCKED` summary with reason and next action; `[SILENT]` is forbidden for a scheduled production tick.

A provider limit or login issue does not cause another seed to be started as compensation during the same tick.

## 13. Retry and anti-stall policy

- Retry only retryable technical/provider failures.
- Do not retry rights/safety hard vetoes unchanged.
- Do not create multiple duplicate cycles for the same seed due to timeout ambiguity.
- If provider status is uncertain, inspect artifact/state before retrying.
- If the same failure repeats, escalate via Telegram and Kanban instead of infinite retry.
- Hermes follows actionable active cards until an autonomous terminal/human gate; cards do not disappear because a cron run ends.
- `WAITING_FOUNDER_QC` and `READY_FOR_MANUAL_PUBLISH` are parked human gates and do not serialize unrelated seed production.
- The watchdog may remind/escalate parked cards separately without consuming the three-hour new-seed production slot.

## 14. Atomic task graph relationship

`company/muxia-task-graph-v1.json` remains the canonical engineering journey and milestone map for Linux migration, MUXIA hardening and DIE capability completion.

Production policy:

- completed atomic tasks remain evidence of capability;
- unfinished atomic tasks continue as engineering work;
- normal production does not wait for unrelated future nodes;
- a task blocks production only when its missing capability is an actual prerequisite of the current cycle;
- real production failures may create/refine atomic tasks for subsequent engineering improvement.

This creates the loop:

`Build -> Run -> Observe -> Fix -> Verify -> Scale`

not:

`Document every possible future condition before running.`

## 15. Early-phase success metrics

Hermes reports and accumulates:

- cycles started;
- artifacts generated;
- generation success rate;
- median generation time;
- upscale/recovery rate;
- QA pass/block/fail counts;
- QC score distribution;
- Founder approve/reject count;
- ready-to-publish count;
- manually published count;
- provider limit/login failures;
- family/seed production counts.

These metrics matter more than the number of documents/contracts produced.

## 16. Current manual-publish authority boundary

Until Founder changes policy:

- automated generation: allowed within approved zero-spend production policy;
- automated postprocess/QA/QC: allowed;
- Telegram reporting: required;
- final Founder manual QC: required;
- marketplace upload/submission/publication: manual Founder action;
- paid spend: explicit Founder authorization required.

## 17. Operational summary by actor

Hermes:
`select -> route cognition only if needed -> freeze/reuse Blueprint -> Kanban -> Worker -> provider -> postprocess -> QA/QC -> Telegram -> Founder gate`

Division01:
`author/revise semantics and fixed Blueprint when requested; do not operate the production queue`

Executive:
`challenge new/material family strategy when requested; do not gate every image`

Worker:
`execute bounded job exactly; do not invent semantics`

MUXIA/OAUTH/provider:
`generate and return real artifacts`

Founder:
`human rights/QC + irreversible publish/spend/account authority`

## 18. North-star behavior

The system is successful when Founder can be away from the VPS and still receive concise Telegram evidence that the production organism is moving from seed to artifact to QA/QC, with intervention required only at meaningful human gates.
