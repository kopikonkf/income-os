# COS-002 — Founder Ratification Packet: Mission Control Operational Control Plane v1

Status: **PREPARED / NOT RATIFIED**
Prepared: 2026-09-09
Decision authority: Founder only

This packet is intentionally inert. Merely merging this packet does **not** amend `CONSTITUTION.md`, change autonomy level, transfer authority, disable Hermes, or grant Mission Control spend/market/credential authority.

## A. Recommended Founder decision

**Recommended decision after all promotion gates pass:**

> Ratify Mission Control as DIE's single deterministic operational control/enforcement plane, while preserving Founder sovereignty, DIE State Manager as the canonical company operational-state writer, Chief Executive Architect DEV as Founder-invoked/non-runtime authority, and all existing financial/market/credential/irreversible Founder gates. Hermes loses unique control-plane primacy but is not deleted; its retained role is decided separately from evidence.

**Recommended decision today while MC-008J and MC-009D are incomplete:** `DEFER_RATIFICATION_UNTIL_GATES_PASS`.

## B. Required evidence attached to a future ratification event

- MC-008J sanitized final 24h receipt with `FULLY_UNATTENDED_24X7_ACCEPTED`.
- MC-009D delegated-execution acceptance.
- Writer-domain conformance evidence proving Mission Control does not supersede State Manager company truth.
- Final diff of the four governance files below.

## C. Exact proposed constitutional amendments

The text below is the proposed content direction to apply **only after Founder ratification**. The implementation task is `COS-004`.

### C1. `CONSTITUTION.md` — autonomy target clarification

Replace the actor-specific wording in §1.5 with:

```markdown
| Level | Nama | Authority | Evidence untuk naik |
|---|---|---|---|
| A0 | Observed / governed internal automation | Operational control plane may perform deterministic, reversible internal orchestration and recovery only inside already-ratified policy. Financial commitment, market submission/publication, credential/permission mutation, new mission classes and irreversible actions remain Founder-gated. | Uptime + event/evidence log terbaca; red-zone gates fail closed |
| A1 | Bounded execution | Operational control plane may execute already-committed missions without Founder approval per internal step, within explicit authority envelopes | 1 externally useful artifact/result delivered with complete evidence and bounded side effects |
| A2 | Bounded origination | Operational control plane may open missions only inside Founder-ratified mission classes and budget/risk envelopes | First verified revenue plus accepted governance evidence |
| A3 | Portfolio operation | Operational control plane may manage multiple missions and reallocate explicitly authorized envelopes | Recurring verified revenue >= 2 billing/realization cycles plus accepted portfolio controls |

Current level remains A0 until the Founder explicitly promotes it in the decision ledger.
```

This clarification does **not** itself promote A0.

### C2. `CONSTITUTION.md` — authority table

Keep Founder, runtime cognition, Chief Executive Architect DEV, DIE State Manager and Worker rows substantively intact. Replace the Hermes monopoly with these two roles:

```markdown
| **Mission Control** (deterministic operational control/enforcement plane, REPLACEABLE) | Menerima work/mission yang sudah memiliki authority basis; melakukan deterministic intake, eligibility, lease, routing, bounded retry/failover, review routing, dependency progression, runtime supervision, incident escalation, dan governed publication/writeback pada domain yang diizinkan | Tidak menciptakan Northstar/strategi/market truth; tidak mengalokasikan kapital; tidak memperluas authority; tidak mewarisi Architect DEV; tidak mengubah Constitution; tidak melakukan spend, credential mutation, external submission/publication atau irreversible action tanpa authority eksplisit; tidak menjadi Company Truth writer menggantikan DIE State Manager |
| **Hermes** (replaceable operational specialist / compatibility adapter) | Menjalankan cognition/edge workflow/notification/legacy operational capability yang secara eksplisit didelegasikan melalui control plane, jika masih dipertahankan berdasarkan evidence | Bukan sovereign, bukan canonical state writer, bukan unique mission owner, bukan second control plane; tidak memperoleh privilege DEV/financial/red-zone dari keberadaan historisnya |
```

### C3. `CONSTITUTION.md` — operational tie-breaker

Replace the old Hermes operational-primacy rule with:

```markdown
2. **Primasi operasional:** Mission Control adalah satu deterministic operational control/enforcement plane. Ia mengeksekusi policy dan lifecycle work yang sudah memiliki authority basis; ia tidak menggantikan semantic judgment yang secara konstitusional dimiliki Founder atau authorized cognition.
3. **State sovereignty:** DIE State Manager tetap memvalidasi dan menulis canonical company operational truth. Mission Control memiliki durable control-plane state (lease/attempt/dispatch/review/runtime) dan boleh melakukan governed engineering/task-graph Git publication hanya pada domain yang secara eksplisit diizinkan.
4. **Otoritas final:** Founder. Sengketa authority yang belum diputus Founder -> paused/no-op.
5. **Default aman:** ketidakjelasan authority = tidak bertindak.
```

### C4. `CONSTITUTION.md` — Architect DEV/runtime separation clarification

Add under authority boundaries:

```markdown
**Architect identity separation.** `chief-executive-architect-dev` adalah Founder-invoked privileged DEV plane dan bukan runtime principal. `chatgpt-architect` dapat menjadi replaceable runtime cognition principal untuk architecture/governance/incident analysis, tetapi tidak mewarisi unrestricted DEV authority. Proactive engineering execution hanya boleh melalui task-scoped delegated execution yang sudah diterima governance; interactive Founder invocation dapat memasuki DEV plane sesuai authority eksplisit.
```

## D. Exact proposed `COMPANY_BRAIN.md` changes

Replace invariant 5 with:

```markdown
5. **One operational control plane.** Mission Control owns deterministic operational lifecycle enforcement for authorized work. Runtime cognition proposes/decides within scope; workers and retained specialists do not create competing schedulers/control planes. DIE State Manager remains the canonical company operational-state writer.
```

Replace the organizational identity line for operational orchestration with:

```markdown
| Mission Control | Operations | Deterministic operational control/enforcement plane |
| Hermes Operator | Operations specialist | Replaceable legacy/edge specialist when explicitly delegated; not a second control plane |
```

Replace generic `Founder Decision -> Hermes Mission -> Worker / Proxima execution` operating-loop wording with:

```text
Founder / authorized canonical decision
-> State Manager commit where company operational truth is involved
-> Mission Control work lifecycle
-> bounded cognition / worker / provider / delegated executor
-> independent review where required
-> validated evidence + governed progression/writeback
```

## E. Exact proposed `PROTOCOLS/agency-contract-v0.md` changes

Replace runtime invariant 1 with:

```markdown
1. **One operational control plane:** `mission-control`. Runtime cognition may author proposals or bounded decisions; retained operational specialists and Workers do not orchestrate the company independently.
```

Keep runtime invariant 2:

```markdown
2. **One canonical writer:** `die-state-manager` for canonical company operational records.
```

Replace the old cross-role fixed flow with:

```text
semantic author / canonical source
-> authority validation
-> DIE State Manager commit when company operational truth is mutated
-> Mission Control lifecycle acceptance
-> lease / route / dispatch bounded owner or worker
-> result + evidence
-> independent review when required
-> Mission Control progression / governed publication
```

Replace Hermes authority class with:

```markdown
| Mission Control | Deterministic work lifecycle, lease/routing/failover/review/recovery enforcement inside ratified policy | Northstar, strategic/business judgment, capital allocation, constitutional change, unrestricted DEV, unapproved red-zone actions |
| Hermes | Explicitly delegated specialist/legacy operational work if retained | Company orchestration monopoly, canonical state sovereignty, undelegated worker control, privilege widening |
```

Add:

```markdown
`chatgpt-architect` runtime cognition never inherits `chief-executive-architect-dev`. Proactive privileged execution requires a task-scoped delegated-execution contract; otherwise it must escalate or remain cognition-only.
```

## F. Exact proposed `company/identity-registry.json` changes

Preserve:

```json
"canonical_state_writer": "die-state-manager"
```

After ratification change:

```json
"operational_control_plane": "mission-control"
```

Register a deterministic identity entry equivalent to:

```json
{
  "id": "mission-control",
  "kind": "deterministic_operational_control_plane",
  "scope": "authorized_company_work",
  "runtime": true,
  "template": false,
  "architect_dev_access": "deny",
  "inherits_identity_ids": [],
  "capabilities": [
    "canonical_work_intake",
    "eligibility_enforcement",
    "lease_management",
    "principal_routing",
    "bounded_failover",
    "review_routing",
    "dependency_progression",
    "runtime_supervision",
    "incident_escalation",
    "governed_task_graph_writeback"
  ]
}
```

Change Hermes registry semantics only after `OPS-002` determines its retained role. Control-plane promotion alone must remove unique orchestration authority from Hermes, but it must not fabricate a final KEEP/DEMOTE/RETIRE disposition before evidence.

If `chatgpt-architect` is registered as a runtime organizational identity, its entry must explicitly contain:

```json
"architect_dev_access": "deny"
```

and no inherited DEV capability. The existing `chief-executive-architect-dev` constitutional plane remains separate and Founder-invoked.

## G. Founder decision form

A future Founder ratification should be recorded with an explicit choice, for example:

```text
DECISION: RATIFY_COS002_MISSION_CONTROL_CONTROL_PLANE_V1

I ratify Mission Control as DIE's single deterministic operational control/enforcement plane under the COS-002 packet, preserving:
- Founder sovereignty;
- current autonomy level unless separately promoted;
- DIE State Manager company-state writer sovereignty;
- Chief Executive Architect DEV as Founder-invoked/non-runtime;
- no autonomous spend, external submission/publication, credential mutation, new-vendor, or irreversible authority beyond separately ratified envelopes;
- Hermes disposition as a separate evidence-based decision.

Authority becomes effective only after MC-008J FULLY_UNATTENDED_24X7_ACCEPTED, MC-009D accepted, writer-domain conformance passes, and COS-004 applies/validates the exact ratified canon changes.
```

The Founder may instead record:

```text
DECISION: DEFER_COS002_RATIFICATION
REASON: <Founder reason>
```

No silence, timeout or elapsed soak time counts as ratification.
