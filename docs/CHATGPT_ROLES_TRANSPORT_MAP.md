# ChatGPT Roles & Transport Map v1

Status: GOVERNED runtime cheat-sheet
Owner: Founder
Purpose: bind identity, transport, and authority without treating transport as identity or state.

## Registry

| Identity | Scope | Runtime? | Transport lane | Port(s) | Decision MCP | May | May NOT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `founder` | `company` | No; human sovereign | — | — | — | exercise all sovereign authority | be inferred, replaced, or used as routine message transport |
| `chatgpt-plus-executive` | `company_portfolio` | Yes | BrowserOS neo wake + bounded semantic snapshot | wake `127.0.0.1:9010`; browser CDP `:9110` | `127.0.0.1:8791` (18 tools) | observe, propose, challenge, escalate | shell, Git, state writes, market submission |
| `division-head-division01` | `single_division:DIVISION-01` | Yes | Brave principal-dedicated user-data-dir CDP wake | CDP `127.0.0.1:9333` | `127.0.0.1:8792` (6 tools) | division research, score, propose | other divisions, portfolio, capital |
| `chatgpt-creator` | `single_job_workspace` | Yes | Proxima V2 production gateway | REST `127.0.0.1:3211`; IPC `:19223` | **ZERO Decision MCP tools** | artifact production only | research, decisions, orchestration, state |
| `chief-executive-architect-dev` | development plane | **NO — Founder-invoked only** | repository, Git, tests | — | Architect DEV MCP `:8787`; runtime forbidden | build and repair the governed system | runtime missions or privilege inheritance |
| `hermes-operator` | `committed_missions` | Yes; control plane, not ChatGPT | Telegram, cron, gateway | — | semantic state requests via State Manager | orchestrate, delegate, report | make products, exceed budget, create a second control plane |
| `worker-template` | `single_job_workspace` | Yes; job-bound | CLI such as OpenCode | — | none | execute one job; return artifact + evidence | missions, strategy, credentials, worker spawning |

`division-head-template` is the registry template for bounded Division Heads; it does not create another active principal, division, or transport lane. Its concrete active instance here is `division-head-division01`.

## Invariants

- Proxima :3211 is a production gateway. It is NEVER a cognitive lane.
- Wake actuators (`:9010`, `:9333`) are outbound briefing transports, never canonical state mutation.
- Executive BrowserOS uses principal-dedicated browser CDP `:9110` behind the `:9010` wake service boundary; these are not Decision MCP ports.
- Decision MCPs (`:8791`, `:8792`) are principal-pinned; `:8787` is Architect DEV and forbidden to all runtime identities.
- Reserved/infrastructure ports: `8787` (Architect DEV), `8789` (OAuth edge), `8790` (Architect gateway) — fail-closed.
- Canonical mutation is performed only by DIE State Manager after authority validation; chat, wake, browser, and MCP responses are not Company Truth by themselves.

## Read rule

Before answering a topology, role, transport, or authority question, resolve the identity in `company/identity-registry.json`, then use this map and the registered identity anchor. On conflict, apply `COMPANY_BRAIN.md` authority order and escalate with default `no-op`.

Sources: `company/identity-registry.json`; `IDENTITY/*.md`; `PROTOCOLS/agency-contract-v0.md`; `COMPANY_BRAIN.md`; `docs/architecture/WAKE_AUTH_SESSION_SECURITY_V1.md`; `docs/operations/RUNTIME_MCP_ACTIVATION_V1.md`.
