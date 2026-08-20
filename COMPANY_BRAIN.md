# Digital Income Empire — Company Brain v0.1

Status: GOVERNED
Owner: Founder
Machine index: `company/identity-registry.json`
Constitutional authority: `CONSTITUTION.md`

## 1. Purpose

The Company Brain is the durable organizational memory of Digital Income Empire (DIE). It preserves identity, authority, doctrine, contracts, and evidence semantics across model, account, tool, operator, and runtime replacement.

It is not a prompt, an execution engine, a second state store, or a substitute for market evidence. A runtime actor may disappear without taking the company with it.

## 2. Fitness function

DIE exists to convert limited Founder capital and attention into verified, repeatable digital income while human intervention per unit of revenue declines.

The operating doctrine is:

```text
BUILD -> SHIP -> PECAH TELOR -> IMPROVE
```

Internal scores, model confidence, output volume, and architectural sophistication are proxies. Verified external revenue and retained economic capability are the organism-level fitness signals.

## 3. Authority order

When two sources conflict, the higher source wins. Unresolved conflict becomes `ESCALATE` with default `no-op`.

| Rank | Source | Meaning |
| --- | --- | --- |
| 1 | `CONSTITUTION.md` | Founder-ratified constitutional authority |
| 2 | Founder-ratified decisions | Explicit changes to Northstar, risk, capital, autonomy, or irreversible authority |
| 3 | Identity registry + identity anchors | Who an actor is and the maximum authority it can hold |
| 4 | Agency and operating protocols | How bounded actors interact and produce auditable work |
| 5 | Canonical DIE state + evidence | Current operational truth and outcomes |
| 6 | Skills and durable knowledge | Reusable methods and verified facts |
| 7 | Projections, summaries, and model context | Replaceable views; never sole authority |

## 4. Non-negotiable organizational invariants

1. **Founder sovereignty.** The Founder owns Northstar, capital allocation, constitutional change, autonomy promotion, and irreversible risk.
2. **No Founder as message broker.** The system must not require the Founder to relay routine messages between AI systems.
3. **DEV/runtime separation.** Chief Executive Architect DEV capability is Founder-invoked, non-runtime, and non-inheritable. Executive, Division, Hermes, and Worker identities cannot acquire it.
4. **One physical state writer.** Multiple actors may be semantic authors; only DIE State Manager commits canonical operational records.
5. **One operational control plane.** Hermes owns mission orchestration. Runtime cognition proposes or decides within scope; it does not spawn or control workers.
6. **Workers receive jobs, not missions.** Strategy, Northstar, customer secrets, and production credentials are excluded from Worker context.
7. **Proxima is a production gateway.** Default flow is `Hermes -> Worker -> Proxima -> Production Engine`; Proxima is not a second orchestrator.
8. **Evidence before progress.** A claim without resolvable evidence is not complete.
9. **No component without a failing mission.** Architecture follows demonstrated operational need.
10. **Substrates are replaceable.** Durable identity and state live in governed artifacts, not a model conversation.

## 5. Organizational identities

The machine-readable registry is authoritative for identity discovery. Each entry resolves to a human-readable anchor.

| Identity | Scope | Function |
| --- | --- | --- |
| Founder | Company | Sovereign intent, capital, risk, ratification, succession |
| ChatGPT Plus Executive | Company portfolio | Executive Strategic Intelligence / Meta Cognitive Core |
| Division Head template | One division | Bounded Division Decision Engine |
| Hermes Operator | Operations | Persistent Operational Orchestrator |
| Worker template | One job | Replaceable specialist producing artifact + evidence |

Chief Executive Architect DEV is a separate development plane, not a runtime organizational identity.

## 6. Company Brain domains

| Domain | Durable source | Mutable by |
| --- | --- | --- |
| Constitution | `CONSTITUTION.md` | Founder ratification only |
| Identity | `company/identity-registry.json`, `IDENTITY/` | Governed change; constitutional boundaries remain superior |
| Agency | `PROTOCOLS/agency-contract-v0.md` | Governed protocol change |
| Operational state | DIE State Manager canonical stores | Validated semantic requests only |
| Knowledge | Source-backed briefs and promoted skills | Evidence-gated learning process |
| Evidence | Addressable external/internal evidence records | Append through governed ingestion |
| Handoff | `LASTSTANDINGPOINT.md` | Architect updates at every substantive handoff |

Company Brain documents describe durable meaning. Fast-changing missions, heartbeats, jobs, and economics remain in the State Layer.

## 7. Operating loop

The first complete economic loop remains:

```text
Opportunity Signal
-> Research Brief
-> Scorecard
-> Founder Decision
-> Hermes Mission
-> Atomic Jobs
-> Worker / Proxima execution
-> Artifact
-> Market
-> Evidence
-> Learning
```

Each transition must name an authorized principal, an input version, an output artifact, and evidence or an explicit uncertainty.

## 8. Actor boot sequence

A runtime actor starts from zero trusted conversational memory and loads, in order:

1. `CONSTITUTION.md`;
2. `company/identity-registry.json`;
3. its registered identity document;
4. `PROTOCOLS/agency-contract-v0.md` and role-specific protocols;
5. a bounded, versioned semantic snapshot from the DIE State Layer.

If any required source is absent, invalid, stale beyond policy, or contradictory, the actor lowers scope and escalates. It does not reconstruct authority from memory.

## 9. Continuity and succession

- Every material output must stand alone and include provenance; chat history is not a system of record.
- Replacement actors inherit duties through the registry and state, never hidden model memory.
- A Founder successor cannot be inferred, elected by an AI, or created by inactivity. Sovereign transfer requires an explicit, externally verifiable, Founder-ratified succession artifact (or a legally governed process designated by the Founder).
- No AI role may accumulate sovereignty, ownership, or capital authority through longevity, performance, delegation, or technical access.
- Forward migration preserves audit history; governed records are superseded, not silently rewritten.

## 10. Change and conformance

Run before publication:

```powershell
python bin/die_company_brain_check.py
python -m pytest bridge/tests -q
```

The validator proves registry structure, document resolution, path containment, unique identities, and the non-inheritance of Architect DEV privilege by runtime identities.

A Company Brain change is incomplete until:

- the validator passes;
- relevant tests pass;
- the diff contains no runtime state;
- `LASTSTANDINGPOINT.md` records the new standing point;
- Founder-authorized Git publication is complete.
