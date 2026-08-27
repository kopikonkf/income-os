# MUXIA — PROXIMA KEEP / REIMPLEMENT / RETIRE AUTOPSY V1

Status: MX-011 COMPLETE / READ-ONLY SOURCE CLASSIFICATION
Date: 2026-08-26
Source baseline: `D:\V2 Proxima` at `06b9c9bea212122e76ecfadb88f307378dd9bd7d`
Legacy support tree: `D:\proximav2-setup`
Successor: MUXIA

## 1. Executive verdict

MUXIA must **not** be implemented by moving, copying, renaming, or mechanically extracting the Proxima source tree.

The correct migration pattern is:

```text
PROXIMA LIVE
  |
  +-- observe proven behavior/contracts
  +-- preserve runtime/evidence
  +-- classify source concepts
  |
  v
INDEPENDENT DIE IMPLEMENTATION
  |
  +-- new MUXIA source tree
  +-- new tests from DIE-owned requirements/receipts
  +-- no Electron dependency
  +-- no Proxima code copy unless separate commercial rights are proven
```

`D:\V2 Proxima` and `D:\proximav2-setup` remain untouched legacy inputs until an explicit cutover/retirement decision.

## 2. License blocker discovered

`D:\V2 Proxima\LICENSE` states **PERSONAL, NON-COMMERCIAL USE ONLY** and explicitly prohibits:

- commercial use by businesses/organizations;
- using the software as part of a commercial product/service;
- enterprise/corporate deployment.

DIE is a commercial program. Therefore, absent a separate commercial license/permission owned by Founder, the Proxima implementation is **REFERENCE-ONLY** for MUXIA.

### Binding MUXIA rule

- Do not copy Proxima source into MUXIA.
- Do not create MUXIA by renaming the Proxima repository/product.
- Do not transplant Proxima tests verbatim.
- Preserve only independently stated functional behavior, receipts, protocols, and acceptance criteria that DIE can lawfully reimplement.
- If Founder possesses separate commercial rights, record that evidence through a separate licensing decision before changing this rule.

This autopsy is an architecture/code-reading classification, not a legal opinion.

## 3. Classification vocabulary

- `KEEP-CONTRACT` — behavior/requirement is valuable and should survive, but implementation is rewritten independently.
- `REIMPLEMENT` — build a new DIE-owned equivalent behind MUXIA interfaces.
- `RETIRE` — do not carry the component/behavior into MUXIA V1.
- `DEFER` — not needed for MUXIA V1; reconsider only with a concrete business requirement.
- `PRESERVE-LEGACY` — do not modify/delete yet; retain as live fallback/evidence.
- `PROBE` — unresolved fact that must be measured rather than assumed.

## 4. Source classification

