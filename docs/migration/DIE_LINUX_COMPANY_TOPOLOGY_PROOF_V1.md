# DIE-204 — Linux Company Topology Proof V1

Date: 2026-08-30
Status: PASS
Task: `DIE-204`

## Purpose

Prove the Chapter #4 logical company topology on Linux without performing production generation, market submission, publication, spend, or Architect control-channel cutover.

The accepted topology chain is:

```text
Atlas data/canon
  -> Division01 cognition node (live/routable, no semantic invocation required for topology canary)
  -> Hermes orchestrator
  -> Worker-001 OpenCode bounded executor
  -> MUXIA Job Registry / Artifact Registry
  -> verified synthetic artifact
```

## Live Linux proof

Atlas lineage:

- Human-Centric Atlas canonical SHA256 `3e011079b4da3770ee10fd8a7c419bafe4c111e0ff5349890e397bd6e7ffd483`.
- Object Atlas canonical runtime `seed_library.db` SHA256 `3035b179ba435a9cc4983ca567528b15941b1a9f205451d425cd40ce5925ab77` with 475,560 validated object primitives.

Principal/runtime nodes:

- Executive `chatgpt-plus-executive`: Linux Runtime Decision MCP health PASS, 18 tools.
- Division01 `division-head-division01`: Linux Runtime Decision MCP health PASS, 6 tools.
- Hermes `hermes-operator`: Linux gateway enabled/active; Founder-originated Telegram user input -> assistant response E2E PASS.
- Worker-001: OpenCode CLI 1.18.23, bounded runner result `done`.

MUXIA boundary:

- real mutable root: `/var/lib/muxia`;
- job: `DIE204-topology-muxia`;
- required capability: `image.generate`;
- final state: `SUCCEEDED`;
- provider call: not performed;
- network in Worker stage: none;
- synthetic fixed PNG artifact only.

Artifact Registry proof:

- path: `/var/lib/muxia/artifacts/DIE204-topology-muxia/synthetic-fixture.png`;
- SHA256: `431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460`;
- bytes: 68;
- MIME: `image/png`;
- artifact exists, receipt exists, hash matches, byte count matches and MIME matches: all PASS.

## Company topology interpretation

The required logical ownership roots exist under `/srv/die/company`: Architect, Executive, Atlas, MUXIA, Division, DIE agents, Workers, and next-subprojects. Human/Object Atlas subroots exist.

Only `division001` is materially instantiated today. The `division002` ... `division100` target is a northbound namespace/capacity shape, not authorization to create 99 empty active source trees. This is consistent with DIE-103's one-canon rule: materialize real ownership/components without duplicate or dummy active source trees. Future divisions are created when their own identity/source/runtime contracts are ratified.

`company/architect` remains logical ownership only. Windows Architect MCP remains the control/bootstrap channel through CUT-005; DIE-204 does not alter MX-053/MX-054/CUT-006 ordering.

## Aether boundary

The active DIE-204 lineage artifacts plus component registry contain zero Aether text references and the Linux company tree contains zero symlinks into protected Aether/state-shared estates. No Aether dependency was absorbed.

## Authority boundary

This canary is synthetic and zero-spend. It grants no production authority and performs no production provider call, submission, publication or irreversible external action.

Receipt: `company/muxia/receipts/DIE-204-linux-company-topology.receipt.json`.
Validator: `company/scripts/validate_die204_topology_receipt.py`.