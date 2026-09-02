# Factory Asset Level Up — Architecture Decision Record Set v1

**Date:** 2026-09-02
**Status:** CANONICAL v1.1
**Scope:** Asset Blueprint v2, Asset Derivative Engine, Factory Asset Core
**Authority:** Founder retains spend, account, credential, publication, policy-exception, and irreversible-cutover authority.

## Decision index

| ADR | Decision | Status |
| --- | --- | --- |
| FA-ADR-001 | Separate semantic assets from packaging derivatives | ACCEPTED |
| FA-ADR-002 | Select native representation before provider dispatch | ACCEPTED |
| FA-ADR-003 | Make canonical masters immutable and content-addressed | ACCEPTED |
| FA-ADR-004 | Keep Asset Derivative Engine v1 deterministic and LLM-free | ACCEPTED |
| FA-ADR-005 | Prefer native vector production; gate raster tracing | ACCEPTED |
| FA-ADR-006 | Make Factory Core provider-neutral | ACCEPTED |
| FA-ADR-007 | Treat `D:\OAUTH` as a laboratory, not a production dependency | ACCEPTED |
| FA-ADR-008 | Treat free-web capacity as observed evidence, never a fixed entitlement | ACCEPTED |
| FA-ADR-009 | Isolate every provider account and cap browser tabs | ACCEPTED |
| FA-ADR-010 | Scale through quality/economic unlocks, not raw file count | ACCEPTED |
| FA-ADR-011 | Preserve DIE State Manager as the sole canonical writer | ACCEPTED |
| FA-ADR-012 | Use GenWHITE as a benchmark, not a backend assumption or dependency | ACCEPTED |
| FA-ADR-013 | Maintain a separate Factory Asset task graph with a global repo-write lease | ACCEPTED |
| FA-ADR-014 | Split Linux isolated engine builds from Windows OAUTH provider proofs | ACCEPTED |
| FA-ADR-015 | Protect the live Linux Production Organism from scheduled engineering | ACCEPTED |
| FA-ADR-016 | Classify provider transports before choosing browser architecture | ACCEPTED |
| FA-ADR-017 | Require original-byte proof for six Windows image-provider targets before GenWHITE parity work | ACCEPTED |

---

## FA-ADR-001 — Separate semantic assets from packaging derivatives

### Context

One PNG can be exported to JPEG, WebP, TIFF, and PDF. Those files may serve different delivery constraints but do not represent four distinct commercial works. In contrast, a photo, outline icon, repeating pattern, and animation of the same noun have distinct utility and should have distinct blueprints and identities.

### Decision

Use two identity layers:

- `semantic_asset_id` identifies a commercially distinct work.
- `derivative_id` identifies a deterministic representation/package of one master.

All format, compression, resolution, preview, and marketplace packaging derivatives set `counts_as_distinct_asset=false`.

### Consequences

- Portfolio and revenue metrics cannot be inflated by format copies.
- Marketplace duplicate/spam controls become enforceable.
- “One generation → five files” is reported as one semantic asset and five packaging outputs.
- New variants require a distinct commercial use case, blueprint, and quality evaluation.

### Rejected alternative

Treat every output file as an asset. Rejected because it corrupts economics, distinctness, and marketplace risk controls.

---

## FA-ADR-002 — Select native representation before provider dispatch

### Context

The current raster engine outputs PNG. A universal PNG master cannot preserve editable vector paths, layered templates, motion timelines, or 3D geometry.

### Decision

`Asset Blueprint v2` must declare:

- `asset_type`;
- `native_representation`;
- `producer_class`;
- canonical master specification;
- delivery recipes and marketplace targets.

Raster opportunities may use a PNG source master even when the final delivery format is JPEG. Vector, motion, procedural, layered, and 3D opportunities must route to native producers.

### Consequences

- ChatGPT/Qwen remain valid raster providers but are not universal producers.
- Future vector, Remotion, template, and 3D engines plug into the same blueprint boundary.
- Impossible format/producer combinations fail before cost or quota is consumed.

### Rejected alternative

Generate every opportunity as PNG and convert afterward. Rejected because conversion cannot recover missing semantic structure.

---

## FA-ADR-003 — Make canonical masters immutable and content-addressed

### Context

The `D:\ASSETS\OAUTH` audit found eleven files but only nine unique SHA-256 values. Identical bytes were saved under different paths. Filename-based identity therefore permits duplicate ingestion and false throughput.