| Legacy area | Classification | MUXIA decision |
| --- | --- | --- |
| `LICENSE` | PRESERVE-LEGACY / BLOCKER | Never copy implementation into commercial MUXIA without separate rights evidence. |
| `electron/main-v2.cjs` | KEEP-CONTRACT + REIMPLEMENT | Preserve concepts: bounded loopback service lifecycle, provider registry, orderly shutdown, settings, per-provider serialization. Rewrite without Electron/UI coupling. |
| Electron `BrowserWindow` / `BrowserView` / renderer UI / `index-v2.html` / preload / IPC UI handlers | RETIRE | No Electron windowing in MUXIA core. Optional future dashboard is a separate control surface. |
| `electron/browser-manager.cjs` profile/session concept | KEEP-CONTRACT + REIMPLEMENT | Dedicated persistent browser identity, lifecycle, operator auth recovery, isolated provider/session handling are useful. Implement with Playwright persistent profiles/process ownership. |
| `browser-manager.cjs` stealth/fingerprint spoofing/client-hint manipulation/automation camouflage | RETIRE / DO NOT PORT | MUXIA does not disguise automation or attempt protective-measure bypass. Protection/auth ambiguity becomes `WAITING_OPERATOR`/`BLOCKED`. |
| permissive certificate-error handling in Electron main | RETIRE | MUXIA keeps normal browser/TLS validation; no provider-specific certificate bypass. |
| `electron/providers/api.cjs` provider-adapter abstraction | KEEP-CONTRACT + REIMPLEMENT | Keep versioned provider adapter boundary and readiness/state checks. Rewrite against Playwright/browser surfaces. |
| engine-script injection pattern into provider pages | RETIRE for MUXIA V1 | Do not make arbitrary injected private-web-API engines the MUXIA foundation. Provider-specific automation must pass policy/contract review. |
| `chatgpt-engine.js` direct session-token/backend/SSE/private endpoint logic | RETIRE / DO NOT PORT | Not part of MUXIA V1. Do not copy token extraction, private backend calls, or internal challenge-handling implementation. |
| `chatgpt-engine.js` proof-of-work/challenge solver logic | RETIRE / DO NOT PORT | Protective/challenge logic is a hard boundary; MUXIA fails closed to operator rather than solving/circumventing protections. |
| `chatgpt-engine.js` visible UI state observations (composer ready, send button, generation completion) | KEEP-CONTRACT, POLICY-GATED REIMPLEMENT | Useful as high-level state requirements, but any automated consumer-web execution/export requires a current provider-policy gate before implementation. |
| `electron/providers/image-artifact-export.cjs` durable artifact behavior | KEEP-CONTRACT + REIMPLEMENT | Strong requirement: bounded raster type detection, size cap, atomic persistence, SHA-256 identity, receipt, no signed URL/token leakage. Rewrite independently and remove Electron fallback path. |
| `electron/providers/sender.cjs` per-provider queue + bounded transient retry | KEEP-CONTRACT + REIMPLEMENT | Implement queue/lease semantics in MUXIA Job Manager. Retry only safe/idempotent transient failures. |
| `electron/api/rest-api.cjs` loopback REST gateway concepts | KEEP-CONTRACT + REIMPLEMENT | Preserve private-loopback API, auth, bounded body, stats, provider-neutral routing, durable artifact response metadata. Split from browser runtime and Electron settings. |
| OpenAI-compatible response shape / current `/v1/models` compatibility | KEEP-CONTRACT where useful | Preserve only the minimal compatibility required by DIE Worker/M-001; do not inherit unrelated surface area automatically. |
| BYOK subsystem | DEFER | Not required for current MUXIA economic thesis. Add later only as a replaceable provider backend if demanded. |
| `proxima-agent`, generic agentic/memory/workflow subsystems | RETIRE from MUXIA responsibility / DEFER elsewhere | MUXIA is not `agentd`. Agent reasoning/memory belongs to DIE Agent Runtime/Context Fabric, preventing duplicated control planes. |
| generic MCP subsystem | DEFER | Architect/DIE MCP already exists. MUXIA should expose a bounded control API/capability and be surfaced through DIE control plane later, not duplicate a generic MCP product by default. |
| CLI/SDK | KEEP-CONTRACT later / REIMPLEMENT | Compatibility CLI/SDK may be rebuilt after core runtime proves stable; not copied from Proxima. |
| desktop auto-updater / installers / Electron Builder | RETIRE | Server/runtime deployment uses DIE service/container packaging, not desktop installer mechanics. |
| provider engines other than ChatGPT | DEFER | MUXIA V1 proves ChatGPT primary producer first. Add Qwen/Gemini/etc. only after concrete requirements and independent adapters. |
| `net-tracer.cjs`, `net-trace.log`, reverse-engineering/debug payload dump patterns | RETIRE / SENSITIVE LEGACY | Do not port network credential/body capture into MUXIA. Historical logs must be treated as potentially credential-bearing legacy data. |
| legacy settings/provider config | PRESERVE-LEGACY / SPEC REFERENCE | Useful to identify provider names/ports only; MUXIA defines new configuration schema. |
| Proxima tests | REFERENCE-ONLY | Derive new DIE-owned tests from MUXIA PRD, receipts, and observable behavior; do not copy test source verbatim. |
| `D:\proximav2-setup\artifacts` | PRESERVE-LEGACY EVIDENCE | Existing durable output/receipts are baseline evidence; do not move/delete during refactor. |
| copied source/docs under `D:\proximav2-setup` | PRESERVE-LEGACY until provenance classified | Not authoritative source. Do not develop from this tree. |

