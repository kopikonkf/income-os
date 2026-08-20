CODEBASE_AUTOPSY_KEEP_MODIFY_RETIRE.md

Project: Digital Income Empire / kopikonkf/income-os
Date: 2026-08-20
Status: Architecture autopsy completed against current main
Purpose: Salvage the working Opus-era implementation without preserving obsolete ownership assumptions.

Executive finding

The repository is not a disposable prototype. It already contains a usable v0 substrate:

append-only event/decision/economics state

a single state writer (bin/die_event.py)

read-only semantic projection / MCP surface

schema guards and redaction

worker contract + conformance fixtures

deterministic cron/conformance tooling

Founder/Hermes/cognitive identity doctrine

The primary defect is not implementation quality. It is ownership topology drift:

OLD:
Hermes = orchestrator + canonical operational-state owner

NEW:
Hermes = orchestrator / mission owner
DIE State Manager = provider-neutral canonical state authority

Therefore: salvage code, migrate authority.

KEEP

bin/die_event.py

KEEP as the seed of DIE State Manager.

Why:

already declares itself the single physical writer for EVENTS / DECISIONS / ECONOMICS;

append-only;

serializes writes;

actor/source is passed as data rather than hard-coded;

therefore it is already closer to a provider-neutral state service than the Constitution implies.

Change later: provenance/schema-version fields and service/API wrapper. Do not rewrite the append-only core.

state/EVENTS.jsonl, state/DECISIONS.jsonl, state/ECONOMICS.jsonl

KEEP as MVP stores.

Do not introduce Kafka/CQRS/event-bus infrastructure until scale proves JSONL insufficient.

Historical records remain immutable.

bridge/income_os_bridge/

KEEP the architecture of:

envelope

access logging

redaction

schema guard

bounded semantic tools

rate limiting

projection

read-only MCP surface

The existing bridge is an operational cognitive interface, not an Architect engineering bridge.

Worker Contract v0

KEEP:

worker gets JOB, not MISSION;

one workspace per job;

evidence required;

resumability/idempotency;

least privilege;

no worker-spawn;

mechanical acceptance criteria.

Conformance fixtures / tests

KEEP.

They are real replaceability machinery, not documentation theater.

bin/die_accept.py, bin/die-conformance.ps1

KEEP as deterministic validation gates.

Core constitutional doctrine

KEEP:

Founder sovereignty

BUILD → SHIP → PECAH TELOR → IMPROVE

evidence over claim

replaceable substrates

one operational control plane

no over-engineering

revenue as organism fitness signal

irreversible actions require Founder authority

Hermes mission-owner doctrine

KEEP:

Hermes owns mission execution;

decomposition/delegation/monitoring/retry;

workers own bounded jobs;

native delegated agents are ephemeral;

durable worker work must survive restart.

MODIFY

CONSTITUTION.md

MODIFY state ownership.

Replace:
Hermes physically owns/writes event log, decision ledger, mission state, economics

With:
DIE State Manager is the sole physical canonical writer.
Actors are semantic authors and submit validated transitions/events.

Hermes remains semantic owner of mission orchestration, not storage authority.

IDENTITY/chatgpt-architect.md

MODIFY / SPLIT.

It currently conflates two roles that are now distinct:

Operational Executive Strategic Intelligence

bounded

no raw filesystem/shell

consumes semantic state

participates in Decision Fabric

Chief Executive Architect / Builder

Founder-invoked development authority

may inspect/edit/test the DIE codebase and controlled VPS services

does NOT participate as an autonomous runtime actor

admin engineering access belongs only to the DEV PLANE

The old no-raw-access rule stays valid for role #1, not role #2.

IDENTITY/hermes-operator/SOUL.md

MODIFY wording:

"state milik saya/Hermes" -> "DIE canonical state";

Hermes emits semantic events/transitions through State Manager;

Hermes does not directly become database authority.

KEEP Hermes as one operational control plane.

