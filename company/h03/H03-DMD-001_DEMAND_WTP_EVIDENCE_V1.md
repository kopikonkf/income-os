# H03-DMD-001 — Demand + Willingness-to-Pay Evidence v1

Status: DONE / PASS
Date: 2026-09-09

Demand/WTP evidence is typed rather than blended into a generic popularity score. Revealed spend is strongest; paid substitutes and marketplace-sale proxies are medium; purchase-intent search and repeated pain are weak WTP evidence. Engagement-only signals never establish WTP and therefore keep WTP `UNKNOWN`. Explicit money is required for `REVEALED_SPEND`.

Artifacts: `company/h03/contracts/demand-wtp-evidence.v1.schema.json` and `company/h03/lib/demand_wtp.py`.
