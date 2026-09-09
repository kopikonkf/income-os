# H03-ORG-001 - Bounded End-to-End Problem-to-Package Internal Canary v1

Status: DONE / PASS
Date: 2026-09-09

## Canary problem

A privacy-conscious consumer wants a repeatable DIY workflow for reducing exposed personal information on people-search sites without delegating the whole job to a paid removal service.

The canary deliberately separates **real external evidence** from **non-live role execution fixtures**:

- Market/knowledge source bytes are real public pages captured on 2026-09-09 and retained with SHA256 lineage.
- Browser/CDP workforce preflight was not performed.
- Curator/researcher/synthesizer/producer cognition is represented by explicit `NONLIVE_ROLE_FIXTURE` workers routed through the same Work Card/provider-pool contracts.
- No live Qwen, Gemini, Manus, Claude, ChatGPT or other provider call is claimed.

## Lifecycle proved

```text
real problem candidate
  -> SEED_CURATOR Work Card + curated seed batch
  -> cheap governed opportunity evidence
  -> Demand/WTP = MEDIUM
  -> Worth-Making = MAKE
  -> bounded Research Plan
  -> 3-way routed research fan-out
  -> governed research packets
  -> research stop
  -> SYNTHESIZER Work Card
  -> Knowledge Map + Knowledge Package Candidate
  -> governed Knowledge Package
  -> Useful Product Planner -> guide
  -> 5 section PRODUCER jobs across 2 fixture workers
  -> evidence-bound content blocks
  -> deterministic Document AST
  -> PDF render + reopen/raster QA
  -> manifest + deterministic ZIP
  -> LOCAL_SALE_READY_UNREVIEWED package
```

The expensive research plan is materialized only **after** the Demand/WTP + Worth-Making gate returns `MAKE`.

## Evidence separation

Market evidence comes from current paid-removal-service pages and is used only for Demand/WTP / market findings. The sale-ready product knowledge packet uses the governed FTC Consumer Advice source only. Tests assert that Incogni/DeleteMe source URIs do not leak into the accepted product Knowledge Package.

All external sources are `REVIEWED_REFERENCE_ONLY`; verbatim commercial reuse is false.

## Runtime fixtures

Research routing acceptance:

```text
Q-MARKET-1   -> fixture-market-a
Q-OFFICIAL-1 -> fixture-knowledge-a
Q-MARKET-2   -> fixture-market-b
```

Producer routing acceptance:

```text
SEC-001 -> fixture-producer-a
SEC-002 -> fixture-producer-a
SEC-003 -> fixture-producer-a
SEC-004 -> fixture-producer-b
SEC-005 -> fixture-producer-b
```

This proves role separation, slot accounting and multi-worker fan-out without requiring browser accounts to be provisioned first.

## Canary product

- Product: `DIY People-Search Opt-Out Guide`
- Product ID: `H03-PROD-ORG001-001`
- Form: `guide`
- Package state: `LOCAL_SALE_READY_UNREVIEWED`
- Pages: 2
- PDF SHA256: `9387de9c840a9aa2f5b77a72ffc48f0d78b8936b90e012d0707309f871c99c19`
- ZIP SHA256: `c93b149bfe139c9fe10a2dd662427720afad57ba6523d373c7d7c8e550b1fb8a`
- External publication: false
- Paid ads: false
- Founder publication gate crossed: false

## Failure discovered and remediated

The first canary run exposed a real bug: `research_executor` parsed hyphenated question IDs with `rsplit('-', 1)`, so `Q-MARKET-1` became `1`. The executor now strips an exact Work Card plan prefix and preserves the full question ID. A dedicated regression covers hyphenated IDs.

The canary also exercised producer capacity enforcement: an initial 4-slot fixture pool refused a 5-section product with `NO_ELIGIBLE_WORKER_SLOT`. The bounded fixture capacity was corrected to five slots; the router/backpressure behavior was not bypassed.

## Reproducibility

The full canary can be rerun offline from the committed source snapshots. Two independent temporary build roots produce identical PDF and ZIP hashes.

Validation:

- Canary + research executor targeted tests: `9/9 PASS`
- Full H03 regression: `119/119 PASS`
- Live provider call claimed: false
- External publication: false

Artifacts:

- `company/h03/lib/org_canary.py`
- `company/h03/tests/test_org_canary.py`
- `company/h03/evidence/H03-ORG-001/`
