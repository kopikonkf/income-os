# DIE H01 Daily Standalone SVG Selector v1

Status: pre-scale runtime implementation
Date: 2026-09-14

## Purpose

The daily selector converts the immutable H01-101 standalone SVG queue into a bounded daily production manifest without mutating Object Atlas or making market evidence a production dependency.

```text
H01-101 queue (43,005)
        +
terminal GENERATION_COMPLETE receipts
        +
optional H01-130 demand records
        +
optional H01-131 connector evidence
        +
optional H01-132 Human Atlas context
        ↓
H01-133 deterministic prioritization
        ↓
h01_daily_selector.py
        ↓
daily production manifest
```

## Produced truth

A queue item is excluded from future selection only when a `generation-complete.receipt.json` records `GENERATION_COMPLETE` and `h01_103_status=PASS`. Rights, Founder QC and submission state do not participate in produced detection.

Therefore a master that later receives `REVIEW_REQUIRED` or `BLOCKED_RIGHTS` remains generated and is not sent back to Web-AI merely to chase a different rights outcome.

## Ranking

The selector reuses H01-133 exactly. H01-133 currently weights accepted evidence as:

- demand: 60%;
- competition opportunity: 25%;
- demand confidence: 15%.

Items with usable evidence are emitted first in H01-133 priority order. Items with no usable market evidence remain production-valid and follow in original H01-101 source order.

Human Atlas context is carried as bounded annotation. It has no independent rank authority in selector v1.

## Non-blocking evidence policy

Demand/connector files are optional runtime inputs. Missing files, missing Google Ads authentication, connector outage, stale evidence or zero evidence must not stop the daily standalone production lane. The deterministic fallback is H01-101 source order after already-generated queue IDs are removed.

This implementation does not claim a live external market-evidence refresh daemon. H01-131 remains the accepted connector/normalizer contract; selector v1 consumes evidence when available and degrades honestly when it is absent.

## Provider plan

A daily manifest carries a deterministic provider cycle for compatibility with the current generation runner. Runtime scheduler readiness remains authoritative at dispatch time, and the existing bounded wrong-modality redistribution policy may select one alternate READY provider when permitted. Provider assignment does not change noun identity or ranking.

## Authority

Selector output is a production proposal/manifest, not a provider dispatch capability. It grants no marketplace submission, publication, credential, or spend authority.
