# DIE Shared Agent Runtime Pool v1

Status: CANONICAL OPERATING DECISION
Date: 2026-09-18
Authority: subordinate to the DIE Constitution, ORG-001 shared-resource model, H03 architecture, Mission Control authority boundaries, and each Holding's local execution contract.

## Decision

DIE command-line agents are pooled execution capability, not a control plane and not a mandatory resident stack per Holding.

```text
Founder / constitutional authority
        |
Mission Control
(task truth, lease, routing, review, recovery)
        |
        +---------------- Shared DIE Agent Pool ----------------+
        |                                                       |
 OpenCode / Codex / Claude Code / Pi / OMP / JCode / Cline   other bounded executors
        |
        +---------- lease / target_runtime / holding_id --------+
                           |
                    Holding-local estate
```

Hermes remains an optional operational specialist/compatibility layer where retained evidence justifies it. OpenCode and other CLI agents are bounded workers/executors. None may become a second Mission Control, manufacture task truth, bypass Founder/red-zone gates, or silently inherit a Holding's credentials/authority.

## Office 6133 temporary topology

The current Windows Office host physically co-locates the global Mission Control/Universal plane with H02, H03 and H04. While those Holdings remain on one host, one shared DIE agent runtime pool may serve them when all of these remain true:

- every job carries `holding_id` and, when local execution matters, `target_runtime`;
- filesystem/service access is resolved to the intended Holding estate;
- credentials remain scoped to the capability/holding/provider that owns them;
- evidence and receipts retain Holding attribution;
- Mission Control owns task/lease/review state;
- a shared agent is capacity, not organizational authority.

Co-location is a deployment optimization, not an identity merge. If H02/H03/H04 later move to separate hosts, the logical shared pool may dispatch remotely or be split by measured locality/security requirements without changing the global authority model.

## H01 exception

H01 is a dedicated Linux factory/execution plane with existing internal production runtimes. H01 does not need a full duplicate resident copy of every DIE CLI agent merely for symmetry.

H01 may consume:

1. holding-local workers already proven by the H01 production contract;
2. shared Office agent capacity over a governed SSH/delegated-execution boundary for diagnosis or engineering;
3. additional H01-local CLI agents only when workload, locality, isolation or recovery evidence justifies them.

The existing H01 OpenCode Worker-001 remains a Holding-local worker capability. It is not the global shared agent pool.

## 9router boundary

9router used by CLI agents as a model/provider gateway is a separate capability from the H01 Founder Console work.

H01 port `127.0.0.1:20128` is reserved by the accepted H01 Founder Console architecture for a presentation-only/read-only console body. It must not be treated as the canonical port or authority for a company-wide 9router agent gateway.

Any shared 9router gateway used by DIE agents must have its own runtime identity, port/service contract, secret boundary and observability. It may provide provider routing/capacity, but it must not become Mission Control or Founder Console authority.

## Public OpenCode surfaces

Public presentation names identify logical capability scope rather than physical host:

- `opencode.aethers.web.id` = shared DIE OpenCode presentation/capability currently hosted on Office 6133.
- `opencode-h01.aethers.web.id` = H01 holding-local OpenCode surface.

Moving the shared pool to another host should not require renaming `opencode.aethers.web.id`; only the ingress/runtime binding changes.

Public OpenCode surfaces must require authentication and must not expose provider credentials, tokens, session files or unrestricted host authority.

## Memory/context layer

A lightweight persistent cross-agent memory layer may be shared when it stores governed context rather than authority. Agent memory can help recover yesterday/today/next direction, but:

- Mission Control remains task truth;
- canonical Git/Company Truth remains authoritative over remembered prose;
- memory entries are attributable and replaceable;
- secrets are not promoted into shared memory;
- stale memory cannot override current task/role/holding policy.

## Scaling rule

```text
number of Holdings != number of resident agent stacks

agent capacity scales with:
queue pressure
+ workload locality
+ isolation requirements
+ recovery value
+ economics
```

The default is pooled, demand-driven capacity. Dedicated per-Holding agent runtimes are exceptions justified by evidence.

## Acceptance

This decision reconciles the current Office co-location, H03 supervisor proof, ORG-001 pooled-resource doctrine, H01 factory isolation, and the distinction between the 9router Founder Console presentation experiment and any separate CLI-agent gateway. It grants no new spend, publication, credential mutation or unrestricted execution authority.
