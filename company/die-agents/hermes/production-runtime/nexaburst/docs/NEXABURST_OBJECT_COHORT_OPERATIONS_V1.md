# NexaBurst Object Cohort Operations V1

## Purpose

This runbook controls deterministic 500-item Object Atlas cohorts for object-centric lanes such as WC-L0 and PSR-L0.

The authoritative selector is `bin/nexaburst-object-cohort-plan.py`.

The old `nexaburst-roundrobin-next.py --skip N` helper is preview-only and must not be used for future production cohorts.

## Selection doctrine

Each cohort is recomputed from current durable manifestation coverage:

1. Load the semantic presence map (exact WordNet sense-set identity; lexical fallback only when WordNet is absent).
2. Read the target lane's manifestation ledger.
3. Treat `RAW_DONE`, `WAITING_FOUNDER_QC`, and `VAULT_VERIFIED` semantic concepts as covered.
4. Exclude covered concepts.
5. Select up to 500 remaining representatives using simple A->Z round-robin.
6. Require unique candidate IDs and unique semantic keys.
7. Emit `PREPARED_NOT_AUTHORIZED` plan + SHA-256.

Do **not** precompute cohort #3, #4, ... from static offsets. Recompute only after the previous authorized cohort reaches its boundary so durable coverage is incorporated automatically.

## WC-L0 next cohort

Example after the current cohort is complete:

```bash
RT=/home/kopiko/die-sessions/NEXABURST-H01-P001
$RT/bin/nexaburst-object-cohort-plan.py \
  --lane WC-L0 \
  --cohort-id WC-C0002 \
  --count 500 \
  --ledger /var/lib/die/h01/nexaburst/state/nexaburst-manifestation-ledger.db \
  --out $RT/config/cohorts/WC-C0002.jsonl \
  --summary-out /var/lib/die/h01/nexaburst/state/cohorts/WC-C0002.summary.json
```

A new Founder authorization is required before a prepared plan may be dispatched.

## PSR-L0 cohorts

PSR uses the **same semantic universe and same A->Z round-robin selector** as WC, but its coverage ledger and expression identity are independent.

Example:

```bash
$RT/bin/nexaburst-object-cohort-plan.py \
  --lane PSR-L0 \
  --cohort-id PSR-C0001 \
  --count 500 \
  --ledger /var/lib/die/h01/nexaburst-lane2-psr/state/nexaburst-manifestation-ledger.db \
  --out $RT/config/cohorts/PSR-C0001.jsonl \
  --summary-out /var/lib/die/h01/nexaburst-lane2-psr/state/cohorts/PSR-C0001.summary.json
```

If the PSR ledger does not yet exist, coverage is zero and the planner starts from the full semantic universe.

## OpenCode handoff

OpenCode may prepare the next cohort **only after** confirming:

- previous authorized cohort reached its raw boundary;
- no active provider job belongs to that cohort;
- target lane control is PAUSED;
- semantic-map SHA is readable;
- current ledger is readable;
- generated cohort reports 500/500 unique candidate IDs and semantic keys (or fewer only when the universe is nearly exhausted).

OpenCode must not invent static `skip` values, mutate prior cohort files, arm a cohort, or resume production without Founder authorization.

Required report:

- lane_id
- cohort_id
- semantic_universe
- covered_semantic_keys
- remaining_before_selection
- selected
- semantic_unique
- candidate_unique
- bucket_counts
- output SHA-256
- activation state

## End-of-universe behavior

When fewer than 500 uncovered concepts remain, the final cohort contains only the remaining concepts. When none remain, `selected=0`; the lane is semantically exhausted.
