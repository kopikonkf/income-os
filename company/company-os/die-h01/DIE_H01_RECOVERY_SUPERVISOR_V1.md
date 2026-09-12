# DIE-H01 Recovery-only Supervisor v1

Status: H01-015 acceptance candidate
Date: 2026-09-12

## Boundary

The H01 Supervisor is a **recovery executor**, not an orchestrator. Mission Control on `die-control` remains the only business scheduler. The Supervisor has no feeder, graph-intake loop, task/provider selection, prompt/seed generation, or scope-expansion authority.

```text
Mission Control / accepted runtime observation
        |
        v
explicit incident envelope
        |
        v
Recovery Supervisor
  | L0 -> reobserve / reconcile same work / bounded wait (no mutation)
  | L1 -> exact allowlisted local recovery + verification
  | L2 -> engineering escalation
  + L3 -> Founder escalation
```

One invocation handles one explicit incident. There is no background business polling loop and no timer that can synthesize work.

## Observation boundary

The Supervisor may observe sanitized health metadata for:

- Mission Control / Universal MCP standing supplied by the accepted control-side boundary;
- fixed H01 runtime services;
- Factory Cluster A/B loopback `/v1/status` endpoints;
- browser-owner services and sanitized broker ownership/lease counts.

It does not read cookies, tokens, session bytes, provider conversation content, arbitrary browser storage, or Company Truth stores. Mission Control is observe-only from H01; Windows boot/watchdog recovery remains owned by `die-control`.

## L0

Allowed L0 playbooks are exactly `L0_REOBSERVE`, `L0_RECONCILE_SAME_WORK`, and `L0_WAIT_BACKOFF`. They perform no service/process mutation and cannot create replacement business work. A retry/resume must refer to the same durable work identity outside this Supervisor boundary.

## L1

L1 supports only `L1_RESTART_ALLOWLISTED_SYSTEMD`. The exact local allowlist is:

- `die-executive-runtime-mcp.service`
- `die-division01-runtime-mcp.service`
- `die-runtime-mcp-cloudflared.service`
- `die-fa121-cluster-broker.service`
- `die-muxia-cluster-b.service`
- `die-muxia-dispatch.service`
- `die-muxia-cluster-a-browser.service`
- `die-muxia-cluster-b-browser.service`

Legacy `die-hermes-gateway.service` and `die-opencode-web.service` are intentionally excluded. No arbitrary systemd unit, shell command, filesystem repair, cleanup path, or remote Windows restart is accepted.

L1 requires all of: unambiguous ownership; no ambiguous external side effect; active business work absent or explicitly reconciled safe; and, for browser owners, no active browser job and no held UDD lock. Recovery is not successful merely because restart returned zero: `systemctl is-active` must verify the exact unit as active.

## Durable anti-loop rule

The local ledger is `/var/lib/die/h01/supervisor/recovery-ledger.json`. An L1 attempt is written before mutation. Maximum automatic budget is two L1 attempts for one stable fingerprint in a rolling 60-minute window. If the same fingerprint recurs after a successful L1 recovery inside that window, it escalates to L2 rather than restarting again. Process reboot does not reset the ledger.

## Hidden-authority rejection

Incident input fails closed if it tries to carry task creation, queue dispatch, provider/task selection, prompt/seed generation, business scheduling, scope expansion, Mission lease/review capability, cookies/tokens/session bytes, spend, credential mutation, submission, or publication authority.

L1 cannot edit source/config as a recovery primitive. Repeatable code/schema/config defects are L2 engineering work and require their own governed task/worktree authority.

## Runtime Gateway relationship

H01-012 remains unchanged. Cross-VPS business traffic is still only `WORK_DISPATCH`, `WORK_CHECKPOINT`, and `WORK_RESULT`; the recovery Supervisor is H01-local and is not added as a generic WAN RPC or recovery scheduler. It never persists Mission owner/reviewer capabilities.

## Live acceptance observation

A read-only H01 observation during H01-015 found all eight allowlisted local services active. Factory Cluster A and B both returned `READY`, each with zero active leases and one open browser page; both browser-owner services were active. Mission Control standing was injected from the current Mission Work Card/H01-011 accepted control-plane boundary as healthy `mc-mission-v1` scheduler authority.

No live L1 restart was justified because no accepted incident existed. The executable path was therefore canaried with an L0 re-observation only; no process, browser owner, service, queue, work item, credential, or `/srv/die` state was mutated.