### Decision

- The accepted provider output becomes an immutable canonical master.
- Master identity and deduplication use SHA-256 plus the semantic/job lineage contract.
- No worker overwrites a master.
- Derivative keys include master hash, recipe/version, and marketplace-profile version.
- Duplicate provider output creates a new attempt receipt but reuses the canonical content record.

### Consequences

- Retries, restarts, and provider duplicates are safe.
- Regeneration and audit are reproducible.
- Storage and metrics reflect unique content.

### Rejected alternative

Use path, filename, timestamp, or provider URL as identity. Rejected because those values are mutable and do not prove content equality.

---

## FA-ADR-004 — Keep Asset Derivative Engine v1 deterministic and LLM-free

### Context

Raster conversion and packaging are mechanical transformations. Calling an LLM or image model again increases cost, latency, variability, and rights/lineage complexity.

### Decision

Asset Derivative Engine v1 uses deterministic local tools and pinned recipes for:

- JPEG/WebP/TIFF/PDF exports;
- resizing and previews;
- alpha flattening;
- color/ICC/DPI rules;
- metadata attachment;
- decode/reopen, magic-byte, dimensions, size, and hash validation;
- native vector normalization/export and gated tracing.

A practical implementation is a Python worker plus pinned libraries/CLI tools behind a versioned job/receipt contract. No architectural authority is assigned to Python itself; the contract remains portable.

### Consequences

- Outputs are reproducible and cheap.
- Provider quota is reserved for generative work.
- Every recipe can be regression-tested.
- System dependencies such as vector exporters must be version-pinned and included in evidence.

### Rejected alternative

Ask ChatGPT/Qwen to regenerate each requested format. Rejected because it creates new content, not a deterministic derivative.

---

## FA-ADR-005 — Prefer native vector production; gate raster tracing

### Context

Photorealistic raster tracing can create huge, ugly, non-editable path collections. Some exporters can also wrap a bitmap inside SVG/EPS without creating a real vector asset.

### Decision

- Icons, outlines, flat illustrations, and procedural patterns use native vector producers by default.
- Raster tracing is a fallback only for blueprint classes explicitly marked `TRACE_FALLBACK_ALLOWED`.
- The gate checks visual complexity, color count, edge structure, alpha, expected path count, file size, and commercial editability.
- SVG/EPS QA rejects embedded-only raster, excessive paths, missing fonts, invalid bounds, and preview mismatch.
- Photorealistic assets deterministically return `NOT_VECTORIZABLE`.

### Consequences

- Vector listings remain genuinely editable.
- Trace fallback can salvage simple silhouettes and line art without corrupting the vector lane.
- A rejected trace is a correct outcome, not a pipeline failure.

### Rejected alternative

Always trace every PNG or merely rename/wrap it as SVG/EPS. Rejected as technically invalid and commercially misleading.

---

## FA-ADR-006 — Make Factory Core provider-neutral

### Context

ChatGPT web output is currently the production provider, while Qwen has passed a separate Windows experiment. Gemini, Grok, and Manus remain incomplete. Provider protocols and capacity can change without notice.

### Decision

Factory Core owns:

- provider capability registry;
- profile/account leases;
- capacity ledger;
- deterministic routing;
- queue, retry, resume, and reconciliation;
- normalized master ingestion;
- sanitized observability.

Each provider owns only authentication/session integration, request translation, output acquisition, health, and typed errors. Factory Core never contains vendor wire formats.

### Consequences

- ChatGPT becomes provider lane #1, not the definition of the Factory.
- Qwen or future official/owned-capacity providers can be added without changing asset identity or orchestration.
- Provider drift is isolated.

### Rejected alternative

Build a separate end-to-end factory around each provider. Rejected because it duplicates governance, lineage, QA, and storage logic.

---

## FA-ADR-007 — Treat `D:\OAUTH` as a laboratory, not a production dependency

### Context

`D:\OAUTH` contains valuable live-proven work but also extensive uncommitted experiments, raw captures, session-oriented code, empty canonical tests, hard-coded Windows asset paths, and an inline credential in the local Git remote.

### Decision

