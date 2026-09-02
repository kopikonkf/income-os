# Factory Asset Level Up — Product Requirements Document v1

**Date:** 2026-09-02
**Status:** CANONICAL v1.1 — ratified via FA-000 governed publication
**Project:** Digital Income Empire / LEVEL UP DIE
**Product tracks:** Asset Blueprint v2, Asset Derivative Engine, Factory Asset Core
**Target repository:** `github.com/kopikonkf/income-os`
**Doctrine:** Build > Run > Verify > Refactor > Extend
**Execution split:** Linux isolated hourly build + Windows `D:\OAUTH` image-provider laboratory

## 1. Executive decision

Factory Asset must stop treating every opportunity as “generate one PNG.” The target product is a commercial-asset manufacturing system that chooses the correct native representation, producer, delivery formats, and marketplace package before generation begins.

Founder decision on 2026-09-02 splits execution into two parallel lanes:

1. `LINUX_HOURLY_BUILD` builds schemas, registries, compilers, deterministic derivative/vector/package workers, Factory Core, and later native producers from isolated worktrees. It may inspect production evidence read-only, but must never deploy to, restart, reconfigure, or write through the live Production Organism.
2. `WINDOWS_OAUTH_LAB` preserves the already-working text/chat-completion path and proves image generation separately for Qwen, ChatGPT, Gemini, Grok, Manus, and Duck.ai through prompt → real generated image → original bytes → automatic local VPS save.

The live Linux schedule `die-production-cycle-v1` remains independent and continues at `0 */3 * * *`. Factory development must not change that cadence or its runtime state.

The core model is:

```text
Noun / long-tail opportunity
          ↓
Commercial asset opportunity
          ↓
Asset Blueprint v2
          ↓
Native producer selection
          ↓
Immutable canonical master
          ↓
Deterministic derivatives and packages
          ↓
QA / rights / metadata / Founder QC
          ↓
Marketplace-ready package
```

There is no universal `master.png` for every asset family:

| Asset family | Native representation | Canonical master | Typical delivery formats |
| --- | --- | --- | --- |
| Photo / raster illustration | Raster | Lossless provider output, commonly PNG | JPEG, WebP, TIFF, PDF/preview |
| Isolated object | Raster + alpha | PNG | PNG, JPEG preview, WebP |
| Icon / outline / flat vector | Vector scene/paths | SVG or native vector source | SVG, EPS, PNG preview |
| Pattern | Vector or procedural recipe | SVG/source recipe | SVG, EPS, PNG/JPEG tile previews |
| Motion | Timeline/code/scene | Source project + lossless intermediate | MP4, MOV, animated WebP/GIF where valid |
| Template / layered design | Editable document model | PSD/AIT/INDT/PPTX/etc. | Native editable file + previews |
| 3D | Scene/model | GLB/GLTF/OBJ/FBX as selected | Model + textures + preview renders |

For the current Linux raster pipeline, ChatGPT or Qwen may continue to emit PNG as the immutable source master. A photo opportunity may still be delivered as JPEG after deterministic conversion. Vector, motion, layered, and 3D opportunities must eventually use native producers; they must not be disguised raster exports.

## 2. Evidence baseline

### 2.1 Current production organism

- The Linux Production Organism is live and has started producing PNG artifacts.
- The proven production chain already includes opportunity intelligence, blueprinting, MUXIA generation, upscale, metadata/rights/QA/QC stages, durable receipts, and manual publication authority.
- This project extends that chain. It does not replace the DIE State Manager, Hermes, MUXIA, QA/QC, submission governance, or marketplace authority boundaries.

### 2.2 `D:\OAUTH` / `web-ai-adapter` audit snapshot

