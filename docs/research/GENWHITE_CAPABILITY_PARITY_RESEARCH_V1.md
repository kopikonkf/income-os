# GenWHITE Capability Parity Research V1

Status: FA-W010 DONE/PASS
Date: 2026-09-03
Method: clean-room observation of public product information only; no purchase, login, account action, proprietary-code extraction, protection bypass, or backend endpoint guessing.

## Observed GenWHITE product capabilities

Public product evidence observed on 2026-09-03 supports these product-level claims:
- desktop app for Windows 10+ and macOS 11+;
- White Mode (theme/object driven) and Prompt Mode;
- Auto-Pilot generation and automatic download;
- automatic save/load for unfinished or not-yet-downloaded results;
- direct 2K and 4K output claims;
- consistency controls for style/color/description;
- custom icon color and white/green-screen/HEX background controls;
- 31 public style presets across realistic, vector, line-art, icon, illustration and 3D-render categories;
- public statement that generation processing runs server-side rather than on the local computer;
- public note that future Google Gemini AI technical/system changes can affect the product.

Source: https://lynk.id/templatix.id/lxg0j4878yo6 (observed 2026-09-03).

## Explicit unknowns

The public evidence reviewed does NOT establish:
- internal provider API/session mechanism;
- queue implementation or fairness;
- explicit pause/resume semantics for an active batch;
- retry count/backoff rules;
- rate-limit/capacity telemetry;
- crash-reconciliation algorithm;
- dedupe/idempotency behavior;
- output lineage/hash/QA model;
- whether every advertised style is a separate model, prompt preset, or another mechanism.

These remain UNKNOWN and must not be copied or inferred.

## Factory Console capability mapping

| Observable pattern | Evidence state | Factory-owned requirement |
| --- | --- | --- |
| Auto-Pilot batch run | OBSERVED | Batch intent -> governed Factory Core queue |
| Auto download | OBSERVED | Automatic durable master ingestion + gallery refresh |
| Auto save/load | OBSERVED | Durable queue state + restart reconciliation |
| 2K/4K choice | OBSERVED | Blueprint/master-spec resolution control subject to provider capability |
| Style presets | OBSERVED | Versioned Console presets that compile into Blueprint inputs; not semantic IDs by themselves |
| Consistency controls | OBSERVED | Reusable style/color/description constraints pinned in batch intent |
| Custom backgrounds | OBSERVED | Blueprint production constraint, not provider-specific UI logic |
| Server-side generation | OBSERVED product claim | Console remains thin client; Factory Core/providers own execution |
| Queue internals | UNKNOWN | Factory Core FA-105 owns queue, fairness, retry, resume and reconciliation |
| Pause/resume | UNKNOWN publicly | Factory Console must expose it through FA-105 governed semantics |
| Retry/rate-limit visibility | UNKNOWN publicly | FA-102/104/107 provide observed capacity, routing rationale and typed failures |
| Output dashboard internals | PARTIAL/UNKNOWN | Factory Console FA-C008 uses canonical masters/derivatives/hashes/QA |

## Clean-room product decision

Factory Console should reproduce useful operator capabilities, not GenWHITE implementation. It must remain a control plane over Factory Core and web-ai-adapter/MUXIA. No provider credential/session ownership, direct vendor wire calls, or marketplace publication authority belongs in the GUI.

## Acceptance

PASS. Queue/batching, auto persistence/download, style/consistency controls, resolution and background controls are mapped to Factory-owned contracts. Unsupported areas remain explicitly UNKNOWN. No purchase/account action or proprietary implementation access occurred.