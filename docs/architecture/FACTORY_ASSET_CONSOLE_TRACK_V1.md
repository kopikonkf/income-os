# Factory Asset Console Track V1

Status: RATIFIED
Date: 2026-09-03
Task: FA-C000

## Purpose

Factory Console is the Founder-operated web control plane for batch and mass-production workflows. It is not a second orchestration engine and does not own provider/browser automation.

## Authority boundaries

```text
Factory Console
    ↓ governed intents / normalized events
Factory Core
    ↓ queue / router / capacity / leases / retry / reconciliation
web-ai-adapter
    ↓ provider normalization
SESSION_API or BROWSER_CDP
    ↓ when browser-backed
MUXIA runtime
```

Factory Console may expose Blueprint, Batch, Queue, Providers/Capacity and Output/QA views. It does not store or export provider credentials, launch provider-specific browsers, call vendor wire protocols directly, bypass provider protection, publish to marketplaces, or convert UI state into canonical truth.

## Current provider-pool decision

The current proven autonomous/backend-reference pool is sufficient to continue Factory and Console work:

- Qwen — SESSION_API primary, BROWSER_CDP fallback proven.
- ChatGPT — BROWSER_CDP, standalone/MUXIA-compatible.
- Gemini — BROWSER_CDP.
- Manus — BROWSER_CDP.
- Duck.ai — BROWSER_CDP.
- Grok — optional/deferred because current availability is gated by provider/plan policy outside Factory control.

Grok must not lower truth standards when resumed, but its unavailability does not block unrelated Factory progression. No SuperGrok spend, account action or bypass is authorized by this decision.

## Clean-room GenWHITE-like benchmark

Observable product patterns such as queueing, batching, pause/resume, retries, rate-limit visibility, automatic save/download, style controls and output dashboards may be studied and translated into Factory-owned requirements. Proprietary-code extraction, reverse engineering of protected implementation, purchase/account action and unsupported backend assumptions are outside scope.

## Staged Console track

`FA-C000..FA-C013` deliberately separates early GUI/product work from backend authority:

1. clean-room capability matrix and Console PRD;
2. synthetic GUI shell and Blueprint controls;
3. Factory Core API/event binding;
4. queue/provider/output operational views;
5. synthetic E2E;
6. bounded real-provider canary;
7. batch/concurrency and recovery proofs;
8. Founder production-grade acceptance after the authorized 100-unique-master/day Factory model passes.

This allows visible product progress early without creating a second source of routing, retry, capacity or provider truth.