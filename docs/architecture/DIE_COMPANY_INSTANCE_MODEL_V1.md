# DIE Company Instance Model v1

Date: 2026-08-31  
Status: GOVERNED ? cognitive-principal isolation phase 1

## Decision

DIE-WINDOWS and DIE-LINUX are sibling **company runtime instances** that consume one reviewed shared canon. They are not source-code forks and they must not share mutable state, credentials, browser profiles, or external ChatGPT accounts.

```text
                       DIE HOLDINGS / SHARED CANON
          roles + engines + schemas + tests + reviewed source
                              |
                 +------------+------------+
                 |                         |
            DIE-WINDOWS                DIE-LINUX
          stable reference           candidate primary
                 |                         |
       Windows Exec / Div01      Linux Exec / Div01
       existing accounts          NEW dedicated accounts
       old principal ids          Linux-specific principal ids
```

## Identity layers

`ROLE != PRINCIPAL != EXTERNAL ACCOUNT != COMPANY INSTANCE != RUNTIME`.

Shared role anchors remain singular:

- Executive role: `company/executive/IDENTITY.md`
- Division01 role: `company/division/division001/IDENTITY.md`

Instance principal bindings are:

| Instance | Role | Principal ID | MCP |
| --- | --- | --- | --- |
| DIE-WINDOWS | Executive | `chatgpt-plus-executive` | `executive-mcp.aethers.web.id` |
| DIE-WINDOWS | Division01 | `division-head-division01` | `division01-mcp.aethers.web.id` |
| DIE-LINUX | Executive | `die-lnx-executive-001` | `executive-mcp.aethers.biz.id` |
| DIE-LINUX | Division01 | `die-lnx-division-001` | `division01-mcp.aethers.biz.id` |

The two Linux principals reuse the shared semantic role anchors and capability contracts, but authority is resolved against their own server-pinned principal IDs.

## State and account boundaries

Each instance owns its external account sessions, OAuth/MCP secrets, browser profile and mutable state. No account credential or session is copied from Windows to Linux. A Linux account must never authenticate to a Windows principal endpoint and vice versa.

The shared repository is the upgrade channel. Improvements proven on Linux flow back to Windows through reviewed commits and compatibility tests, not filesystem copying or manual source divergence.

## Cross-instance routing

Cross-instance semantic routing is denied by default. In particular, Linux Division01 escalation targets Linux Executive (or Founder), while Windows Division01 targets Windows Executive (or Founder). No hidden route from Linux cognition into Windows Executive is allowed.

## Phase-1 limitation

This version isolates the external cognitive principals first. Hermes and worker logical identity namespaces remain transitional/shared identifiers. Therefore this phase must not be described as full operational active-active federation. Full company-instance independence requires later operational-principal/state namespace work.

## Login handoff

`IDENTITY-LNX-REKEY-004` is an operator boundary. The Founder logs NEW dedicated ChatGPT accounts into the existing isolated Linux browser profiles. No browser infrastructure rebuild is required. Only after that login may `MCP-LNX-003` perform real ChatGPT-cloud OAuth/tool/context E2E.
