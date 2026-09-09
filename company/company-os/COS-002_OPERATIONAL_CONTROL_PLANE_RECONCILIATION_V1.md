# COS-002 — Operational Control-Plane Authority Reconciliation v1

Status: ACCEPTED ANALYSIS / NO CONSTITUTIONAL MUTATION
Date: 2026-09-09
Authority: subordinate to `CONSTITUTION.md`. This artifact is an evidence-backed reconciliation and does not itself transfer authority.

## 1. Decision summary

The current DIE canon and the current Mission Control runtime have diverged in one important way:

- **Canonical governance still names `hermes-operator` as the single operational control plane and mission owner.**
- **Mission Control has mechanically proven most of the control-plane functions that Hermes was originally expected to provide:** deterministic intake, eligibility, leases, owner routing, bounded failover, independent review routing, canonical task progression, reboot recovery, health supervision and durable attempt/evidence lineage.

This is governance drift, not permission to silently replace Hermes.

The recommended target is:

```text
Founder
  = sovereign constitutional authority

Authorized cognition / canonical source
  = semantic proposals, bounded decisions, mission/work intent

DIE State Manager
  = sovereign physical writer of canonical company operational truth

Mission Control
  = deterministic operational control/enforcement plane
    intake -> eligibility -> lease -> dispatch -> failover -> review -> recovery -> progression

Workers / provider principals / delegated executors
  = bounded cognition or execution

Hermes
  = replaceable operational specialist / compatibility edge / legacy adapter if evidence still justifies it
    NOT a second control plane
```

Mission Control must not become Company Truth, strategic cognition, capital authority, or unrestricted DEV authority.

## 2. Sources reconciled

Current company canon reviewed:

- `CONSTITUTION.md`
- `COMPANY_BRAIN.md`
- `PROTOCOLS/agency-contract-v0.md`
- `company/identity-registry.json`

Mission Control evidence reviewed:

- `MC-008A` durable owner-attempt lineage — DONE
- `MC-008B` retry/alternate-owner policy — DONE
- `MC-008C` automatic bounded cross-principal failover — DONE
- `MC-008D` live failover acceptance — DONE
- `MC-008E` deterministic canonical work-intake contract — DONE
- `MC-008F` automatic DIE/Factory feeder — DONE
- `MC-008G` automatic intake-to-DONE + reviewed canonical writeback — DONE
- `MC-008H` Windows boot/runtime watchdog — DONE
- `MC-008I` reboot recovery/auth-honesty acceptance — DONE
- `MC-008J` 24-hour unattended soak — **SOAK RUNNING / final acceptance not yet available**
- `MC-009D` privileged delegated-execution broker — **BLOCKED / not yet accepted**

Live Mission Control during this reconciliation: v0.8.15, feeder enabled with one-card cap, reviewer separation active, dynamic principal READY/BUSY/OFFLINE/DEFERRED states observed, and the MC-008J baseline records spend/external-submission/credential-mutation authority as false.

## 3. Reconciliation matrix

| Canonical doctrine / role | Current canon | Mission Control evidence | Reconciliation decision | Ratification? |
|---|---|---|---|---|
| Founder sovereignty | Founder owns Northstar, capital, risk, constitutional change, autonomy promotion, irreversible approval | MC Founder/red-zone gates fail closed; FA-124 was kept WAITING_APPROVAL | **KEEP AS-IS** | No |
| One physical writer of company operational truth | DIE State Manager only | MC has its own operational DB and also performs governed Git task-graph writeback | **KEEP State Manager sovereignty; explicitly separate company operational truth from engineering/task-graph publication domain. MC must not claim Company Truth.** | Clarifying amendment recommended |
| One operational control plane | `hermes-operator` | MC now performs deterministic intake/routing/lease/failover/review/watchdog/progression | **SUPERSEDE CANDIDATE: Mission Control after promotion gates** | **Yes** |
| Mission operational ownership | Hermes accepts committed mission and delegates jobs | MC Work Card lifecycle and canonical-source identity now drive execution deterministically | **Move lifecycle ownership to Mission Control; semantic mission/work authority stays with Founder/canonical authorized source** | **Yes** |
| Runtime cognition | Propose/decide within scope; no worker orchestration | MC routes replaceable AI principals by capability/runtime state | **KEEP principle. Principals do cognition; MC orchestrates.** | Clarification only |
| Independent review | Old canon does not make an independent reviewer mandatory for every eligible path | MC reviewer separation is explicit; Claude currently reviewer-only | **PROMOTE as deterministic governance invariant for review-required work** | Yes if constitutionalized |
| Retry/failover | Hermes anti-macet/orchestration responsibility | MC-008A-D proves immutable attempt lineage + bounded alternate-owner failover | **MOVE to Mission Control policy engine** | Yes as part of control-plane transfer |
| Runtime health/recovery | Hermes cron/monitoring + manual/operator recovery model | MC-008H/I proves component watchdog + reboot recovery/auth honesty | **MOVE deterministic L0/L1 recovery to Supervisor/MC; engineering defects escalate** | Yes as role clarification |
| Canonical progression | Hermes semantic mutation -> State Manager | MC feeder/writeback can discover/advance Git task nodes after review | **MC may enforce/publish only in explicitly governed Git task-graph domain; company operational records remain State Manager governed** | Yes, clarify domain boundary |
| Chief Executive Architect DEV | Founder-invoked, not runtime actor, privilege non-inheritable | MC has a `chatgpt-architect` runtime principal and standalone Architect MCP; MC-009D plans proactive delegated execution | **DO NOT IDENTIFY `chatgpt-architect` runtime principal with constitutional DEV plane. Preserve DEV separation.** | **Yes / identity clarification required** |
| Proactive Architect engineering | Not authorized as autonomous DEV under current Constitution | MC can route tasks to `chatgpt-architect`; direct privileged execution would conflict with DEV/runtime separation | **BLOCK unrestricted proactive DEV. Allow only task-scoped delegated execution after MC-009D or explicit Founder invocation.** | Yes |
| Hermes existence | Constitutional operational orchestrator | Linux Hermes exists and works; unique future value not yet dispositioned | **DO NOT DELETE HERE.** `OPS-002` later decides KEEP/DEMOTE/RETIRE after MC-008J final evidence | No immediate deletion |
| OpenCode | Worker/executor | Linux Worker-001 accepted; not needed as control plane | **Keep only as optional bounded/ephemeral executor where capability/economics justify it** | No constitutional transfer required |
| Spend / budget / external market action | Founder-gated at current A0 | MC retry policy explicitly excludes spend/submission/credential/red-zone from automatic failover | **KEEP AS-IS** | No |
| Current autonomy level | A0 Founder-ratified | MC has more internal deterministic automation than old A0 wording anticipated | **A0 remains legally/canonically current. Clarify that reversible internal orchestration is not the same as financial/market autonomy. No A1 promotion in COS-002.** | Yes for wording; autonomy promotion remains separate Founder decision |

