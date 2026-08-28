# DIE One-Canon Validator V1

Date: 2026-08-28
Task: DIE-104
Status: CANON
Executable: `company/scripts/validate_one_canon.py`
Contract: `company/contracts/die.one-canon-validator.v1.json`

## Purpose

DIE-104 turns the Chapter #4 one-canon rules into an executable fail-closed gate. The validator is stdlib-only and runs on both Windows and Linux. It validates repository topology and migration boundaries without reading credential values or touching live runtime state.

A validation failure returns exit code `2` and a structured JSON result. Any unexpected validator exception is also converted to `FAIL` rather than being treated as success.

## Canonical checks

The validator currently performs 11 checks:

1. Git root identity and optional clean-worktree gate.
2. Required canonical paths exist and the legacy Atlas path is absent.
3. Component registry contains exactly the nine Chapter #4 logical components and all in-repo source references exist.
4. Linux source/state/MUXIA/config/install roots match the DIE-102 contract and remain separated.
5. No tracked `company/` path contains forbidden runtime/cache/credential material.
6. Legacy tracked runtime state is pinned to an exact temporary allowlist; tracked `workspaces/` are forbidden.
7. Architect/OAUTH/Aether/task-ordering boundaries remain intact.
8. Human-centric Atlas has one operational canonical path.
9. Object Asset Engine source snapshot manifest exactly matches imported files and hashes.
10. Web-AI OAuth provider-neutral snapshot manifest exactly matches imported files and hashes.
11. High-confidence secret patterns are absent from tracked `company/` files.

## Temporary legacy-state exception

The repository still contains 15 tracked `state/` files inherited from the Windows-era source layout. DIE-104 does not pretend they have already been migrated.

Those exact paths are pinned in `die.one-canon-validator.v1.json`. The rule is:

- the allowlist may not expand;
- tracked `workspaces/` are not allowed;
- any new tracked `state/` file fails the validator;
- the exception is removed only after `CUT-002/CUT-003` final state sync and restore/replay proof.

This makes the migration debt explicit and bounded instead of silently accepting arbitrary runtime state in Git.

## Architect boundary

The validator enforces:

- `company/architect` status remains `DEFERRED_SOURCE_IMPORT`;
- source reference remains external `D:\mcp-architect`;
- `MX-053` depends on `CUT-005`;
- `CUT-006` remains the Founder control-channel handoff after `MX-054`.

This prevents a future refactor from accidentally migrating the Architect MCP early and losing the Windows control channel.

## Division01 and OAUTH boundary

The validator enforces principal ID `division-head-division01` and requires the component registry/task graph to state that `D:\OAUTH` is not Division01. The OAUTH snapshot source Git head is also pinned.

## Aether boundary

Aether remains `KEEP_EXTERNAL`. The validator checks both the task-graph migration overlay and the disposition matrix so Chapter #4 cannot absorb Aether silently.

## Snapshot integrity

Each imported external snapshot must satisfy all of the following:

- safe relative manifest paths only;
- no `..` traversal or absolute snapshot path;
- no duplicate manifest entry;
- every listed file exists;
- every imported file hash matches its manifest;
- no extra unmanifested file exists in the snapshot;
- Object Engine remains explicitly `linux_runnable=false` until DIE-203;
- OAUTH source Git HEAD remains pinned.

## Forbidden tracked material

Under `company/`, the following path components are rejected when tracked:

`.git`, `node_modules`, `credentials`, `__pycache__`, `.pytest_cache`, `.test-userdata`, `data`, `db`, `outputs`.

Tracked `.pyc` files are also rejected.

The validator also scans tracked `company/` text for high-confidence private-key/API-token patterns. This is a narrow secret tripwire, not a substitute for later dedicated secret scanning.

## DIE-104-R1 finding

The first real validator execution correctly detected stale Hermes component-registry references to `bin/die_operator_tick.py` and `bin/die_operator_switch.py`. Those files are not present in clean GitHub main; they were only observed as live/dirty Windows candidates earlier.

The registry was corrected to reference only canonical Hermes identity + shared bridge source. The note now explicitly states that live-only proactive-operator candidates must be reconciled during DIE-202 rather than treated as already canonical.

## Negative proof

The test suite creates isolated temporary Git fixtures and proves fail-closed behavior for:

- a tracked `company/**/credentials/token.json`;
- a new tracked `state/NEW.jsonl` outside the legacy allowlist;
- Architect migration-order drift (`MX-053` dependency changed);
- snapshot content tampering.

The current repository and a clean synthetic fixture must both pass.

## CLI

```text
python company/scripts/validate_one_canon.py --root <DIE_ROOT>
python company/scripts/validate_one_canon.py --root <DIE_ROOT> --require-clean
```

Optional `--output <path>` writes the structured JSON result as evidence.

## Gate consequence

`DIE-200`, `DIE-201`, `DIE-202`, and `DIE-203` may proceed only after DIE-104 is green. Later migration tasks should rerun this validator after source/canon changes so one-canon drift fails before reliability/cutover work.