- Perform a KEEP/EXTRACT/REWRITE/RETIRE provenance autopsy.
- Extract the smallest reusable Qwen logic into a clean provider package through the Factory provider contract.
- Do not copy credentials, session dumps, raw HAR files, logs, or unrelated chat/tool-emulation code.
- Add unit, parser, fixture, negative, and bounded live-canary tests before promotion.
- Run separate authorized credential hygiene to remove inline Git authentication and rotate the affected credential.

### Consequences

- Proven work is reused without importing experimental debt.
- Windows remains a reference/probe environment; Linux becomes the production target after canary.
- Security remediation is explicit and auditable.

### Rejected alternative

Point Linux Factory Core directly at `D:\OAUTH:8456` or copy the directory. Rejected because it creates a hidden Windows dependency and imports ungoverned state.

---

## FA-ADR-008 — Treat free-web capacity as observed evidence, never a fixed entitlement

### Context

Qwen, Gemini, Manus, Grok, and ChatGPT free-web limits can be unpublished, dynamic, account-specific, region-specific, or policy-dependent. A single successful generation does not prove daily capacity.

### Decision

- Every provider profile begins with `capacity_state=UNKNOWN`.
- Capacity becomes available only through dated, bounded, policy-compatible observations.
- Rate-limit, auth, protection, and restriction events are durable typed evidence.
- The router never assumes “20/day,” extrapolates one run, or treats theoretical request latency as entitlement.
- No account creation, CAPTCHA bypass, fake identity, quota evasion, or rate-limit circumvention is part of the architecture.
- Official APIs or owned compute become the preferred scale substrate when 500+/day is economically justified and Founder-authorized.

### Consequences

- Throughput claims remain honest.
- The system degrades safely when free capacity changes.
- 1K–5K/day remains a future gate, not an initial SLO.

### Rejected alternative

Encode guessed free-tier limits and add accounts until the target is reached. Rejected for instability, policy risk, operational fragility, and false economics.

---

## FA-ADR-009 — Isolate every provider principal and cap browser tabs

### Context

Prior MUXIA work proved that profiles, leases, crash recovery, and browser resource bounds matter. Unbounded browser tabs waste RAM and increase session contamination risk.

### Decision

- One provider account remains one logical principal with at most one active job lease.
- One Founder-owned identity bundle may use one browser profile to hold authenticated sessions for different provider domains under the same email identity, but each provider principal retains separate credentials, capability, capacity, policy evidence, health and lease state.
- Extracted credentials/session material never cross provider principals or identity bundles.
- Browser lanes allow at most two open tabs per principal: work and auth/recovery.
- Direct supported transport is preferred where policy-compatible; CDP/browser use is limited to providers that require it.
- A `SESSION_API` provider such as the current Qwen prototype does not require a continuously running browser; the browser is an authentication/refresh capsule.
- Crash recovery reconciles owned processes and leases before reuse.
- Authentication and protection challenges require human recovery and block the lane.

### Consequences

- Multi-profile means an isolated governed fleet, not shared cookies, guessed entitlement, or uncontrolled tabs.
- Resource planning becomes measurable.
- Provider lanes can be quarantined independently.

### Rejected alternative

Treat one browser profile as one pooled credential blob, share cookies between providers/accounts, or open unlimited tabs. Rejected because ownership, security, and reproducibility fail.

---

## FA-ADR-010 — Scale through quality/economic unlocks, not raw file count

### Context

A factory can generate files faster than QA, submission, marketplace review, and demand can absorb them. Format derivatives and rejected near-duplicates can create misleading volume.

### Decision

Use staged unlocks:

1. deterministic/synthetic correctness;
2. five-master derivative canary;
3. 20–50 masters/day stability;
4. 100 masters/day downstream QA/distinctness proof;
5. 500/day only with verified capacity and economics;
6. 1K/day only with acceptance/revenue evidence and Founder approval;
7. 5K/day only after a separate market-absorption and infrastructure decision.

Metrics separately report attempts, unique masters, QA-passed semantic assets, packaging derivatives, marketplace-ready packages, submissions, acceptances, licenses, and revenue.

### Consequences

- The Factory optimizes for accepted commercial assets and profit, not vanity volume.
- Scale cannot be unlocked by generating extra formats.
- QA/QC and marketplace learning remain part of capacity planning.

### Rejected alternative

Set 5,000 generated files/day as the first success metric. Rejected because it ignores value, quality, compliance, and downstream constraints.

---

## FA-ADR-011 — Preserve DIE State Manager as the sole canonical writer

### Context

