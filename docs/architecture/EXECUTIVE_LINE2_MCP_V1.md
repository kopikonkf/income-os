# Executive Line 2 MCP v1

Status: IMPLEMENTED LOCALLY ON FEATURE BRANCH
Principal: `chatgpt-plus-executive`
Scope: `company_portfolio`
Input dependency: `die.context.snapshot.v1`
Commit dependency: `die.state.request.v1` -> `die.decision.gateway.result.v1`

## 1. Decision

Executive Line 2 v1 is a dedicated mutation MCP transport. It is separate from:

- the existing read-only Line 1 MCP;
- the Chief Executive Architect development MCP;
- MCP Proxima V2, which remains the Worker ↔ Web Chat AI production-engine path;
- Hermes, which remains the sole operational control plane.

The server exposes exactly one business capability:

`decision_submit`

It does not expose filesystem, shell, database, Git, service-control, credential, worker, or arbitrary JSON-write capabilities.

## 2. Trust boundary

The MCP process pins:

- principal: `chatgpt-plus-executive`;
- scope: `company_portfolio`;
- action: `state.decision.submit`;
- object type: `DECISION`.

The model cannot supply or override those values. A future network-facing adapter must authenticate the connection to this dedicated process; caller-supplied identity is not accepted as authentication.

The tool accepts:

- a replay-safe `request_id`;
- a fresh signed Line 1 `source_snapshot`;
- one commit-ready semantic decision;
- typed evidence already present in the snapshot;
- bounded assumptions.

## 3. Executable composition

```text
ChatGPT Plus Executive
  -> Line 1 context_snapshot
  -> Line 2 decision_submit
  -> P5 validate_and_normalize
  -> P6 Decision Gateway
  -> DIE State Manager (sole writer)
  -> typed committed/rejected receipt
  -> Hermes-ready route
```

The transport does not write state itself. Its production bootstrap injects only
`die_event.commit_normalized_decision`.

## 4. Tool contract

```json
{
  "request_id": "REQ-EXEC-L2-0001",
  "source_snapshot": {"schema_version": "die.context.snapshot.v1"},
  "decision": {
    "decision_class": "strategy",
    "choice": "Run the bounded falsification experiment",
    "reason": "It limits cost before scaling",
    "alternatives_rejected": []
  },
  "evidence_refs": [],
  "assumptions": []
}
```

Unknown fields are rejected. There is no principal, scope, action, object type,
path, command, or credential parameter.

## 5. Security and failure rules

- Snapshot freshness, deterministic integrity, server HMAC, authority, scope, evidence, and semantic bounds are revalidated by P5/P6.
- Missing or wrong HMAC trust fails closed with `E_SNAPSHOT_UNTRUSTED`.
- Raw host paths, traversal, and credential-shaped values are rejected.
- An absent/failing State Manager writer fails closed.
- Mutation is rate-limited to 12 tool calls per process-hour before validation.
- `request_id` replay returns the same decision ID without another append.
- A committed decision is only marked `ready_for_operational_acceptance`; Line 2 does not dispatch Hermes or execute workers.
- No production secret is provisioned or stored by this package.

## 6. Runtime

Newline-delimited MCP JSON-RPC over stdio:

```powershell
python bin/die_executive_mcp.py
```

This package deliberately stops at the governed MCP transport. Remote hosting,
TLS, connection authentication, ChatGPT app registration, and production HMAC
provisioning are deployment concerns requiring their own explicit authorization.

## 7. Acceptance

```powershell
python bin/die_company_brain_check.py
python -m py_compile bridge/income_os_bridge/executive_mcp_server.py bin/die_executive_mcp.py
python -m pytest bridge/tests -q
```

Acceptance requires proof that:

- exactly one semantic mutation tool is exposed;
- identity/scope cannot be caller-overridden;
- P5 and P6 are composed rather than bypassed;
- unsigned snapshots fail closed without invoking the writer;
- raw access and unknown tools are rejected;
- process-local mutation throttling works;
- sequential replay produces one decision row;
- isolated stdio MCP round-trip commits and replays correctly;
- neither unit nor end-to-end tests modify live `EVENTS.jsonl` or `DECISIONS.jsonl`.
