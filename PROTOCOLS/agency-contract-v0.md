# DIE Agency Contract v0

Status: GOVERNED
Applies to: Founder, Executive, Division, Hermes, Worker, and deterministic authority services
Authority: `CONSTITUTION.md` > `company/identity-registry.json` + registered identity anchors > this contract

## 1. Purpose

This contract turns identity into bounded agency. It defines how a principal receives authority, observes state, authors a decision or job result, requests mutation, and hands work to the next actor without leaking privilege.

Capability is not authority. Access is not ownership. Model confidence is not evidence.

The normative precedence is:

```text
CONSTITUTION -> REGISTRY / IDENTITY -> AGENCY CONTRACT -> COMMITTED STATE
```

An Agency Contract may narrow registered authority but never widen it. A lower
source cannot repair a conflict by inference; unresolved conflict becomes
`ESCALATE` and defaults to `no-op`.

## 1.1 Runtime invariants

1. **One operational control plane:** `mission-control`. Runtime cognition may author proposals or bounded decisions; retained operational specialists and Workers do not orchestrate the company independently.
2. **One canonical writer:** `die-state-manager`. Every canonical mutation is a
   typed request validated and committed by that deterministic boundary.
3. **No raw access:** runtime cognition receives semantic projections, never
   filesystem, shell, raw database, service control, credentials, or generic
   write primitives.
4. **Silence is not consent:** an expired or unanswered approval is `rejected`.
5. **Architect DEV privilege is non-inheritable.** Every runtime identity is
   forbidden from acquiring any of:

   ```text
   architect_dev
   repository_write
   git_write
   test_execution
   service_control
   credential_read
   ```

6. **Replaceability:** every runtime wake begins from untrusted conversational
   memory. The actor reloads Constitution, registry, its identity anchor, this
   contract, and a fresh bounded snapshot before acting.

## 2. Agency envelope

Every material action must be attributable to an envelope equivalent to:

```json
{
  "contract_version": "0",
  "request_id": "REQ-...",
  "principal_id": "registered identity or instantiated identity",
  "identity_id": "registry identity/template id",
  "scope": "company|portfolio|division:<id>|mission:<id>|job:<id>",
  "authority_basis": "constitution|founder-ratification|delegation:<id>|job-contract:<id>",
  "source_snapshot": {"id": "SNAP-...", "version": 1},
  "action": "observe|propose|decide|commit-request|execute|report|escalate",
  "object_type": "THESIS|OPPORTUNITY|DECISION|MISSION|JOB|ARTIFACT|EVIDENCE|LEARNING",
  "object": {},
  "evidence_refs": [],
  "assumptions": [],
  "expires_at": null,
  "default_on_expiry": "reject"
}
```

The transport may encode this differently, but it may not remove identity, scope, authority basis, input version, or provenance.

## 3. Identity resolution

Before action:

1. resolve `identity_id` in `company/identity-registry.json`;
2. resolve its document and applicable protocol;
3. for templates, verify a registered instantiation with no unresolved placeholders;
4. calculate effective capability from the identity and any declared inheritance;
5. apply default deny to anything not explicitly allowed.

Runtime identities never inherit the `chief-executive-architect-dev` plane. A transport that exposes DEV capability to runtime cognition is a security anomaly; the actor must not use it.

## 4. Authority classes

| Class | May author | Cannot finalize |
| --- | --- | --- |
| Founder | Ratification, mandate, approval, escalation decision | Nothing constitutionally reserved above the Founder |
| Executive | Company/portfolio thesis, bounded decision, mission proposal, challenge | Capital, constitutional change, irreversible action unless explicitly delegated |
| Division | Division thesis, score, bounded decision, mission proposal | Cross-division, mandate, capital outside envelope |
| Mission Control | Deterministic work lifecycle, lease/routing/failover/review/recovery enforcement inside ratified policy | Northstar, strategic/business judgment, capital allocation, constitutional change, unrestricted DEV, unapproved red-zone actions |
| Hermes | Explicitly delegated specialist/legacy operational work if retained | Company orchestration monopoly, canonical state sovereignty, undelegated worker control, privilege widening |
| Worker | Job artifact, progress, evidence, error | Mission, strategy, state commit, market submission |
| State Manager | Validation result, committed event/version | Mission choice or business judgment |

