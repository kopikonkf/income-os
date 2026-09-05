# Factory Asset Provider Feasibility v1

**Task:** FA-110  
**Date:** 2026-09-05  
**Status:** CANONICAL CANDIDATE  
**Machine-readable scorecard:** `company/factory-asset/registries/provider-feasibility.v1.json`

## Decision

Factory has one current Linux production anchor and four additional evidenced Windows autonomous candidates. The order is:

1. **ChatGPT/MUXIA — 85/100 — CURRENT_LINUX_ANCHOR**
2. **Qwen — 79/100 — NEXT_LINUX_EXTRACTION_CANDIDATE**
3. **Gemini — 71/100 — WINDOWS_PROVEN_LINUX_CANDIDATE**
4. **Manus — 71/100 — WINDOWS_PROVEN_LINUX_CANDIDATE**
5. **Duck.ai — 70/100 — WINDOWS_PROVEN_LINUX_CANDIDATE**
6. **Grok — 25/100 — DEFERRED_NOT_IN_ACTIVE_POOL**

The numeric score is an engineering prioritization aid only. It **does not authorize routing, spend, provider access, publication, or quota use**. Policy and health gates remain authoritative and can override any score.

## Evidence boundary

The scorecard is pinned to canonical Factory evidence, primarily the Windows/OAUTH proof chain plus current policy contracts:

- `FA-W009` proves real provider image generation and strict local original-byte validation for all six names, but explicitly does **not** claim autonomous operation for the five browser-operator proofs at that stage.
- `FA-W011` defines Level-2 as zero operator action after `dispatch_committed_at`; allowed transports are `SESSION_API`, `BROWSER_CDP`, `HYBRID`, or `OFFICIAL_API`. `BROWSER_OPERATOR`, `UNKNOWN`, and `UNSUPPORTED` cannot pass Level-2.
- `FA-W012` pins Qwen `SESSION_API` as the Level-2 reference; `FA-W018` adds an explicit proven `BROWSER_CDP` fallback without replacing the primary route.
- `FA-W013`, `FA-W015`, `FA-W016`, and `FA-W017` prove zero-touch-after-dispatch BROWSER_CDP artifacts for Gemini, Manus, ChatGPT, and Duck.ai respectively.
- `FA-W019` accepts the current autonomous candidate pool as Qwen + ChatGPT + Gemini + Manus + Duck.ai and keeps Grok optional/deferred.
- `FA-103` policy registry currently marks those five as `ALLOWED_EVIDENCED`; Grok is `DEFERRED_PLATFORM_GATE`.
- `FA-102` forbids guessed quota and converts stale capacity observations to `UNKNOWN`.
- The current Linux ChatGPT/MUXIA runtime is separately proven by the Factory live-production chain, including the FA-140C/FA-140C-R1 workspace/export recovery. This Linux evidence is used only for the Linux-feasibility dimension; it does not retroactively change Windows provider proofs.

## Scoring model

| Dimension | Max | What earns points | Fail-closed rule |
|---|---:|---|---|
| Transport maturity | 20 | Proven Level-2 transport; dual proven routes score highest | `UNKNOWN` / operator-only is not autonomous |
| Policy readiness | 15 | Current `ALLOWED_EVIDENCED` policy | Deferred/unknown policy cannot route |
| Auth operability | 10 | Proven pre-authenticated/no-account boundary without post-dispatch operator action | Plan/auth gate stays blocked |
| Linux feasibility | 20 | Live Linux proof scores highest; portable-but-unproven candidate gets limited credit | No Linux canary = not `PROVEN_LIVE` |
| Image capability | 15 | Real provider-original image bytes strictly validated | Text/status/URL/screenshot is not image success |
| Capacity evidence | 10 | Evidence maturity only | No jobs/day or quota extrapolation from latency |
| Technical quality | 5 | MIME/magic/dimensions/decode/reopen/hash integrity | Not a subjective marketplace-quality score |
| Maintainability | 5 | Lower coupling / stronger fallback architecture | Engineering assessment, never provider fact |

`TOTAL = transport + policy + auth + linux + image + capacity + technical_quality + maintenance`

## Provider scorecard