- Repository: `kopikonkf/web-ai-adapter`.
- Local `HEAD` and recorded `origin/main` are both `bc155d4279b9a5eefe98113ed64ca32e221a59dc`.
- The local worktree contains extensive modified and untracked experimental files; it is not safe to import wholesale.
- The committed `tests/` directory is empty. The current image smoke harness is an untracked standalone script rather than a canonical regression suite.
- Qwen live test: `HTTP 200`, about 33.4 seconds, base64 image payload returned.
- Qwen transport is now verified as `SESSION_API`: a browser establishes/refreshes the login session, while generation uses session cookies with direct HTTP/SSE calls to Qwen web endpoints and does not require a continuously running browser GUI.
- Eleven PNG files were observed under `D:\ASSETS\OAUTH`, all 2048×2048 and roughly 4.05–4.93 MB.
- Content hashing found only nine unique images: two pairs are exact duplicate bytes under different paths. This proves the need for content-addressed ingestion and idempotent save behavior.
- Gemini returned an image URL, but direct download was blocked with HTTP 403.
- ChatGPT failed when the required CDP browser endpoint was unavailable.
- Grok failed because the hypothesized generation route returned 404/no image.
- Manus remained pending until the polling deadline and produced no artifact.
- Duck.ai has an experimental adapter against a text-chat endpoint, but native image generation is not evidenced. It remains `CAPABILITY_UNKNOWN`, not a working image provider.
- The local Git remote stores an inline credential. Its value must never enter documentation or logs; credential rotation and remote sanitization require a separate authorized security task.

Conclusion: Qwen is a proven research provider, not yet a production provider. `D:\OAUTH` is an upstream laboratory whose reusable logic must pass a provenance/security autopsy and be extracted through a stable interface.

### 2.3 GenWHITE benchmark

The preserved 2026-09-01 product-page snapshot describes server-side generation, Gemini dependency, 2K/4K output, Auto-Pilot, automatic download, style presets, and thousands of assets per day. A live refetch on 2026-09-02 was blocked by HTTP 403, so no stronger claim is made.

The public evidence does not prove whether GenWHITE uses an official API, a key pool, web sessions, or a hybrid. It validates a product pattern—queue + remote provider + resume + download—not a backend mechanism or sustainable economics.

## 3. Problem statement

### 3.1 Format problem

The current runtime produces raster PNG masters regardless of the commercial asset opportunity. This creates four defects:

1. Asset type is decided too late or inferred from a file extension.
2. Vector, motion, template, and 3D opportunities have no native producer route.
3. Marketplace delivery requirements are not compiled into deterministic recipes before production.
4. Format copies risk being counted as new assets even though they are only packages of the same semantic work.

### 3.2 Scale problem

The current ChatGPT web lane is one image provider, not the factory. Free-web account limits are dynamic and often unpublished. UI flows, session expiry, provider policy changes, anti-abuse systems, output quality, and marketplace rejection can dominate throughput.

The question is therefore not “How do we make ChatGPT generate 5,000 images?” It is:

> How does Factory Core schedule commercially justified asset jobs across verified providers while preserving account isolation, policy compliance, lineage, quality, economics, and resumability?

## 4. Goals

1. Make `Asset Blueprint v2` the canonical pre-generation contract.
2. Select native representation and producer class before work is queued.
3. Convert raster masters locally into valid marketplace derivatives without an LLM.
4. Provide native vector routes and a narrowly gated raster-trace fallback.
5. Keep every master and derivative immutable, content-addressed, idempotent, and reproducible.
6. Separate Factory Core from provider implementations.
7. Turn observed account capacity into a dated ledger; never invent or hard-code an undocumented free-tier limit.
8. Reuse verified Qwen work only after extraction, tests, Linux canary, security cleanup, and policy evidence.
9. Scale through evidence gates: stability → quality → marketplace acceptance → economics → higher volume.
10. Preserve Founder authority for spend, account actions, credentials, policy exceptions, publication, and irreversible cutover.
11. Allow hourly Linux engineering without modifying the live three-hour Production Organism.
12. Prove each Windows image lane with durable original image bytes; URLs, screenshots, HTTP 200, or textual completion alone are not success.
13. Preserve the working `D:\OAUTH` text/chat-completion engine with before/after regression checks.

## 5. Non-goals for v1