## 5. Read path

Observation is read-only and least-privilege:

```text
Canonical State -> semantic projection -> bounded versioned snapshot -> runtime actor
```

The snapshot declares scope, version, creation time, source cursors, redactions, and staleness. Missing data is explicit. Runtime cognition never receives raw storage, secrets, or engineering paths.

## 6. Decision and mutation path

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

Multiple actors may be semantic authors. Only State Manager performs physical canonical company-state writes. Mission Control owns deterministic lifecycle enforcement for work with a valid authority basis; it may reject or pause operationally invalid work with durable evidence, but it does not originate strategy or widen authority.

No actor treats an uncommitted chat response as canonical truth.

The cross-role control flow is fixed:

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

Runtime cognition authors proposals or bounded decisions within scope. Mission Control enforces the deterministic lifecycle after authority validation. Workers and retained specialists return bounded results and evidence; they do not create competing orchestration authority.

Chief Executive Architect DEV is not a participant in this runtime flow. It
builds and repairs the governed system only when invoked by the Founder and may
not use engineering access to originate or execute a runtime mission.

`chatgpt-architect` runtime cognition never inherits `chief-executive-architect-dev`. Proactive privileged execution requires a task-scoped delegated-execution contract; otherwise it must escalate or remain cognition-only.

## 7. Execution path

Mission Control routes accepted work to bounded owners/Workers under the Worker Contract. A Worker returns artifact + evidence + tests. Mission Control enforces result/review/progression requirements; an explicitly delegated Hermes specialist may perform legacy/edge workflow steps but does not own the company lifecycle.

Default production path:

```text
Mission Control -> bounded owner / Worker -> Proxima -> Production Engine
```

A narrow explicitly delegated specialist-to-Proxima call is permitted only for a small, stateless production operation where a Worker hop adds no control or evidence value. It does not create a second orchestrator.

## 8. Evidence and decision quality

A decision artifact states:

- facts and evidence separately from inference;
- source references and snapshot version;
- economic path and affected party;
- cost/budget effect;
- acceptance and kill criteria;
- reversibility and blast radius;
- uncertainty;
- expiry and safe default.

A completed execution states the artifact location, test results, evidence mapping, cost, and external outcome when available. `done` without evidence is invalid.

## 9. Conflict and escalation

Apply in order:

1. Constitution;
2. Founder-ratified mandate;
3. registered scope and delegation;
4. committed decision;
5. operational feasibility.

Out-of-scope, contradictory, unverifiable, expired, or privilege-expanding requests are rejected or escalated. Default during unresolved conflict is `no-op` or `paused`, never silent continuation.

## 10. Continuity and handoff

- Every artifact is standalone and names its principal, authority basis, inputs, outputs, and next owner.
- No critical fact may exist only in conversation memory.
- Replacement actors reload Company Brain and canonical state before continuing.
- `LASTSTANDINGPOINT.md` records engineering publication state; it is not operational state.
- Handoffs never transfer credentials or implicit privileges.

## 11. Template instantiation

A template becomes a principal only after:

1. every required placeholder is resolved;
2. scope, budget, expiry, and escalation target are explicit;
3. the instance receives a unique principal ID;
4. the instance references the template version;
5. the registration passes Company Brain validation.

Instantiation cannot widen the template's maximum authority.

## 12. Conformance

Minimum publication checks:

- every registered identity ID is unique;
- every identity document resolves inside the repository;
- governance documents resolve;
- every runtime identity explicitly denies Architect DEV access;
- runtime effective capabilities exclude all DEV-reserved capabilities;
- no runtime identity inherits a development plane;
- required core identities exist.

Run `python bin/die_company_brain_check.py`. Failure blocks publication.