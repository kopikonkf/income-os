# Executive MCP Activation Readiness v1

Status: IMPLEMENTED LOCALLY; NO DEPLOYMENT OR REGISTRATION
Base: PR #5 merged at `bbfaaf8778d32b1d0cc96e260968323ce0c78abf`
Activation target: ChatGPT Plus Executive, Developer mode, private Secure MCP Tunnel

## 1. Audit correction

Executive Line 1 and Line 2 are implemented in the repository, but neither is
an active ChatGPT connection yet. Code completion and runtime activation are
different states.

The VPS audit found:

- no running DIE Executive MCP process;
- no Windows service whose executable points to `C:\DIE`;
- no Secure MCP Tunnel client command;
- no production snapshot HMAC key or key ID;
- the Python MCP SDK is installed;
- unrelated Proxima, Aether, and CodeGraph MCP processes remain outside this
  activation boundary.

The existing Chief Executive Architect MCP must not be reused: Architect DEV
authority is a separate, Founder-invoked trust plane and cannot be inherited by
runtime cognition.

## 2. Current OpenAI transport baseline

Official OpenAI documentation states that ChatGPT Developer mode is available
to Plus and supports SSE and streaming HTTP MCP connections. Write actions are
treated as writes and require confirmation by default; accurate
`readOnlyHint` metadata matters.

For a private MCP server, OpenAI documents Secure MCP Tunnel as the supported
developer-mode path without exposing the private server directly to the public
Internet. A tunnel can reach a configured stdio or HTTP MCP server.

References:

- https://developers.openai.com/api/docs/guides/developer-mode
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/connect-chatgpt

This internal activation chooses Secure MCP Tunnel. Public plugin submission,
public HTTPS proxying, OAuth 2.1 authorization-server construction, and
OpenAI-managed mTLS are out of scope.

## 3. Two distinct lanes

Line 1 and Line 2 remain separate MCP connections:

```text
Executive Line 1
  -> read-only tools
  -> context_snapshot
  -> readOnlyHint: true

Executive Line 2
  -> decision_submit only
  -> append-only canonical write
  -> readOnlyHint: false
  -> idempotentHint: true
  -> user confirmation required
```

They require distinct tunnel IDs. This prevents a read-only connection from
silently acquiring mutation capability.

Entrypoints:

```powershell
python bin/die_executive_line1_mcp.py
python bin/die_executive_mcp.py
```

## 4. Non-secret readiness checker

Run:

```powershell
python bin/die_executive_activation_check.py
```

The checker validates:

- Line 1 metadata is entirely read-only;
- Line 2 exposes exactly `decision_submit` as an idempotent write;
- both servers publish bounded instructions;
- server identities and entrypoints are distinct;
- shared snapshot HMAC key presence and minimum length;
- HMAC key ID presence;
- Secure MCP Tunnel activation mode;
- tunnel client presence;
- two present, distinct tunnel IDs.

It returns booleans and blocker names only. It never returns the HMAC value or
tunnel IDs and performs no provisioning, process start, service mutation,
network exposure, deployment, or ChatGPT registration.

## 5. Correct activation order

The earlier handoff placed HMAC provisioning before the service boundary.
The live audit showed that no DIE MCP service or tunnel client exists, so doing
that first would create an orphaned credential.

Correct order:

1. merge this non-secret activation-readiness package;
2. under explicit Founder authorization, install/configure the Secure MCP
   Tunnel client and obtain two distinct tunnel IDs;
3. under the same or a separate explicit credential authorization, generate
   and provision one strong snapshot HMAC key plus rotation ID into both
   dedicated MCP process environments;
4. run the readiness checker until `activation_ready: true`;
5. start the two dedicated MCP processes/tunnels and verify with MCP Inspector;
6. enable ChatGPT Developer mode, register both tunnel connections, and inspect
   discovered metadata;
7. prove Line 1 reads without write confirmation;
8. prove Line 2 presents confirmation and fails closed on an unsigned request;
9. perform the first real decision only under a separate explicit Founder
   authorization.

## 6. Hard exclusions

This package does not:

- generate or provision any credential;
- install a tunnel client;
- create a tunnel;
- start or register an MCP service;
- expose a public port;
- modify firewall, DNS, TLS, Cloudflare, or Windows services;
- mutate live `EVENTS.jsonl` or `DECISIONS.jsonl`;
- connect Hermes;
- change MCP Proxima.