- Generating 1,000–5,000 sellable assets per day immediately.
- Creating or farming accounts to evade quotas.
- Bypassing CAPTCHA, Cloudflare, anti-abuse controls, rate limits, or provider access restrictions.
- Treating format conversions as unique commercial inventory.
- Converting photorealistic PNGs into fake “vectors” containing embedded raster data or pathological path counts.
- Implementing PSD, AIT, INDT, 3D, cinematic video, fonts, or audio before a native editable producer contract exists.
- Automating marketplace publication or waiving the Founder submission gate.
- Importing credentials, raw captures, session dumps, or the dirty `D:\OAUTH` worktree into `income-os`.
- Replacing MUXIA, Hermes, DIE State Manager, QA, QC, rights, metadata, or submission engines.
- Deploying Factory code into the live Linux Production Organism during the isolated build program.
- Restarting or changing `die-production-cycle-v1`, its three-hour cadence, browser profiles, credentials, queues, or active artifacts.
- Claiming that every web-chat provider supports native image generation before live original-byte evidence exists.

## 6. Product terminology

### 6.1 Semantic asset

A commercially distinct work with its own utility and identity. Examples: shopping-bag photo, shopping-bag outline icon, and shopping-bag repeating pattern.

### 6.2 Canonical master

The immutable highest-fidelity source produced by a native producer or accepted provider. It is the root of lineage and is never overwritten.

### 6.3 Packaging derivative

A format, size, color-space, preview, or marketplace-specific representation of the same semantic asset. JPEG, WebP, TIFF, and PDF exports of one PNG master remain one semantic asset.

### 6.4 Semantic variant

A new commercial work with a distinct use case, blueprint, and `semantic_asset_id`. It is not created merely by changing format, compression, dimensions, or background color.

### 6.5 Marketplace package

The exact files, previews, metadata, rights declarations, and compatibility receipt required for one marketplace route. A package is not a publication.

### 6.6 Provider profile

One isolated provider/account principal with capability, authentication mode, dated policy evidence, health, lease, observed capacity, and failure state. Credentials are opaque references and never appear in canonical artifacts.

## 7. Product requirements

### 7.1 Asset Blueprint v2

Every production job must compile from a validated blueprint containing at least:

```json
{
  "schema": "die.asset-blueprint.v2",
  "blueprint_id": "BP-...",
  "opportunity_id": "OPP-...",
  "semantic_asset_id": "ASSET-...",
  "concept": "shopping bag for packing customer orders",
  "asset_type": "PHOTO|ISOLATED_OBJECT|ICON|OUTLINE|PATTERN|MOTION|...",
  "native_representation": "RASTER|VECTOR|PROCEDURAL|MOTION|LAYERED|3D",
  "producer_class": "WEB_IMAGE|VECTOR|PROCEDURAL|REMOTION|...",
  "canonical_master_spec": {
    "format": "PNG|SVG|...",
    "min_dimensions": [4096, 4096],
    "alpha": "REQUIRED|FORBIDDEN|OPTIONAL",
    "color_space": "sRGB"
  },
  "deliverables": [
    {
      "format": "JPEG",
      "recipe_id": "raster-jpeg-stock-v1",
      "marketplace_targets": ["ADOBE_STOCK"],
      "counts_as_distinct_asset": false
    }
  ],
  "distinctness_contract": {},
  "quality_contract": {},
  "rights_contract": {},
  "policy_contract": {}
}
```

Requirements:

- `native_representation` and `producer_class` are required and validated against `asset_type_registry`.
- Delivery formats are selected from dated marketplace profiles, not guessed from extensions.
- A raster producer cannot satisfy a native-vector requirement unless the blueprint explicitly permits `TRACE_FALLBACK` and the vector gate passes.
- `counts_as_distinct_asset` is always false for packaging derivatives.
- The compiler must reject impossible combinations before a provider job is dispatched.

### 7.2 Asset type registry

The registry maps each asset type to:

- native representation;
- allowed producer classes;
- canonical master formats;
- allowed derivative recipes;
- vectorizability class;
- alpha/color-space requirements;
- metadata and rights requirements;
- supported marketplace families;
- distinctness rules;
- current maturity: `SUPPORTED|EXPERIMENTAL|DEFERRED|PROHIBITED`.

### 7.3 Marketplace delivery profile registry

Profiles initially cover the current M-001 cohort: Adobe Stock, Dreamstime, 123RF, Vecteezy, and MotionElements.

Each profile includes:

- source URL and evidence date;
- asset family and accepted formats;
- dimensions, duration, codecs, color space, alpha, and size constraints;
- preview/source bundle requirements;
- AI labeling and rights declarations;
- similarity/duplicate constraints;
- profile version and freshness policy.

Stale or unknown requirements must produce `COMPATIBILITY_UNKNOWN`, never an inferred pass.

### 7.4 Asset Derivative Engine

The v1 engine is deterministic and does not call an LLM.

Raster functions:

- PNG → JPEG with explicit alpha flattening policy and quality recipe;
- PNG → WebP;
- PNG → TIFF;
- PNG → PDF/preview package;
- optional resize/thumbnail recipes;
- explicit ICC/color-space/DPI policy;
- metadata injection through the existing metadata contract;
- decode/reopen verification, magic-byte validation, dimensions, byte count, and SHA-256.

Vector functions:

- native SVG validation and normalization;
- SVG → EPS export with real vector paths;
- preview rendering;
- path-count, embedded-raster, text/font, clipping, bounds, and editability checks;
- gated simple-raster trace fallback for icons, outlines, silhouettes, and flat shapes;
- deterministic rejection for photorealistic or excessively complex raster input.

Idempotency:

```text
derivative_key = SHA256(
  master_sha256 + recipe_id + recipe_version + marketplace_profile_version
)
```

If a verified derivative with the same key already exists, the engine returns the durable receipt and performs no new write.

### 7.5 Artifact and derivative registry

Every master records:

- `master_asset_id`, `semantic_asset_id`, blueprint/job IDs;
- producer/provider/model/version and opaque account reference;
- prompt hash and source receipt;
- path, MIME, magic/container, dimensions, bytes, alpha, color space, SHA-256;
- quality, rights, metadata, and policy status.

Every derivative records:

- `derivative_id`, `master_asset_id`, `parent_sha256`;
- recipe ID/version and marketplace profile version;
- output path/hash/bytes/specification;
- QA results and compatibility status;
- `counts_as_distinct_asset=false`.

The DIE State Manager remains the sole canonical writer. Workers return proposals/receipts; they do not directly mutate canonical truth.

### 7.6 Factory Core provider abstraction

Required interface:

```text
generate(blueprint, compiled_prompt, output_spec, provider_profile_lease)
  -> provider_result | typed_failure
```

Provider capability fields include:

- supported native representations and asset types;
- output sizes/formats;
- prompt/image/reference support;
- latency and success observations;
- quality score observations;
- auth mode and `HUMAN_REAUTH_REQUIRED` state;
- policy/terms evidence date;
- observed capacity state;
- Linux/Windows/runtime dependency.
- transport class: `SESSION_API|BROWSER_CDP|HYBRID|OFFICIAL_API|UNSUPPORTED|UNKNOWN`.

Factory Core must not contain provider-specific wire formats.

Windows laboratory proof targets are Qwen, ChatGPT, Gemini, Grok, Manus, and Duck.ai. A provider passes only when a bounded live request produces a real generated image whose original bytes are saved locally and validate by magic/MIME, decode/reopen, dimensions, byte count, and SHA-256. If native image capability is absent, the lane must return `UNSUPPORTED_CAPABILITY`; it must not loop guessed endpoints or substitute a text answer, screenshot, or unrelated image.

### 7.7 Account isolation and browser budget

- One account principal = one profile = at most one active lease.
- Session material is never copied between principals.
- A lease identifies the exact job and expires/reconciles after crash.
- Maximum open tabs per principal is two: one work tab and one auth/recovery tab.
- Prefer a supported direct protocol or official API when permitted; use browser/CDP only where required and policy-compatible.
- Expired sessions and protection challenges become typed blocked states requiring the operator. No automated bypass is permitted.

