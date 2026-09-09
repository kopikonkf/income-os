# ORG-001 — 50-Holding Shared Control-Plane Resource Model v1

Status: ACCEPTED MODEL / NO INFRASTRUCTURE PROVISIONING
Date: 2026-09-09
Authority: subordinate to DIE Constitution, COS-001 host-exit plan, COS-002 control-plane reconciliation, COS-003 Aether↔DIE bridge, and Mission Control MC-009/MC-010 acceptance gates.

## 1. Decision

DIE must scale organizationally by **logical Holding namespaces + shared capacity pools**, not by cloning one complete agent stack or one VPS per Holding.

```text
50 Holdings
!= 50 Mission Controls
!= 50 Universal MCPs
!= 50 copies of each web-AI principal
!= 50 resident Hermes/OpenCode stacks
!= necessarily 50 VPS

50 Holdings
= 1 authoritative global control plane
+ 1 global company-truth plane
+ pooled cognition capacity
+ pooled generic compute/render/storage capacity
+ up to 50 logical holding-local execution/security domains
+ physical nodes only where measured workload/locality requires them
```

`one global control plane` means one **logical authority**. Future HA replicas may exist only if they preserve one writer/leader and cannot create competing mission truth.

## 2. Identity dimensions

```text
holding_id   = business/accounting/governance namespace
principal_id = global cognition identity/capability
runtime_id   = concrete execution runtime
endpoint_id  = deterministic capability endpoint
host_id      = physical/virtual machine
```

Example:

```text
Owner principal = claude-web-01
Holding          = H01
Target runtime   = architect-h01-linux
Endpoint         = architect.h01.mcp.aethers.web.id
Physical host    = die-prod-01
```

A principal does not become H01-owned merely because it works on H01. A host does not become a Holding merely because one Holding is deployed there.

## 3. Resource scaling classes

### G0 — Global singleton logical authorities: O(1)

These do **not** multiply with Holding count:

- Founder constitutional authority;
- DIE Constitution / identity canon;
- DIE State Manager logical company-truth authority;
- Mission Control logical operational-control authority after separate promotion gates;
- Universal MCP logical company capability surface;
- Economic Observer/Ledger logical company measurement plane;
- canonical Git repositories/task graphs;
- global principal registry/routing policy;
- global incident taxonomy/policy;
- Aether remains one separate external strategic-cognition/identity domain.

For 1, 10, or 50 Holdings: **1 logical instance of each authority**.

### H1 — Holding namespace/control metadata: O(H_active)

Each active Holding requires logically separate:

- `holding_id` and policy namespace;
- business/accounting attribution namespace;
- allowed capabilities and authority-envelope references;
- holding-specific secret references, never secret values in global task payloads;
- target runtime registry entries;
- business-state/data roots where that Holding owns local state;
- local executor identity if privileged filesystem/service work exists;
- Holding-specific economic dimensions and P&L attribution;
- Holding-specific product/channel/provider adapters only where required.

At 50 active Holdings: **50 logical namespaces**, not 50 full agent stacks.

### H2 — Holding-local privileged executors: O(H_exec), H_exec <= H_active

A Holding that needs privileged local work gets a logical runtime such as:

```text
architect-h01-linux
architect-h02-linux
architect-h03-windows
...
architect-h50-<platform>
```

But logical runtime identity is not equal to physical host count. Multiple isolated Holding executor runtimes may coexist on one physical compute node if filesystem roots, service identity, policy and endpoint resolution remain isolated. One filesystem-capable endpoint must never load-balance a request across different hosts.

A cognition-only Holding may have `H_exec=0` until local privileged work exists.

### P1 — Global cognition pool: O(CognitiveWorkload), not O(Holdings)

Mission Control already states `principal_pool_above_holdings=true`.

Shared examples:

- ChatGPT web/approved API capacity;
- Claude reviewer/cognition capacity;
- Manus long-horizon capacity;
- Grok signal/research capacity;
- Qwen engineering/tool capacity;
- Gemini/Google ecosystem capacity where supported;
- future licensed/BYOK/API providers.

Do **not** create `50 x principal pool` for 50 Holdings.

Scale cognition capacity from measured pressure such as sustained queue wait/SLA miss, provider capacity failures, high utilization with eligible queued work, insufficient reviewer availability, or positive unit economics supporting another licensed seat/API budget.

Free-tier capacity may be used lawfully while available; profitable workloads should graduate to licensed/subscription/API/BYOK capacity when economics justify it.

### P2 — Generic CPU worker pool: O(CPUWorkload)

Examples: metadata transforms, deterministic QA, document compilation, batch post-processing, research processing where permitted, packaging, and bounded OpenCode/CLI worker execution where retained.

Workers should be ephemeral or queue-driven where practical. A Holding leases capacity; it does not own a permanently idle worker daemon by default.

### P3 — Expensive media/render/API pool: O(ExpensiveWorkload)

Examples: video generation, paid image generation, GPU render/inference, premium reasoning/API calls, commercial voice/video services.

```text
cheap cognition/filtering first
-> expensive generation only for accepted candidates
```

Scale from observed conversion/revenue/learning economics, not because another Holding exists.

### P4 — Shared storage/egress: O(DataProduced + Retention)

Scale by artifact bytes, derivatives/media, evidence/receipts, backups/snapshots, knowledge corpus size and egress. Logical namespaces remain Holding-specific even when physical storage is pooled.

### A1 — Observability/state volume: O(WorkEvents)

Mission/task/attempt/review/incident/economic events grow with actual work, not configured Holding count. Fifty mostly-idle Holdings should be cheap.

## 4. 50-Holding reference topology

