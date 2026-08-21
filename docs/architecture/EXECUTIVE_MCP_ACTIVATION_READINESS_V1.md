# Executive MCP Activation Readiness v1.1

Status: IMPLEMENTED LOCALLY; NO DEPLOYMENT OR REGISTRATION
Base: PR #6 merged at `290f64a1eae218b59c3ce0bae67f6d0b8023d740`
Activation target: private Executive Line 1/Line 2 MCP connections through Secure MCP Tunnel

## 1. Why v1.1 exists

Activation Readiness v1 correctly separated code readiness from runtime activation,
but its deployment gate did not include every prerequisite in the current official
OpenAI Secure MCP Tunnel contract. It could therefore report
`activation_ready: true` after injecting HMAC, tunnel-client, and tunnel IDs even
when the OpenAI control-plane identity or ChatGPT workspace access was absent.

v1.1 closes that false-positive path before any credential, tunnel, process,
deployment, exposure, or registration is performed.

## 2. Official OpenAI baseline

The official Secure MCP Tunnel guide establishes that:

- the tunnel is outbound-only and does not require public ingress;
- `tunnel-client` needs a `tunnel_id`, a runtime control-plane API key, and
  reachability to the private MCP server;
- running the client or selecting a tunnel requires **Tunnels Read + Use**;
- tunnel access belongs to a Platform organization and must be associated with
  the intended Platform organization and ChatGPT workspace;
- ChatGPT Developer Mode is a separate workspace/account permission;
- the target host needs outbound HTTPS to `api.openai.com:443` by default;
- the client should be validated with `tunnel-client doctor` before ChatGPT
  discovery and tool testing.

Canonical reference:

- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

This internal Founder/Executive lane remains a private developer-mode connection.
Public plugin submission, public HTTPS proxying, and OAuth construction remain out
of scope.

## 3. Separate trust lanes

Line 1 and Line 2 remain separate connections and require distinct tunnel IDs:

```text
Executive Line 1
  -> bounded observation/context tools
  -> readOnlyHint: true

Executive Line 2
  -> decision_submit only
  -> readOnlyHint: false
  -> idempotentHint: true
  -> explicit user confirmation
```

A read-only connection must never silently inherit Line 2 mutation authority.

## 4. Fail-closed readiness contract

Run:

```powershell
python bin/die_executive_activation_check.py
```

Schema:

```text
die.executive.mcp.activation.readiness.v1.1
```

The checker now evaluates three groups:

1. code contract;
2. OpenAI control-plane prerequisites;
3. local deployment prerequisites.

New control-plane checks:

| Environment contract | Meaning | Secret |
| --- | --- | --- |
| `CONTROL_PLANE_API_KEY` | Runtime identity for `tunnel-client`; presence and minimum length only | Yes |
| `DIE_OPENAI_TUNNELS_READ_USE_GRANTED` | Founder/operator attests Tunnels Read + Use is granted | No |
| `DIE_OPENAI_TUNNEL_WORKSPACE_ASSOCIATED` | Founder/operator attests the target ChatGPT workspace is associated | No |
| `DIE_CHATGPT_DEVELOPER_MODE_ENABLED` | Founder/operator attests Developer Mode is available and enabled | No |

Existing deployment checks remain:

- activation mode is `secure_mcp_tunnel`;
- production snapshot HMAC key has at least 32 UTF-8 bytes;
- HMAC key ID is present;
- tunnel-client is present;
- Line 1 and Line 2 tunnel IDs are present and distinct.

Attestations accept only explicit truth values: `1`, `true`, `yes`, or `on`.
Missing, blank, or any other value fails closed.

The result returns booleans and blocker names only. It never returns the HMAC key,
control-plane API key, tunnel IDs, raw configuration, or credential material.

## 5. Correct activation order

1. merge the v1.1 gate hardening;
2. verify the target Platform organization, Tunnels Read + Use permission,
   ChatGPT workspace association, and Developer Mode access;
3. obtain separate explicit authorization to install/configure tunnel-client and
   create two distinct tunnel identities;
4. obtain separate explicit authorization to generate and provision the
   production HMAC key, key ID, and tunnel runtime API key without disclosing
   their values;
5. set the non-secret attestations only after the corresponding facts are
   verified;
6. run the checker until `activation_ready: true`;
7. start the two dedicated MCP/tunnel processes and validate both profiles with
   `tunnel-client doctor` and MCP Inspector;
8. register Line 1 and Line 2 separately in ChatGPT and inspect discovered
   metadata;
9. prove Line 1 read behavior and Line 2 confirmation/fail-closed behavior;
10. submit the first real canonical decision only under a separate Founder
    authorization.

## 6. Verification

```text
targeted activation tests
7 passed

full bridge regression
69 passed

live readiness
schema=die.executive.mcp.activation.readiness.v1.1
code_ready=true
activation_ready=false
exit=2
secret_values_returned=false
deployment_performed=false
registration_performed=false
```

The expected live control-plane blockers are:

- control-plane API key absent;
- Tunnels Read + Use not yet attested;
- target ChatGPT workspace association not yet attested;
- ChatGPT Developer Mode not yet attested.

## 7. Hard exclusions

This refactor does not:

- install or configure tunnel-client;
- create or modify any OpenAI tunnel;
- generate or provision any credential;
- start, stop, or register an MCP process/service;
- expose a public port;
- change firewall, DNS, TLS, Cloudflare, or Windows services;
- mutate live `EVENTS.jsonl` or `DECISIONS.jsonl`;
- touch projection/organism runtime artifacts;
- connect Hermes;
- change Worker or MCP Proxima.
