# DIE H01 Market Signal Acquisition Core v1

Task: H01-131A

## Purpose

H01-131A turns the H01-131 connector contracts into a reusable acquisition substrate for first-party demand sources. It deliberately does **not** encode source-specific Shutterstock/Pond5/Vecteezy/Freepik/123RF/Adobe parsing. Those adapters are separate atomic tasks and plug into this core.

The core owns only shared invariants:

```text
source capability
  -> HTTPS/domain guard
  -> no credential/cookie header access
  -> source lease + persistent minimum interval
  -> bounded request budget / response size
  -> immutable raw snapshot
  -> source-specific normalizer
  -> immutable normalized evidence
  -> acquisition receipt
  -> fresh cache / stale-cache fallback
```

A source outage never invalidates Object Atlas, never blocks standalone production, and never grants production/submission/publication/spend authority.

## Per-source capability registry

Capabilities live as one JSON file per source under:

`company/company-os/die-h01/runtime/market-signal-sources/`

This layout is intentional: H01-131B..H01-131H can be implemented in parallel sessions with low merge-conflict risk. Each adapter owns its own capability file and source-specific code/tests rather than editing one giant registry.

The capability contract records:

- source identity and first-party status;
- adapter state (`ACTIVE`, `ADAPTER_PENDING`, `AUTH_CONTEXT_REQUIRED`, `DISABLED`);
- public HTTPS vs authorized external-import acquisition mode;
- allowed first-party hosts;
- supported signal classes;
- request budget and persistent minimum interval;
- cache TTL and maximum response bytes;
- accepted content types;
- commercial-intent evidence tier;
- fail-soft production policy and zero action authority.

The initial ACTIVE proof source is Wikimedia Analytics. Google Ads remains `AUTH_CONTEXT_REQUIRED`; H01-131A does not provision, read, export, or synthesize Google credentials.

## Security boundary

Public HTTP acquisition accepts only GET over HTTPS to the capability's allowlisted first-party host. Redirects are rechecked. Request headers named `Authorization`, `Cookie`, `Proxy-Authorization`, `X-API-Key`, or `X-Goog-Api-Key` are rejected before network I/O.

Source/layout/content-type/transport failures degrade to no evidence or stale cached evidence. Policy violations such as off-host URLs, secret-bearing requests, immutable hash collisions, malformed normalizer output, or request-budget violations fail closed as implementation errors.

## Persistent runtime state

Canonical Linux state root:

`/var/lib/die/h01/demand-intelligence/signals`

Per source/query layout:

```text
sources/<source_id>/
  source.lock
  source-state.json
  queries/<query_hash>/
    latest-success.json
    raw/<raw_sha256>.bin
    evidence/<evidence_id>.json
    acquisitions/<acquisition_id>.json
```

Raw payloads and normalized evidence are immutable/hash-addressed. `latest-success.json` is only a mutable pointer to the latest proven data snapshot; failed refreshes do not overwrite it.

## Cache/freshness semantics

- valid cached snapshot inside TTL -> `CACHE_HIT_FRESH`, no source request;
- stale cache + successful refresh -> new immutable `ACQUIRED` snapshot;
- stale cache + source failure -> `DEGRADED_STALE_CACHE`, effective freshness `STALE`;
- no cache + source failure -> `DEGRADED_NO_EVIDENCE`;
- source lease busy -> `DEGRADED_SOURCE_BUSY`;
- missing authorized context -> `DEGRADED_AUTH_REQUIRED`;
- adapter not operational -> `DEGRADED_ADAPTER_UNAVAILABLE`.

These are evidence states, not production states.

## Parallel source-adapter contract

H01-131B..H01-131H may run in separate Architect sessions after this core is merged. Every adapter must:

1. add/own a source capability file or transition its own existing capability;
2. construct only bounded first-party requests/imports;
3. parse source-specific raw data into deterministic H01-131 evidence;
4. route acquisition/persistence/cache/freshness through this core;
5. prove source failure is non-blocking;
6. never read credentials unless a later task explicitly grants an authorized external context;
7. never add marketplace upload/submission/publication/spend behavior.

## Baseline proof

A live first-party Wikimedia acquisition for `Cat`, seven complete UTC days ending 2026-09-13, produced one immutable raw snapshot and one normalized TREND evidence record. The evidence covered 7 periods with 80,887 pageviews total. Immediate replay returned `CACHE_HIT_FRESH` and reused the same raw/evidence hashes.