AGENTS.md

MODIFY all state-writing rules:

no direct conceptual ownership of JSONL by Hermes;

Hermes calls/submits to State Manager;

State Manager validates + appends;

economics/revenue facts require evidence refs;

Kanban stays operational projection/mission interface.

PROTOCOLS/a2a-combus-chatgpt-hermes.md

MODIFY heavily.

OLD topology:
one ChatGPT #A ↔ BrowserOS neo ↔ Hermes
plus production lane.

NEW topology:
Plus Executive + scoped Division Decision Engines ↔ DIE State/Decision Fabric ↔ Hermes

Keep the cognitive-vs-production lane separation, but:

demote BrowserOS neo from canonical architecture to optional transport;

make DIE State Layer the shared truth;

add Decision Request / Decision Gateway;

preserve Proxima as production fabric.

bridge/income_os_bridge/hermes_state_reader.py

MODIFY toward provider-neutral source abstraction.

Near-term:

keep file for backward compatibility;

introduce state source adapter contract;

Hermes DB becomes one operational evidence source, not canonical company truth.

Future rename only after tests prove compatibility.

bridge/income_os_bridge/projection.py

MODIFY:

compile from DIE state + operational Hermes evidence;

do not imply projection truth originates solely from Hermes DB.

bridge/income_os_bridge/briefing.py

MODIFY into / alongside semantic context.snapshot() compiler.

Purpose-aware views:

executive_review

division_decision

execution

investigation

Existing JSONL schemas

MODIFY forward-only:
add on new records:

schema_version

actor_id

actor_role

event_id

correlation_id

causation_id

evidence_refs

state_version when a materialized-state transition occurs

Do NOT rewrite historical lines.

bin/die_cron.py

MODIFY only where it assumes Hermes is canonical state owner.
Scheduler remains deterministic infrastructure.

RETIRE / ARCHIVE AS ACTIVE AUTHORITY

RETIRE as canonical assumptions, not necessarily delete the files.

Sole ChatGPT #A Free architecture

Retire.
Replace with:

ChatGPT Plus Executive Strategic Intelligence

reusable Division Decision Engine template

Chief Executive Architect DEV role outside runtime authority

Hermes-owned Company Truth

Retire permanently.

Hermes may be mission owner and operational control plane.
It must not be the persistence sovereignty of the Company Brain.

BrowserOS neo as mandatory cognitive transport

Retire as canonical requirement.
May remain as optional/fallback experimental transport.

Old P1/P2 briefing/report documents

Archive as engineering history:

bridge/P1_BRIEFING.md

bridge/P1_REPORT.md

bridge/P2_RESEARCH.md

bridge/NEXT_BRIEFING.md

QA / schema research notes

They are evidence of what was built, not current architecture authority.

Phase-gating that blocks shipping merely because time/test-days have not elapsed

Retire as doctrine.
Keep conformance tests, but gates must correspond to a real risk or failing mission.

Resulting canonical boundary

                     FOUNDER
                        │
          ┌─────────────┴──────────────┐
          │                            │
          ▼                            ▼
 CHIEF EXECUTIVE ARCHITECT       RUNTIME COGNITION
 DEV / BUILD PLANE               Plus / Division Heads
 admin engineering access              │
          │                             │
          │                     Decision Fabric
          │                             │
          ▼                             ▼
 CODE / TEST / GIT              DIE STATE MANAGER
                                      │
                          Event / Evidence / Decision
                                      │
                                      ▼
                                   HERMES
                            Operational Orchestrator
                                      │
                                      ▼
                                    WORKER
                                      │
                                  [PROXIMA]
                                      │
                                      ▼
                                   ARTIFACT

Architect DEV permissions do not leak into the autonomous Executive/Division runtime identities.

This separation resolves the apparent contradiction:

Runtime cognition must be least-privilege.

The human-invoked Architect needs engineering authority to build and repair the OS.