```text
                         FOUNDER / CONSTITUTION
                                  |
                 +----------------+----------------+
                 |                                 |
        AETHER (KEEP_EXTERNAL)              GLOBAL COMPANY PLANE
         strategic cognition                 State Manager
                 |                           Mission Control
                 |                           Universal MCP
                 |                           Economic Observer/Ledger
                 |                                 |
                 +------------ proposals/evidence-+
                                                   |
                             GLOBAL PRINCIPAL POOL
                         GPT / Claude / Manus / Grok /
                          Qwen / Gemini / APIs / BYOK
                                                   |
                 +---------------------------------+--------------------------------+
                 |                                 |                                |
                H01                               H02                              H03
          asset/production                  affiliate/media                knowledge/PDF
          local executor                    local executor                  local executor
          local data/services               media adapters                 knowledge estate
                 |                                 |                                |
                 +------------------- POOLED CAPACITY FLEETS ------------------------+
                                      CPU / render / storage
```

Extend H04...H50 by namespace and required local execution/data services, not by copying the whole stack.

## 5. Physical-host model

A plausible early topology may be:

```text
H03 Windows control-plane host
  Mission Control + Universal + browser workforce + H03 local executor

H01 Linux production host
  H01 Factory/MUXIA/data + H01 local executor

H02 Linux/media host(s)
  affiliate/publishing services + H02 local executor

N cheap pooled CPU worker nodes
M specialized render/API capacity units
```

Later 50-Holding topology may have `N << 50` physical nodes when workloads fit shared isolated fleets, or `N > 50` when a few high-volume Holdings need multiple nodes. Host count follows workload/SLA/security locality, never Holding count by formula.

## 6. What scales per Holding vs workload

| Resource | 1 Holding | 50 Holdings | Scaling driver |
|---|---:|---:|---|
| Mission Control logical authority | 1 | 1 | global singleton |
| DIE State Manager logical authority | 1 | 1 | global singleton |
| Universal MCP logical authority | 1 | 1 | global singleton |
| Aether external strategic domain | 1 | 1 | external singleton |
| Holding namespaces | 1 | 50 | active Holding count |
| Holding P&L/attribution dimensions | 1 | 50 | active Holding count |
| Logical local Architect executors | 0..1 | 0..50 | Holdings needing privileged local work |
| Physical executor/VPS hosts | estate-dependent | **not fixed at 50** | workload, locality, isolation, SLA |
| Web/API cognition slots | pooled | pooled | task arrival/service time/capacity |
| Reviewer slots | pooled | pooled | review-required workload + independence |
| Generic CPU workers | pooled | pooled | CPU/memory/queue workload |
| Video/GPU/premium API capacity | pooled | pooled | expensive accepted workload + economics |
| Storage | pooled namespaces | pooled namespaces | retained bytes/egress |
| Task/incident/economic events | workload-based | workload-based | actual operations |
| Resident Hermes/OpenCode stack | evidence-dependent | **not x50** | retained unique capability only |

## 7. Capacity equations

For pooled service class `k`:

```text
OfferedLoad_k = arrival_rate_k * average_service_time_k
RequiredSlots_k >= OfferedLoad_k / target_utilization_k
```

`target_utilization_k` is an observed policy value, not invented here.

Physical compute:

```text
RequiredCapacity
= peak accepted workload
+ recovery/review headroom
+ bounded redundancy requirement
```

Scale-out requires both operational evidence of constraint **and** economic justification. Holding count or AI suggestion alone is insufficient.

## 8. Cost model

```text
Cost_company(t)
= GlobalFixed(t)
+ HoldingDirect(t)
+ SharedCognitionUsage(t)
+ SharedComputeUsage(t)
+ SharedMediaUsage(t)
+ StorageEgress(t)
+ DistributionTransactionCost(t)
+ OtherGovernedCost(t)
```

The architecture seeks to keep `GlobalFixed` near O(1) while expansion cost follows actual economically useful workload.

Per-Holding economics must distinguish direct cost, shared variable consumption, global fixed overhead, and any optional managerial overhead allocation under an explicit `allocation_policy_id`.

## 9. Isolation and noisy-neighbor rules

Required:

- per-Holding queues/quotas or fair scheduling where contention matters;
- task carries `holding_id` and optional `target_runtime`;
- filesystem/service execution resolves one Holding-local endpoint;
- credentials/permissions stay scoped to the relevant estate;
- evidence/telemetry preserve Holding attribution;
- one noisy Holding cannot consume all reviewer/control-plane capacity without policy response;
- capacity shortage never relaxes L3/red-zone/reviewer gates.

## 10. Suggested resource hierarchy

```text
Tier 0 — global control capacity
Mission Control / State Manager / Universal / incident path

Tier 1 — shared cognition/reviewer capacity
scale from queue/SLA evidence

Tier 2 — generic cheap compute
scale only when workload exists

Tier 3 — expensive production/render/API
scale after cheap filtering + economic evidence

Tier 4 — dedicated Holding hardware
only when locality, isolation, throughput or economics beat pooling
```

## 11. Economic coupling

ORG-001 emits measurable resource dimensions for ECON-001+:

```text
holding_id
runtime_id
principal_id/provider_id
resource_class
usage_quantity
usage_unit
cost_event_ref when paid
parent_task/economic_trace_id
```

This makes claims such as "H03 needs one more cognition seat" or "H02 video API is destroying margin" measurable rather than intuitive.

## 12. ORG-001 acceptance

**PASS.** One global logical control/company-truth plane, global principal pool, workload-scaled shared compute/media/storage, and Holding-local privileged execution domains are separated explicitly. The model quantifies O(1), O(H_active), O(H_exec), and O(actual workload), and makes clear that 50 Holdings do not imply 50 VPS or 50 resident agent stacks. No infrastructure, provider plan, account, runtime, DNS, credential, Aether estate or authority was changed.
