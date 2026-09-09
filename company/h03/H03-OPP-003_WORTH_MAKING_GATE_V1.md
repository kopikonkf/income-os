# H03-OPP-003 — Worth-Making + Productability Gate v1

Status: DONE / PASS
Date: 2026-09-09

The gate emits `MAKE`, `RESEARCH_MORE`, or `REJECT` without an opaque composite score. `MAKE` requires evidenced medium/strong WTP, medium/strong buyer intent, and medium/high productability. Unknowns route to `RESEARCH_MORE`; low productability or clearly low commercial pressure can `REJECT`. Evidence refs are carried into the decision.

Artifacts: `company/h03/contracts/worth-making-decision.v1.schema.json` and `company/h03/lib/worth_making.py`.