## 4. Writer-domain clarification

A direct replacement of `die-state-manager` with Mission Control is rejected.

The recommended domain model is:

### Canonical company operational truth

Examples: ratified decisions, economic evidence, mission/business state, authoritative events and governed company memory.

```text
semantic author
 -> typed request/event/evidence
 -> DIE State Manager
 -> canonical company operational store
```

### Mission Control operational state

Examples: leases, attempt lineage, dispatch/wake queue, runtime classification, failover state, review workflow, watchdog state.

This is durable control-plane state, but it does not supersede constitutional Northstar/decision/economic truth.

### Governed engineering/task-graph Git publication

Mission Control currently performs isolated-clone, validated PR/merge writeback for accepted task-graph transitions. This may remain a separately governed publication domain provided that:

1. source SHA and task identity are pinned;
2. only allowlisted graph/LSP/receipt files change;
3. required validation passes;
4. reviewer/authority requirements pass;
5. no financial, market, credential or irreversible authority is inferred;
6. company operational truth that belongs to State Manager is not silently redefined by Git writeback.

This distinction closes the apparent one-writer conflict without weakening State Manager sovereignty.

## 5. Architect identity conflict

Current company Constitution defines **Chief Executive Architect DEV** as Founder-invoked and not a runtime actor.

Mission Control separately uses logical principal `chatgpt-architect` as a runtime cognition/ownership principal. Current Mission Control planning (`MC-009D`) already contains the correct future direction: proactive Architect cognition should use Universal Mission Protocol and task-scoped delegated execution, while the standalone privileged Architect surface remains a separate interactive engineering/control plane.

The constitutional bridge must therefore state:

```text
chief-executive-architect-dev
  = privileged Founder-invoked DEV authority
  = not autonomous runtime identity

chatgpt-architect
  = replaceable runtime cognition identity for architecture/governance/incident analysis
  = no inherited unrestricted DEV privilege
  = proactive execution only through task-scoped delegated broker after MC-009D acceptance

interactive Founder invocation
  may enter the DEV plane under explicit authority
```

Until this is ratified and MC-009D is accepted, Mission Control must not treat autonomous routing to `chatgpt-architect` as blanket authorization for unrestricted filesystem/Git/service mutation.

## 6. Promotion gates for Mission Control control-plane authority

Mission Control may be proposed as the canonical operational control plane only when all are true:

1. `MC-008J` final receipt says `FULLY_UNATTENDED_24X7_ACCEPTED`.
2. No soak violation: no operator-created recovery Work Cards, duplicate publication, stale lease, silent quota loop or unauthorized red-zone action.
3. `MC-009D` delegated execution contract is accepted so proactive Architect work cannot inherit unrestricted DEV authority.
4. State Manager / Mission Control writer-domain boundary is implemented or explicitly conformance-tested.
5. Founder ratifies the exact amendment packet in `COS-002_FOUNDER_RATIFICATION_PACKET_V1.md`.
6. Ratified changes are applied atomically to Constitution/Company Brain/Agency Contract/identity registry and validated for internal consistency.
7. Hermes is not deleted by the promotion itself. Its later role is decided by `OPS-002` from evidence.

## 7. What can change without Founder constitutional ratification

- Design/test incident taxonomy (`OPS-001`).
- Continue MC-008J observation.
- Continue MC-009 engineering after its dependencies open.
- Prepare State Manager integration/conformance tests.
- Measure Hermes/OpenCode unique runtime value.
- Improve observability that does not widen authority.

## 8. What cannot change without Founder ratification

- Replacing `hermes-operator` as the named company operational control plane.
- Giving Mission Control mission/business authority broader than committed canonical work.
- Conflating `chatgpt-architect` runtime cognition with Chief Executive Architect DEV.
- Promoting A0 -> A1/A2/A3.
- Giving Mission Control autonomous spend, external submission/publication, credential mutation, new-vendor or irreversible authority.
- Removing DIE State Manager sovereignty over canonical company operational state.

## 9. COS-002 acceptance

**PASS.** The authority drift is mapped, preserved invariants are explicit, Mission Control promotion is gated rather than assumed, the Architect identity conflict is made explicit, and a separate exact Founder-ratification packet is prepared. No constitutional file, identity registry, Mission Control runtime, Hermes runtime, State Manager or Aether estate was mutated by this task.
