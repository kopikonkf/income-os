# DIE Architect Linux Early Staging Amendment V1

Date: 2026-09-08
Founder decision: Linux-native Architect MCP should be staged before MC-008F so Linux execution and Mission Control routing do not depend on a Windows-to-Linux SSH hop.

## Safety invariant

This amendment advances **staging and proof**, not control-channel handoff.

```text
MCP-LNX-005 DONE
  -> MX-053 Linux Architect coexistence staging
  -> MX-054 Linux Architect E2E proof

CUT-004 -> CUT-005 --------------------+
MX-053 -> MX-054 ----------------------+-> CUT-006 Founder handoff
```

- Windows Architect MCP remains active as rollback/control throughout MX-053 and MX-054.
- MX-053 is eligible after MCP-LNX-005 because the non-Architect Linux MCP/wake/identity substrate is already accepted.
- MX-054 proves Linux endpoint/tool parity without switching the active connector.
- CUT-006 now requires **both** MX-054 and CUT-005, plus explicit Founder action.
- No Windows retirement, connector switch, credential copy, publication, or spend is authorized by this amendment.

## Mission Control rationale

A Linux-native `chatgpt-architect` principal removes the SSH relay from normal Linux execution and gives Mission Control a native owner path for Linux engineering tasks. Windows remains a bounded fallback until CUT-006.