## 5. What MUXIA actually needs from Proxima

The valuable inheritance is small and behavioral:

```text
A. persistent authenticated browser identity
B. provider/profile isolation
C. bounded job serialization/ownership
D. reliable browser lifecycle
E. observable provider state
F. durable image artifact materialization
G. hash/size/type receipt
H. private loopback control contract
I. crash/retry/fail-closed behavior
J. compatibility with existing DIE Worker producer boundary
```

Everything else is either implementation detail, legacy desktop UX, duplicated agent functionality, provider-specific technical debt, or deferred capability.

## 6. New MUXIA module boundary implied by autopsy

```text
muxia/
  core/
    profile-registry
    lease-manager
    job-manager
    artifact-registry
    state-machine

  browser/
    playwright-driver
    process-supervisor
    profile-store

  providers/
    contract
    chatgpt/        # policy-gated adapter, independently implemented

  api/
    loopback-server
    compatibility

  observability/
    health
    sanitized-logging

  tests/
    parity-contract
    profile-isolation
    crash-recovery
```

No module above requires Electron.

## 7. Legacy tree relationship

### `D:\V2 Proxima`

Canonical legacy Git/source + current live executable origin. Preserve exactly as-is while MUXIA is built side-by-side.

### `D:\proximav2-setup`

Non-Git support/artifact/copy tree. It contains existing durable artifacts and historical/copy files. Preserve it as legacy evidence/runtime support but do not treat it as source authority.

### Safety rule

MUXIA development must not use either path as its writable source directory.

## 8. Explicit probes created from unknowns

The following facts remain unknown and must be measured in later bounded tasks rather than assumed:

### MX-P01 — Legacy profile-root metadata probe

Purpose: identify the active Proxima user-data/profile root(s) using metadata only, without reading/exporting cookies/tokens/session values.

Must complete before any profile migration/import strategy is approved.

### MX-P02 — Legacy support-tree provenance probe

Purpose: classify `D:\proximav2-setup` content as `artifact | receipt | generated runtime | copied source | stale | sensitive-log` before any cleanup/retirement.

Must complete before legacy storage cleanup/cutover.

### MX-P03 — ChatGPT web execution policy gate

Purpose: re-check current provider terms/product rules and define the allowed MUXIA ChatGPT adapter boundary before implementing automated prompt/output transport. Technical parity evidence does not override provider policy.

Must complete before implementing a production ChatGPT adapter that performs unattended web execution/output extraction.

These probes do not authorize reading session secrets or altering profiles.

## 9. MX-011 acceptance

- source baseline pinned: PASS
- key Electron/browser/provider/artifact/API paths inspected: PASS
- KEEP/REIMPLEMENT/RETIRE/DEFER classification produced: PASS
- Electron dependency isolated as legacy rather than target: PASS
- stealth/challenge/protective-measure logic explicitly excluded: PASS
- commercial license incompatibility identified and converted into no-copy rule: PASS
- `D:\V2 Proxima` preserved unchanged: PASS
- `D:\proximav2-setup` preserved unchanged: PASS
- unknowns converted to explicit probes: PASS
- implementation/refactor performed: NO

## 10. Next atomic task

`MX-012 — Build parity contract tests`

MX-012 must create **new DIE-owned tests/spec fixtures from MUXIA requirements and prior receipts**, not copy Proxima test source. The first parity contract should focus narrowly on:

1. profile/job/artifact contract inputs;
2. durable raster validation + SHA-256 receipt behavior;
3. false-success rejection;
4. current Worker-facing compatibility shape;
5. no Electron dependency in the test contract.

No live provider automation is needed to build the parity contract itself.