Hermes, workers, provider adapters, derivative tools, QA, and scheduled Architect runs can all produce evidence. Multiple canonical writers would create split-brain state.

### Decision

- Workers and providers write job-local artifacts and receipts only.
- Hermes orchestrates but is not canonical truth.
- Factory Core proposes normalized events/receipts.
- DIE State Manager validates and commits canonical asset, derivative, capacity, QA, and economics state.
- “Done” without durable evidence is blocked.

### Consequences

- Existing governance and replay properties remain intact.
- New engines do not gain authority by being added to the pipeline.
- Scheduled execution can be idempotent and audited.

### Rejected alternative

Allow each engine to update a shared database directly. Rejected because authority and reconciliation become ambiguous.

---

## FA-ADR-012 — Use GenWHITE as a benchmark, not a backend assumption or dependency

### Context

The available product snapshot suggests server-side Gemini generation, Auto-Pilot, batching, presets, automatic download, and high-volume claims. It does not prove backend implementation, quota source, unit economics, or policy posture.

### Decision

Use GenWHITE to benchmark product features:

- batch input and preset management;
- queue progress;
- pause/resume;
- retry and rate-limit visibility;
- automatic download;
- output dashboard;
- style consistency controls.

Do not copy, reverse-engineer, purchase, or depend on it as a prerequisite for v1. Do not infer API farming or local-model use without evidence.

### Consequences

- Useful product ideas are retained.
- Factory architecture remains evidence-based and independent.
- Purchase remains a future Founder decision if a bounded benchmark shows positive economics.

### Rejected alternative

Reverse-engineer GenWHITE before building the derivative vertical slice. Rejected because it delays immediate leverage from existing Linux masters.

---

## FA-ADR-013 — Maintain a separate Factory Asset task graph with a global repo-write lease

### Context

The existing `company/muxia-task-graph-v1.json` already governs Chapter #4 and currently has its own READY frontier. Mixing a long Factory Asset roadmap into product-specific MUXIA nodes would blur ownership and allow scheduled runs to preempt unrelated work.

### Decision

- Create `company/factory-asset/task-graph-v1.json` as the Factory Asset SSOT after canon approval.
- Scheduled Factory Asset runs read `origin/main`, the Factory graph, relevant receipts, `LASTSTANDINGPOINT.md`, and active leases.
- Each run executes exactly one highest-priority READY atomic leaf or one explicitly declared tightly coupled acceptance batch, then stops.
- A global `income-os:repo-write` lease prevents concurrent scheduled repository writes across Chapter #4 and Factory Asset schedules.
- Factory Asset automation is not activated until the canon pack is published and the scheduling scope is explicit.

### Consequences

- Both roadmaps remain auditable.
- Existing `SUB-001C`/Chapter #4 work is not silently displaced.
- Parallel schedules can coexist only when leases and product scopes make the work safe.

### Rejected alternative

Append all Factory tasks directly to the MUXIA graph or let schedules select work from chat memory. Rejected because product scope and canonical priority would become ambiguous.

---

## FA-ADR-014 — Split Linux isolated engine builds from Windows OAUTH provider proofs

### Context

The live Linux Production Organism now generates governed artifacts every three hours. Factory Asset engine development can progress independently, while `D:\OAUTH` contains Windows-specific experimental provider code, sessions, HAR evidence and a working text/chat path that must not be destabilized.

### Decision

- `LINUX_HOURLY_BUILD` executes exactly one eligible Linux-build leaf per hourly scheduled run in a fresh isolated worktree/check-out.
- The scheduled task is created in Chat mode at minute `35` UTC. Before the graph is canonical, its only permitted bootstrap action is FA-000; it must stop after canon publication and may select normal Linux leaves only on later runs.
- `WINDOWS_OAUTH_LAB` is a separate Founder-directed interactive lane for provider autopsy, adapter repair and bounded live image proofs.
- Windows OAUTH tasks are never selected by the autonomous Linux scheduled task.
- The two lanes converge only through versioned provider/master/receipt contracts and governed clean extraction.

### Consequences

- Deterministic engine work progresses hourly without coupling to Windows authentication work.
- Provider debugging cannot accidentally mutate the Linux production runtime.
- Windows experiments do not become canonical merely because a live test passes.

### Rejected alternative

Use one scheduler and one mutable checkout for both Linux engine builds and Windows provider debugging. Rejected because environment, authority, credentials and failure modes differ.

