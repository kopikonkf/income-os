# Factory Console PRD V1

Status: FA-C002 DONE/PASS
Date: 2026-09-03
Product: Factory Asset Console
Primary operator: Founder
Inputs: `FA-C000`, `FA-C001`, Asset Blueprint v2 (`FA-019`), and Factory Core contract direction (`FA-100+`).

## 1. Product objective

Factory Console is a Founder-operated control plane for governed batch and mass production. Its purpose is to make Blueprint creation, batch intent, queue state, provider/capacity state and output lineage operable from one interface without duplicating Factory Core or provider runtime responsibilities.

The Console must be useful in two modes:

1. **Synthetic prototype mode** — all views operate from deterministic local fixtures; no live provider, credentials or production queue are touched.
2. **Bound Factory mode** — later tasks connect the same surfaces to Factory Core normalized APIs/events after the required contracts and canaries pass.

## 2. Product principles

1. **Control plane, not execution engine.** Queue ownership, routing, leases, retries, capacity and reconciliation belong to Factory Core.
2. **Semantic asset truth.** Derivatives never increase semantic asset count.
3. **Evidence before green.** Provider availability/capacity/policy states are observed or UNKNOWN; never guessed.
4. **Fail closed.** Disabled controls explain why they are unavailable rather than silently approximating backend capability.
5. **No vendor leakage.** Cookie/session/RPC/vendor endpoint fields never appear in Console contracts or UI state.
6. **Founder authority preserved.** Marketplace publication and red-zone actions stay outside Console unless explicitly added by a future governed task.
7. **Synthetic-first UI.** Visual/product iteration may proceed before live Factory Core binding.

## 3. Primary Founder workflows

### WF-01 — Prepare a semantic asset blueprint

Founder opens **Blueprint**, chooses one canonical asset type (`PHOTO`, `ISOLATED_OBJECT`, `ICON`, `OUTLINE`, `PATTERN`, `ANIMATION`), reviews semantic use-case identity, sets production constraints, and sees compile eligibility. Packaging formats/resolution/style changes must not mint a semantic asset.

### WF-02 — Prepare a bounded batch intent

Founder opens **Batch**, selects a compiled Blueprint reference, quantity, reusable consistency constraints and optional operator label. The screen previews the intended semantic count separately from packaging derivative count.

### WF-03 — Observe and control queue state

Founder opens **Queue** to see READY/RUNNING/PAUSED/RETRY_WAIT/SUCCEEDED/FAILED/BLOCKED-like states. Pause/resume/retry controls are enabled only when normalized Factory Core state says the command is legal. Synthetic mode demonstrates the UX but performs no execution.

### WF-04 — Inspect provider health/capacity/routing

Founder opens **Providers** to see each provider's eligibility, transport class, policy state, observed capacity and routing rationale. Grok can appear `OPTIONAL / DEFERRED` without making the whole pool unavailable.

### WF-05 — Inspect outputs and lineage

Founder opens **Output** to see semantic master cards, derivative packaging, hashes, QA/compatibility status and lineage. One semantic asset may have multiple delivery derivatives but is counted once.

## 4. Information architecture

```text
Factory Console
├── Blueprint
│   ├── Semantic Identity
│   ├── Asset Type
│   ├── Production Constraints
│   ├── Master / Delivery Preview
│   └── Compile State
├── Batch
│   ├── Blueprint Reference
│   ├── Quantity
│   ├── Consistency Controls
│   ├── Semantic-vs-Derivative Count Preview
│   └── Dispatch Authority State
├── Queue
│   ├── Summary Counters
│   ├── Job Table
│   ├── Progress / Attempt
│   ├── Pause / Resume / Retry affordances
│   └── Typed Failure / Reconciliation State
├── Providers
│   ├── Eligibility
│   ├── Transport
│   ├── Observed Capacity
│   ├── Policy Evidence
│   └── Routing Rationale
└── Output
    ├── Semantic Master Gallery
    ├── Derivatives
    ├── SHA-256 / dimensions / format
    ├── QA / Compatibility
    └── Lineage / Dedupe State
```

Global chrome must show the environment (`SYNTHETIC` vs later `BOUND`), no-live-provider warning in synthetic mode, and aggregate semantic/job counters.

## 5. Screen requirements

### 5.1 Blueprint

Required synthetic fields:
- blueprint ID and semantic asset ID;
- commercial use case and subject;
- six-mode asset type selector;
- producer class / native representation preview;
- master format and resolution where applicable;
- delivery recipe preview;
- style/preset, consistency and background controls as UI-only synthetic values;
- compile state: `VALID`, `BLOCKED`, or `UNKNOWN`.

No provider selector belongs in the Blueprint semantic identity section.

### 5.2 Batch

