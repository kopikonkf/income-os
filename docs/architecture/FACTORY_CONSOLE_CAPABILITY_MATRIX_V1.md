# Factory Console Capability Matrix V1

Status: FA-C001 DONE/PASS
Date: 2026-09-03
Inputs: `FA-C000` Factory Console track ratification and `FA-W010` GenWHITE clean-room capability research.

## Scope and evidence rule

This matrix translates observable product patterns into Factory-owned requirements. It does not copy GenWHITE implementation and does not infer unsupported backend behavior. An `OBSERVED` state means the public research supports the product-level pattern. `PARTIAL` means only a user-facing outcome is supported. `UNKNOWN` means the implementation/semantics are not supported by the source and the Factory requirement is independently specified.

## Capability matrix

| ID | Product/operator capability | Source evidence | What the source actually supports | Factory-owned requirement | Canonical owner | Console surface | Fail-closed behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FCAP-001 | Batch / Auto-Pilot run | OBSERVED | Auto-Pilot generation is advertised | Founder creates a bounded batch intent containing blueprint reference, quantity and production constraints | Factory Core queue (`FA-105`) | Batch | No direct provider dispatch from UI |
| FCAP-002 | Queue state | UNKNOWN | Public research does not establish queue internals/fairness | Durable ordered job states with idempotent ownership and reconciliation | `FA-105` | Queue | UI renders `UNKNOWN`/blocked rather than inventing progress |
| FCAP-003 | Pause / resume | UNKNOWN | Exact active-batch pause/resume semantics are not established | Governed pause/resume commands operate on Factory Core job state only | `FA-105` | Queue / Batch | If backend capability is absent, control is disabled with reason |
| FCAP-004 | Retry | UNKNOWN | Retry count/backoff not established | Typed retryable failures may be retried only under Factory retry policy | `FA-105` | Queue | UI cannot force unlimited retry |
| FCAP-005 | Rate-limit / capacity visibility | UNKNOWN | Rate-limit telemetry not established | Show observed capacity state, evidence age, routing rationale and typed provider failure | `FA-102`, `FA-104`, `FA-107` | Providers | Guessed quotas are prohibited; stale/unknown remains visible |
| FCAP-006 | Automatic download | OBSERVED | Automatic download is advertised | Provider-original bytes are durably ingested automatically and surfaced after validation | `FA-106` | Output | No output card until durable validated bytes exist |
| FCAP-007 | Automatic save/load | OBSERVED | Automatic save/load for unfinished/not-downloaded results is advertised | Console reconstructs state from canonical Factory state after reload/restart | `FA-105`, `FA-107` | Queue / Output | Browser-local state cannot become source of truth |
| FCAP-008 | Output gallery | PARTIAL | Product output/download behavior is observable, but internal lineage/QA model is unknown | Gallery shows semantic asset, immutable master, derivatives, hashes, QA, compatibility and lineage | `FA-030`, `FA-106`, `FA-C008` | Output | Derivatives never inflate semantic asset count |
| FCAP-009 | 2K / 4K output choice | OBSERVED | 2K/4K product choices are advertised | Resolution is a Blueprint/master-spec control constrained by provider capability and marketplace profile | Blueprint compiler + provider contract | Blueprint | Unsupported size is rejected before dispatch |
| FCAP-010 | Style presets | OBSERVED | 31 public presets are advertised | Factory presets are versioned UI conveniences compiling to Blueprint/prompt constraints; presets do not mint semantic IDs | Blueprint / Console | Blueprint | Preset metadata cannot bypass identity invariants |
| FCAP-011 | Consistency controls | OBSERVED | Style/color/description consistency controls are advertised | Batch-level reusable constraint set is versioned and compiled into each job intent | Blueprint / Console | Blueprint / Batch | Missing version/constraint state blocks reproducibility claim |
| FCAP-012 | Background controls | OBSERVED | White, green-screen and HEX/custom background controls are advertised | Background is a typed production constraint with family-aware validation | Blueprint compiler | Blueprint | Invalid family/background combination fails compile |
| FCAP-013 | Thin-client / server-side execution | OBSERVED PRODUCT CLAIM | Public page states generation processing is server-side | Console remains control plane; Factory Core/provider adapters execute work | `FA-C000`, `FA-100+` | Global | GUI contains no credentials, browser ownership or vendor wire calls |
| FCAP-014 | Provider health | FACTORY REQUIREMENT | Not established by GenWHITE research | Normalize READY/AUTH_REQUIRED/CAPACITY_UNAVAILABLE/DEGRADED/OFFLINE/POLICY_BLOCKED | `FA-100`, `FA-102`, `FA-103` | Providers | Unknown/provider-policy gate is not rendered as healthy |
| FCAP-015 | Grok optionality | FACTORY DECISION | GenWHITE evidence is irrelevant to Grok availability | Optional/deferred providers never block healthy eligible pool | `FA-W019`, `FA-104` | Providers | Optional provider is visually isolated from global batch readiness |
| FCAP-016 | Errors and recovery | UNKNOWN | Crash reconciliation is not established | Typed failure codes, retryability and reconciliation state are visible to Founder | `FA-105`, `FA-107` | Queue / Providers | No silent retry or false success |

## Navigation model implied by the matrix

The first synthetic Console shell must expose five primary views:

1. **Blueprint** — semantic mode, production constraints, resolution, style/preset and compile state.
2. **Batch** — quantity, reusable consistency constraints and bounded batch intent.
3. **Queue** — job state, progress, pause/resume/retry affordances and typed failure reasons.
4. **Providers** — eligibility, observed capacity, policy state, transport class and routing rationale.
5. **Output** — semantic master, derivative packaging, hash/lineage/QA state and duplicate suppression.

These are navigation surfaces, not new sources of truth.

## Authority boundary

```text
Factory Console (Founder intent + observation)
    -> Factory Core (queue/router/capacity/retry/reconciliation)
    -> web-ai-adapter (provider normalization)
    -> SESSION_API / BROWSER_CDP / later approved transport
    -> MUXIA runtime when browser-backed
```

The Console must not contain provider cookies/session tokens, direct vendor endpoints/RPC IDs, browser automation, marketplace publication actions, canonical-state mutation outside Factory Core, or independent semantic-ID generation.

## Acceptance

PASS. Batching, queue, pause/resume, retry/rate-limit visibility, automatic save/download, output gallery and style-control patterns are mapped to Factory-owned requirements. Unsupported GenWHITE semantics remain explicitly `UNKNOWN`; no proprietary implementation is inferred or copied.
