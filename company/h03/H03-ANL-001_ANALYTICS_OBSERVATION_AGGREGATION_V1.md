# H03-ANL-001 — Marketplace / Social / Direct-Checkout Analytics Observation + Aggregation v1

Status: DONE / PASS
Date: 2026-09-09

Read-only analytics records normalize marketplace, social, hosted-checkout, local-link-commerce and owned-web observations into evidence-linked H03 metrics. Missing values remain `UNKNOWN`; they are never coerced to zero.

Metrics: impression, click, product view, add-to-cart, order, revenue and refund, plus evidence-bound referrer. Aggregation groups by acquisition channel, sales-listing channel, campaign, creative or product. Conversion is derived only when both the order numerator and a valid observed product-view/click denominator exist.

Current unpublished baseline contains 22 UNKNOWN observations and zero live observed metrics. Synthetic acceptance fixtures prove calculation mechanics only and are explicitly non-live. Facebook Page and Facebook Group are distinct analytics channels.