### 7.8 Capacity ledger and router

Free-web capacity starts as `UNKNOWN`.

The ledger records observed events, not assumed quotas:

- timestamp, provider/profile, request/result;
- latency, output count, quality status;
- rate-limit/auth/protection response;
- rolling success and rejection rates;
- cooldown/retry-after where explicitly observed;
- human re-auth requirement;
- dated policy evidence.

The router is deterministic and considers:

```text
eligibility
× available observed capacity
× expected quality
× success rate
× marketplace fit
× cost per successful QA-passed master
− policy risk
− retry/failure cost
```

If all eligible providers are unavailable or unknown, the job blocks. It does not bypass a provider gate or silently route to an unapproved provider.

### 7.9 Queue, retry, and resume

- Jobs are idempotent and resumable.
- A generation attempt and a semantic asset are different records.
- No `SUCCEEDED` status without a durable matching master receipt.
- Retry only typed retryable failures, maximum two automatic attempts with governed backoff.
- Authentication, protection, account restriction, policy unknown, and malformed output fail closed.
- Duplicate content is deduplicated by SHA-256 before canonical ingestion.

### 7.10 Observability

Required measures:

- attempted generations;
- provider successes/failures by typed reason;
- unique canonical masters;
- duplicate outputs suppressed;
- masters passing QA;
- semantic assets produced;
- packaging derivatives produced;
- marketplace-ready packages;
- Founder-approved packages;
- submitted, accepted, licensed, and revenue counts from external evidence;
- CPU, memory, disk, browser process, and open-tab envelope;
- cost per successful master, QA-passed asset, accepted asset, and paid license.

Reports must never combine these counters. “5,000 files” must not be reported as “5,000 sellable assets.”

## 8. Quality and compatibility gates

### 8.1 Raster gate

- decodes and reopens successfully;
- magic bytes match declared MIME/extension;
- dimensions and byte size meet recipe/profile;
- no unintended alpha after JPEG conversion;
- color space and ICC policy pass;
- no truncation/corruption;
- output SHA differs only where expected;
- metadata and rights checks mapped to evidence.

### 8.2 Vector gate

- SVG/EPS contains vector paths, not merely an embedded bitmap;
- path count and file size remain within recipe bounds;
- no missing fonts or unsupported live text;
- bounds/viewBox and preview render pass;
- editability check passes;
- visual comparison meets the configured threshold;
- photorealistic/complex raster input is rejected from tracing.

### 8.3 Distinctness gate

- Format, resolution, compression, and background changes do not create a new semantic ID.
- New semantic variants require a distinct commercial use case and blueprint.
- Near-duplicate generation is quarantined before marketplace packaging.

## 9. Throughput strategy and unlocks

### 9.1 Parallel execution lanes

| Lane | Environment | Cadence | Allowed work | Hard boundary |
| --- | --- | --- | --- | --- |
| `LINUX_HOURLY_BUILD` | Linux isolated worktree/check-out | Once per hour, one eligible atomic leaf, then STOP | Schemas, registries, tests, compiler, derivative/vector/package workers, Factory Core, synthetic/native-producer fixtures, documentation and receipts | No mutation of `/srv/die` live runtime, production services, production profiles, current jobs, or `die-production-cycle-v1` |
| `WINDOWS_OAUTH_LAB` | `D:\OAUTH` on Windows | Founder-directed interactive work | Read-only autopsy, regression protection, adapter repair, bounded provider canaries, local image export proofs | No bulk import to `income-os`; no secret publication; no Linux mutation |
| `LINUX_PRODUCTION` | Existing Production Organism | Existing `0 */3 * * *` | Continue current governed artifact generation | Not an engineering target of this program |