| Provider | Transport | Policy | Auth | Linux | Image | Capacity | Tech QA | Maint. | Total | Disposition |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ChatGPT/MUXIA | 14 | 15 | 10 | **20** | 15 | 3 | 5 | 3 | **85** | Current Linux anchor |
| Qwen | **20** | 15 | 10 | 6 | 15 | 4 | 5 | 4 | **79** | Next extraction/canary |
| Gemini | 14 | 15 | 10 | 6 | 15 | 3 | 5 | 3 | **71** | Normalize after common boundary |
| Manus | 14 | 15 | 10 | 6 | 15 | 3 | 5 | 3 | **71** | Normalize after common boundary |
| Duck.ai | 14 | 15 | 10 | 6 | 15 | 3 | 5 | 2 | **70** | Normalize after common boundary |
| Grok | 4 | **0** | **0** | **0** | 15 | **0** | 5 | 1 | **25** | Deferred; not active pool |

### Capacity is intentionally conservative

For Qwen, ChatGPT, Gemini, Manus, and Duck.ai, sustained capacity remains **`UNKNOWN`**. A bounded successful generation proves that a route can work at the observed attempt; it does not prove hourly quota, daily quota, concurrency, 100/day, 1,000/day, or 5,000/day. Qwen receives one extra evidence-maturity point because both its primary and fallback transports have bounded success evidence; that is resilience evidence, not throughput evidence.

Grok has a dated negative capacity observation (`HIGH_DEMAND / PROVIDER_CAPACITY_UNAVAILABLE`) followed by a `SUPERGROK_UPGRADE_GATE`. The scorecard does not interpret that as permanent unavailability, does not authorize spend, and does not invent a workaround. Current routing remains deferred.

## Provider notes

### ChatGPT/MUXIA

**Why first overall:** it is the only candidate in this scorecard with current live Linux production evidence. Windows BROWSER_CDP Level-2 is also proven, and MUXIA already owns the Linux browser/session boundary. The next architectural task is therefore normalization (`FA-113`), not a second browser owner.

**Known risk:** browser/session/UI maintenance remains real. Current live success must not be converted into a claim of known provider quota.

### Qwen

**Why next to extract:** Qwen has the strongest transport architecture among providers not yet proven in the Linux Factory: `SESSION_API` primary plus explicit `BROWSER_CDP` fallback. That makes `FA-111 -> FA-112` the best next Linux provider expansion path.

**Truth boundary:** Windows evidence does not itself prove Linux compatibility. Until `FA-112` passes, Linux state remains `CANDIDATE_NOT_PROVEN`.

### Gemini

A dedicated authenticated Windows BROWSER_CDP backend produced provider-original JPEG bytes with zero post-dispatch operator action. An attempted SESSION_API bootstrap was explicitly classified `UNKNOWN_TRANSPORT`; the scorecard does not guess an opaque replacement RPC. Linux remains unproven until its normalized adapter/canary chain.

### Manus

Windows BROWSER_CDP Level-2 passed and the generated artifact was distinguished from unrelated Manus UI artwork before acceptance. That is strong provenance discipline, but the generated-CDN discovery surface remains a browser/provider maintenance dependency. Linux remains unproven.

### Duck.ai

A fresh Windows BROWSER_CDP Level-2 attempt passed using provider data-URI bytes, while prior failed artifacts were preserved as non-PASS evidence. The route is viable but comparatively UI/DOM-coupled, so maintenance risk is scored slightly higher. Linux remains unproven.

### Grok

Grok has Level-1 real-image proof, but the bounded Level-2 attempt hit `PROVIDER_CAPACITY_UNAVAILABLE/HIGH_DEMAND`, and the current Imagine preflight later exposed a SuperGrok spend/platform gate. Policy is therefore deferred and autonomous transport readiness is not claimed. Grok is **non-blocking** for Factory progression.

## Linux execution order

```text
CURRENT
  ChatGPT/MUXIA live Linux anchor
        |
        +--> FA-113 normalize boundary (no duplicate browser owner)

NEXT EXPANSION
  FA-110 DONE
        |
        +--> FA-111 Qwen clean extraction
                |
                +--> FA-112 bounded authorized Linux canary

FOLLOWING CANDIDATES
  Gemini -> FA-114
  Manus  -> FA-116
  Duck   -> FA-118

OPTIONAL / DEFERRED
  Grok   -> FA-115 only when policy/plan route is eligible
```

This ordering preserves the Factory principle that a provider is an interchangeable production backend, not the Factory itself. The router must consume typed capability/policy/health evidence and remain indifferent to vendor-specific wire details.

## Non-claims

This scorecard does **not** claim:

- any provider can sustain a particular jobs/day rate;
- any unknown quota, rate limit, or concurrency value;
- Linux support for Qwen/Gemini/Manus/Duck.ai before their Linux acceptance tasks;
- marketplace aesthetic quality or acceptance probability from file-integrity checks;
- Grok current eligibility;
- spend, quota evasion, account farming, protection bypass, or credential transfer authority.
