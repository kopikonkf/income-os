# H03-SCALE-001 — Bounded Multi-Product Throughput + Resilience Soak v1

Status: DONE / PASS
Date: 2026-09-09

This soak is intentionally non-live and capacity-sized. Observed fixture capacity is 6 producer slots and each scale product uses 2 section jobs, therefore safe batch size is `floor(6/2) = 3 products`.

Products compiled locally:
- guide
- checklist
- reference sheet

Metrics from the acceptance run:
- product count: 3
- worker jobs: 6
- throughput: 6.724582 products/sec
- queue latency mean: 1.328267 ms
- terminal failure rate: 0.0
- retry count: 1
- fallback success count: 1
- peak traced memory: 5592839 bytes

The soak deliberately injects one `RATE_LIMITED` event on `fixture-producer-a`; RT-005 selects `FALLBACK_ALTERNATE_WORKER`, the job succeeds on `fixture-producer-b`, and terminal failure rate remains zero. Queue depth equals the six-slot limit, so explicit `PAUSE_NEW_DISPATCH` backpressure is observed instead of overcommit.

No live provider capacity or throughput claim is made. `execution_mode=NONLIVE_ROLE_FIXTURE`; no external publication occurs.

Artifact: `company/h03/evidence/H03-SCALE-001/scale-soak-report.json`.