The hourly scheduled task must read `origin/main`, Factory task graph, `LASTSTANDINGPOINT`, receipts, and active Factory/global repo-write leases. It selects only a READY task assigned to `LINUX_HOURLY_BUILD`, works in a fresh isolated worktree, validates, records the result, and stops. The Chat-mode schedule is active at minute `35` UTC. Until FA-000 publishes this revised pack to `origin/main`, its first-run bootstrap is restricted to FA-000 and must stop immediately afterward; normal Linux leaf selection remains locked.

Windows OAUTH tasks are excluded from the autonomous Linux selector because they may require active sessions, operator re-authentication, provider-policy judgment, or browser evidence.

The long-term capacity target is a research objective, not an immediate production promise.

| Unlock | Real workload | Required evidence |
| --- | --- | --- |
| U0 | Synthetic queue/derivative benchmark | Idempotency, resume, zero false success, no secrets |
| U1 | Existing 5-master derivative canary | Valid packages, lineage 100%, duplicate suppression |
| U2 | 20–50 masters/day | 24-hour stability, QA pass rate, observed provider capacity |
| U3 | 100 masters/day | Downstream QA/QC capacity, distinctness, marketplace-fit packages |
| U4 | 500 masters/day | At least two verified provider lanes or approved official/owned capacity; economics gate |
| U5 | 1,000 masters/day | Founder approval, revenue/acceptance evidence, no policy or quality regression |
| U6 | 5,000 masters/day | Separate architecture/economic decision; storage, QA, submission, and market absorption proven |

Higher unlocks must not be achieved by multiplying packaging formats or creating accounts to evade provider limits.

At current maturity, the recommended operational target remains quality-first: prove the derivative engine on the existing masters, then stabilize 20–50 and 100 masters/day. A 1K–5K/day provider fleet is premature before marketplace acceptance, QA throughput, and cost per accepted asset are known.

## 10. Acceptance criteria

### 10.1 Blueprint acceptance

The six shopping-bag fixtures compile deterministically:

1. `PHOTO` → raster producer → PNG master → JPEG delivery.
2. `ISOLATED_OBJECT` → raster producer → alpha PNG delivery.
3. `ICON` → native vector producer → SVG + EPS + PNG preview.
4. `OUTLINE` → native vector producer → SVG + EPS.
5. `PATTERN` → procedural/vector producer → SVG + raster previews.
6. `ANIMATION` → motion producer → MP4/MOV package.

Invalid cross-family combinations fail before dispatch.

### 10.2 Derivative engine acceptance

- At least five existing Linux PNG masters are processed.
- Every output is idempotent and has a complete receipt.
- Duplicate masters are suppressed by hash.
- JPEG/WebP/TIFF/PDF recipes pass decode/reopen and compatibility tests.
- At least two simple vector-eligible fixtures pass SVG/EPS export or trace; photorealistic input is correctly rejected.
- Zero false success and zero master overwrite.
- All master/derivative lineage is queryable.

### 10.3 Factory Core acceptance

- Synthetic provider fixtures prove routing, leases, capacity states, retries, crash recovery, and secret redaction.
- At least two independently isolated verified provider lanes complete bounded canaries before a multi-provider claim.
- No provider is used when policy evidence is stale/unknown or capacity is exhausted.
- Maximum two tabs per principal is enforced where browsers are used.
- Duplicate provider output produces one canonical master and multiple attempt receipts.

### 10.4 Windows OAUTH image-lane acceptance