Required synthetic fields:
- batch ID/label;
- compiled blueprint reference;
- quantity bounded to a visible maximum in prototype data;
- semantic count preview;
- derivative estimate shown separately;
- style/consistency preset reference;
- action state explaining that synthetic mode cannot dispatch live work.

### 5.3 Queue

Required synthetic fields:
- job ID;
- semantic asset / blueprint reference;
- normalized provider ID;
- state;
- attempt/retry count;
- progress indicator where meaningful;
- typed failure code/reason;
- command affordance state.

Synthetic controls may change local display state for demonstration but must clearly label the action as `SIMULATED` and never perform network/provider calls.

### 5.4 Providers

Required synthetic fields:
- provider ID;
- transport (`SESSION_API`, `BROWSER_CDP`, etc.);
- eligibility state;
- observed capacity state;
- policy state;
- last evidence timestamp;
- routing rationale.

Provider cards must support Qwen, ChatGPT, Gemini, Manus, Duck.ai and optional/deferred Grok without treating Grok as global blocker.

### 5.5 Output

Required synthetic fields:
- semantic asset ID;
- master format/dimensions/hash;
- provider/source attempt;
- QA state;
- compatibility state;
- derivative list with format/purpose/hash placeholder;
- semantic count badge fixed at one per master family.

## 6. State model

The prototype should use normalized product states instead of vendor-specific strings.

### Environment
- `SYNTHETIC`
- later: `BOUND`

### Job
- `READY`
- `RUNNING`
- `PAUSED`
- `RETRY_WAIT`
- `SUCCEEDED`
- `FAILED`
- `BLOCKED`

### Provider eligibility
- `ELIGIBLE`
- `DEFERRED_OPTIONAL`
- `POLICY_BLOCKED`
- `AUTH_REQUIRED`
- `UNSUPPORTED`

### Capacity
- `UNKNOWN`
- `AVAILABLE`
- `CONSTRAINED`
- `UNAVAILABLE`

### QA / compatibility
- `PASS`
- `FAIL`
- `UNKNOWN`
- `COMPATIBLE`
- `COMPATIBILITY_UNKNOWN`
- `INCOMPATIBLE`

## 7. Synthetic fixture contract

`FA-C004` fixture data must include:
- six asset types;
- at least one draft Blueprint and one compiled-plan preview;
- one batch summary;
- queue examples spanning at least READY, RUNNING, RETRY_WAIT, SUCCEEDED and BLOCKED;
- all five current proven providers plus Grok optional/deferred;
- at least two output families demonstrating master + derivatives without semantic-count inflation;
- no credential, cookie, session token, vendor RPC ID, direct endpoint or raw auth body field.

All synthetic data must be obviously non-production and deterministic.

## 8. Interaction contract for FA-C004

The static shell must provide five navigation tabs/views. Navigation is client-local only. Queue action controls may demonstrate state transitions locally but must carry a `SIMULATED` label and cannot issue network requests.

Prototype implementation should avoid a framework dependency unless an existing repo frontend standard requires one. Current repository has no such standard, so a static HTML/CSS/JS shell is preferred for the first proof.

## 9. Visual/product direction

The Console should read as an operational production surface rather than a marketing dashboard:
- dense but legible data;
- explicit state badges;
- job/provider tables where scanning matters;
- gallery cards only for visual/output objects;
- persistent environment banner;
- primary batch controls visually separated from red-zone or unavailable actions;
- no invented real-time charts in synthetic prototype.

## 10. Security and authority boundaries

Prototype and future Console must not:
- store/export credentials or browser profile secrets;
- call provider endpoints directly;
- launch or own MUXIA/CDP sessions;
- bypass provider protections;
- infer capacity/quota from UI guesses;
- publish to marketplaces;
- mutate canonical DIE state directly;
- claim live execution from synthetic fixtures.

## 11. Non-goals for FA-C004

- Factory Core API/event integration (`FA-C003` and later).
- Real Blueprint compiler invocation (`FA-C005`).
- Real pause/resume/retry authority (`FA-C006`).
- Live provider/capacity feed (`FA-C007`).
- Real output lineage/QA backend (`FA-C008`).
- Authentication system for Console users.
- Packaging as Windows installer/native desktop app.

## 12. Acceptance criteria

`FA-C002` passes when:
1. all five Founder workflows are explicit;
2. five primary views and required fields are defined;
3. normalized job/provider/capacity/QA states are defined;
4. synthetic fixture requirements are explicit;
5. semantic-vs-packaging identity is preserved;
6. authority/security boundaries are explicit;
7. `FA-C004` can be built without resolving an unspecified product decision.

PASS. `FA-C004` may now implement the synthetic GUI shell while live Factory Core binding remains separately gated.