---

## FA-ADR-015 — Protect the live Linux Production Organism from scheduled engineering

### Context

`die-production-cycle-v1` is active at `0 */3 * * *` and should continue producing one bounded artifact cycle every three hours while Factory Asset is developed.

### Decision

- Scheduled engineering may read production evidence only when a task explicitly requires read-only inventory or verification.
- It must never edit the live `/srv/die` checkout, active artifact directories, databases, profiles, credentials, queues, cron definitions or service configuration.
- It must not deploy, restart, stop, reconfigure or cut over any production service.
- Repository mutations require the Factory lease plus the global `income-os:repo-write` lease and occur only from a fresh isolated worktree based on current `origin/main`.
- Each hourly run stops after one atomic leaf or declared acceptance batch.

### Consequences

- Production observation and engineering can proceed in parallel.
- A bad build cannot become a live runtime change merely because tests passed.
- Promotion remains a separate Founder-governed action.

### Rejected alternative

Build directly inside the live production checkout or automatically deploy after every hourly task. Rejected because it violates the monitoring window and creates uncontrolled production risk.

---

## FA-ADR-016 — Classify provider transports before choosing browser architecture

### Context

Direct inspection of `D:\OAUTH\src\providers\qwen_image.py` proves Qwen uses browser-session cookies with direct HTTP/SSE generation. It does not drive the visible UI per generation. Other providers may require a different mechanism.

### Decision

Every provider receives one evidenced transport classification:

- `SESSION_API`: browser only establishes/refreshes authentication; generation uses a supported session transport.
- `BROWSER_CDP`: generation requires an authenticated browser page and CDP/DOM/network automation.
- `HYBRID`: browser authentication or acquisition plus direct generation/polling transport.
- `OFFICIAL_API`: documented provider API.
- `UNSUPPORTED`: native image generation or allowed automation route is absent.
- `UNKNOWN`: evidence is incomplete.

Factory Core dispatches through the common image contract; it does not force every provider into a browser or Qwen-style internal endpoint.

### Consequences

- Browser resource forecasts reflect actual provider needs.
- Qwen can remain lightweight while ChatGPT/other lanes use different adapters.
- Provider drift returns a typed failure instead of triggering endpoint guessing.

### Rejected alternative

Assume one web-chat account always needs one permanently running GUI browser, or assume every service exposes a Qwen-like session endpoint. Both assumptions are disproven or unevidenced.

---

## FA-ADR-017 — Require original-byte proof for six Windows image-provider targets before GenWHITE parity work

### Context

Founder selected Qwen, ChatGPT, Gemini, Grok, Manus and Duck.ai as the Windows proof matrix. Qwen is currently the only live success. Duck.ai's current adapter calls a text endpoint and explicitly describes native image generation as hypothesis/non-existent.

### Decision

- A provider passes only after prompt submission, real image generation, original-byte automatic local save, decode/reopen, magic/MIME, dimensions, bytes and SHA-256 evidence.
- Screenshot, URL-only, HTTP 200, textual completion, guessed endpoint, or swallowed download failure cannot pass.
- Qwen is hardened as the `SESSION_API` reference.
- ChatGPT uses a Proxima/MUXIA behavioral comparison without importing Electron wholesale.
- Gemini, Grok, Manus and Duck.ai are investigated one at a time and fail closed.
- `UNSUPPORTED_CAPABILITY` is an honest terminal research result. It blocks the six-provider PASS claim until Founder chooses substitution, deferral or removal.
- GenWHITE work is limited to observable capability-parity research and starts only after Founder accepts the provider proof matrix exit state.

### Consequences

- “Provider supported” always means a durable real image, not merely a responsive chat endpoint.
- Duck.ai cannot be counted unless its native image path is actually evidenced.
- Later Factory integration starts from clean provider evidence.

### Rejected alternative

Count text models, screenshots, inaccessible URLs, or speculative provider routes as working image engines. Rejected because it creates false factory capacity.

---

## Ratification conditions

This ADR set becomes canonical only when:

1. Founder accepts or amends the decisions.
2. The PRD, ADR set, and task graph are published to `origin/main` through the governed repository workflow.
3. Cross-reference and JSON/schema validation pass.
4. No production runtime, credentials, provider accounts, marketplace submissions, or current Chapter #4 statuses are mutated as part of the canon-only change.