- Working text/chat-completion regression remains green before and after image work.
- Qwen remains a proven `SESSION_API` reference lane and gains durable validation/deduplication tests.
- ChatGPT, Gemini, Grok, Manus, and Duck.ai are classified by evidenced transport rather than assumption.
- Each provider marked PASS completes prompt → real generated image → original-byte local save → decode/reopen/MIME/dimensions/bytes/SHA-256 receipt.
- URL-only, screenshot-only, text-only, HTTP-status-only, or silently swallowed download failures cannot pass.
- A provider that lacks native image capability is recorded as `UNSUPPORTED_CAPABILITY` and blocks the six-provider acceptance until Founder decides whether to substitute, defer, or remove that lane.
- No credential values, raw authenticated HAR payloads, cookies, or session dumps enter canonical source or receipts.

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Provider changes web protocol | Versioned adapter, health probe, typed `PROVIDER_DRIFT`, no silent fallback |
| Unpublished/dynamic free limits | Capacity ledger with `UNKNOWN` default; bounded probes; Founder gate for load tests |
| Quota evasion or account abuse | No account farming, CAPTCHA bypass, fake accounts, or limit circumvention; fail closed |
| Duplicate/spam portfolio | Semantic-vs-packaging identity rule, perceptual/semantic distinctness gates |
| Raster mislabeled as vector | Native-vector-first ADR; embedded-raster and path complexity checks |
| Metadata/rights lost in conversion | Recipe contract plus post-conversion metadata/rights verification |
| Credential leakage | Opaque credential refs, sanitized logs, provenance scan, separate security hardening task |
| Dirty `D:\OAUTH` import | KEEP/EXTRACT/REWRITE/RETIRE autopsy and minimal clean-room extraction |
| Volume outruns QA/market demand | Unlocks tied to QA, acceptance, licensing, and economics—not file count |
| Concurrent scheduled repo writes | Global engineering lease plus one atomic leaf per scheduled run |

## 12. Recommended implementation boundary

Suggested canonical layout after Founder approves publication:

```text
company/factory-asset/
├── schemas/
│   ├── asset-type-registry.schema.json
│   ├── asset-blueprint-v2.schema.json
│   ├── derivative-recipe.schema.json
│   └── provider-profile.schema.json
├── registries/
│   ├── asset-types.v1.json
│   └── marketplace-delivery-profiles.v1.json
├── receipts/
├── fixtures/
└── task-graph-v1.json

docs/architecture/
├── FACTORY_ASSET_LEVEL_UP_ADR_V1.md
└── FACTORY_ASSET_PROVIDER_BOUNDARY_V1.md

docs/operations/
├── FACTORY_ASSET_LEVEL_UP_PRD_V1.md
└── FACTORY_ASSET_ATOMIC_TASKS_V1.md
```

Implementation language is subordinate to the contract. A practical v0.1 is a deterministic Python worker for raster/PDF/vector CLI orchestration, invoked by the existing OS-neutral operator through a versioned job/receipt schema. The canonical state and orchestration authority remain in the existing DIE runtime.

## 13. Rollout recommendation

1. Activate one dedicated Chat-mode hourly scheduled task with a first-run gate limited to FA-000, using isolated worktrees and both Factory/global repository leases.
2. Canonize this revised PRD, ADR set, and Factory Asset task graph without runtime mutation; only after that merge may the schedule select normal `LINUX_HOURLY_BUILD` leaves.
3. In Linux isolation, inventory the five current artifacts read-only, freeze Asset Blueprint v2 and marketplace profiles, then build and accept Asset Derivative Engine v0.1.
4. Continue into native vector, marketplace packaging, Factory Core, and later procedural/motion/layered/3D producer tasks only as dependencies open.
5. In parallel on Windows, preserve text/chat regression, harden Qwen, and prove ChatGPT, Gemini, Grok, Manus, and Duck.ai original-byte image export one provider at a time.
6. Do not integrate Windows provider code into Linux until clean extraction, policy evidence, contracts, and the relevant Linux acceptance gates pass.
7. Begin GenWHITE observable-capability parity research only after the Windows provider proof matrix reaches its Founder-approved exit state.
8. Progress through throughput unlocks only after both lanes converge behind Factory Core contracts.

The fastest useful vertical slice is therefore:

```text
5 existing PNG masters
       ↓
Blueprint/recipe reconstruction
       ↓
JPEG + WebP + TIFF + PDF
       ↓
hash/QA/compatibility receipts
       ↓
marketplace-ready dry-run packages
       ↓
PASS
```

That slice creates immediate leverage for the artifacts Hermes is already producing while the slower provider-fleet research continues behind a stable interface.
