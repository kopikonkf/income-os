CONSTITUTION_STATE_BOUNDARY_PATCH.md

Target repository: kopikonkf/income-os
Patch class: CONSTITUTIONAL — Founder ratification required
Date: 2026-08-20
Scope: ownership boundary only; no new infrastructure framework.

Patch objective

Promote the existing single-writer pattern (bin/die_event.py) into the constitutional DIE State Manager boundary.

No new message bus.
No database migration.
No Kafka.
No new dashboard.

This is an authority correction around code that largely already exists.

PATCH A — Add deterministic State Manager role

Insert into CONSTITUTION.md authority model:

DIE State Manager is a deterministic/provider-neutral state authority, not an AI strategic actor. It is the sole physical writer of canonical DIE operational stores. It validates semantic events/transitions, appends provenance, materializes current-state projections, and rejects mutations that violate schema or authority. It does not invent strategy, open missions, allocate capital, or command workers.

Authority:

CAN:
validate event/decision/evidence envelopes
append canonical records
assign sequence/version
materialize current state
reject unauthorized/invalid transition
serve bounded state projections

CANNOT:
reason strategically
originate business decisions
command Hermes/workers
spend money
change Constitution
infer revenue without evidence

PATCH B — Replace "one writer per state" semantics

Replace the old model:

One writer per state. Hermes writes event log / decision ledger / mission state / economics.

With:

One physical writer, multiple semantic authors.

DIE State Manager is the sole physical writer of canonical operational state. Founder, Executive/Division cognition, Hermes, workers, schedulers and external evidence ingestors may be semantic authors only within their authority. They submit typed events, evidence, decisions or transition proposals. State Manager validates and commits them.

This is the new one-control-plane invariant for persistence.

PATCH C — Revised ownership matrix

STATE / ARTIFACT               SEMANTIC AUTHORITY          PHYSICAL WRITER
────────────────────────────────────────────────────────────────────────────
Constitution / Northstar       Founder                     repo/state service
Identity constitutional docs  Founder                     repo
Event store                    actor that observed event   DIE State Manager
Evidence store                 worker/Hermes/external      DIE State Manager
Decision store                 authorized decider          DIE State Manager
Mission definition             Hermes within policy        DIE State Manager
Mission/Kanban status          Hermes                      DIE State Manager
Current-state projection       derived                     DIE State Manager
Economics                      verified source/ingestor     DIE State Manager
Incident store                 detecting actor             DIE State Manager
Company memory                 governed ingestion          DIE State Manager
Worker job input               Hermes                      job workspace/service
Worker result                  Worker                      job workspace → ingest
Thesis / proposal              Executive/Division cognition DIE State Manager
Credentials                    Founder / vault             never canonical model state

Kanban remains Hermes' operational interface, but it is a projection/materialization of canonical event/state records.

PATCH D — Hermes boundary

Replace any clause equivalent to:

Hermes owns/writes canonical Company Truth.

With:

Hermes is the mission owner and operational orchestrator. Hermes is authorized to originate operational events, mission transitions and bounded decisions according to autonomy policy. Hermes submits those mutations to DIE State Manager and receives committed IDs/versions. Hermes must not bypass the State Manager to mutate canonical stores.

Hermes retains:

mission decomposition

job delegation

worker monitoring

retries/recovery

operational scheduling

policy-compliant mission transitions

decision-request generation

evidence ingestion requests

Hermes loses:

persistence sovereignty

arbitrary direct mutation of canonical state

assumption that Hermes memory/database is company truth

PATCH E — Cognitive boundary

Runtime cognitive entities:

ChatGPT Plus Executive Strategic Intelligence
ChatGPT Free Division Decision Engines

They:

observe through semantic snapshots;

author thesis/proposals/authorized decisions;

never write storage directly;

submit through Decision/State services.

The Chief Executive Architect DEV role is explicitly outside this runtime boundary.

Architect DEV:

may inspect/edit/test code;

may operate git;

may invoke bounded diagnostic/service tools;

is Founder-invoked;

is not an autonomous company actor;

its infrastructure privilege MUST NOT be inherited by Executive/Division identities.

PATCH F — Existing state writer migration

bin/die_event.py is reinterpreted immediately as:

DIE State Writer v0

rather than:

Hermes' event writer

No rename is required in the first patch.

Immediate invariants:

all new canonical event/decision/economic writes
        ↓
bin/die_event.py (or its future service wrapper)
        ↓
validate
        ↓
append
        ↓
return stable id

Hermes, cron, future gateways and ingestion scripts call this boundary.

Future code hardening (after repository write access is restored):

add schema_version;

add actor_id / actor_role;

correlation_id / causation_id;

evidence_refs;

tests proving unauthorized roles cannot commit forbidden decision classes.

PATCH G — A2A/Decision protocol language

Replace:

state milik Hermes

with:

canonical DIE State Layer

Replace:

diproyeksikan oleh Hermes sebagai satu-satunya truth

with:

compiled from canonical DIE state plus typed operational evidence emitted by Hermes/runtime sources

Retain:

bounded semantic surface;

no raw DB exposure for runtime cognition;

event classification;

evidence/completeness metadata;

cognitive vs production lane separation.

Add later, not in this patch:

Decision Request

Decision Gateway

context.snapshot()

Those are extensions after this boundary patch is committed and tested.

Acceptance criteria

This constitutional migration is complete when:

AC-1 No authoritative doc says Hermes is physical owner/writer of Company Truth.
AC-2 Hermes remains clearly mission owner / operational orchestrator.
AC-3 DIE State Manager is deterministic, provider-neutral and sole canonical physical writer.
AC-4 Runtime ChatGPT identities remain least-privilege.
AC-5 Architect DEV authority is separated from runtime cognitive authority.
AC-6 Existing bridge/tests still pass without introducing a new infrastructure dependency.
AC-7 Historical JSONL state is preserved unchanged.

Kill criterion:

If enforcing this boundary requires replacing the existing append-only state implementation or breaking current 20-test bridge conformance, stop and reduce the patch. The objective is authority correction, not a state-platform rewrite.