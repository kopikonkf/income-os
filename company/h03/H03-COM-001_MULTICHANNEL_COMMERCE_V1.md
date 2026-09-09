# H03-COM-001 — Channel-Neutral Multi-Channel Commerce v1

Status: DONE / PASS
Date: 2026-09-09

## Decision

H03 Commerce is no longer modeled as Gumroad/Etsy-first truth. The canonical output is one channel-neutral Commerce Package followed by deterministic eligibility/routing and channel listing-draft adapters.

```text
accepted local product
  -> PASS Founder Review Card
  -> channel-neutral Commerce Package
  -> form/artifact/vertical/intake router
  -> channel drafts
       CONTENT_READY
       DERIVATIVE_REQUIRED
       NOT_ELIGIBLE
       PAUSED_INTAKE
```

Account readiness is deliberately separate from content readiness. Every actionable channel remains `PREFLIGHT_REQUIRED` until its real seller account/session is provisioned. No draft is publication authorization.

## Current registry

Registry size: 19 channels. It includes discovery marketplaces, book marketplaces, book-distribution aggregators, creator storefronts, digital-commerce/MoR, native template marketplaces, education verticals and owned storefronts.

For the current `DIY People-Search Opt-Out Guide`:

- CONTENT_READY (13): google_play_books, gumroad, leanpub, fourthwall, ko_fi, lemon_squeezy, payhip, sellfy, shopify, woocommerce, etsy, creative_fabrica, creative_market
- DERIVATIVE_REQUIRED (4): amazon_kdp, apple_books, draft2digital, notion_marketplace
- NOT_ELIGIBLE: 1
- PAUSED_INTAKE: 1

Examples:
- Google Play Books can consume the current PDF content path, so content is route-ready subject to account/country preflight.
- Amazon KDP / Apple Books / Draft2Digital request book-native derivative work such as EPUB/print packaging instead of pretending the current PDF is immediately publishable everywhere.
- Notion Marketplace requests a `notion_template` derivative rather than treating a PDF guide as a native Notion template.
- Teachers Pay Teachers rejects this product by vertical mismatch.
- Envato remains paused in the current registry and must be rechecked before activation.

## Master commerce package

The package carries product identity, buyer/problem/promise, short/long descriptions, benefits, contents, support statement, SEO keywords/tags, untested pricing hypothesis, FAQ, delivery artifacts, rights disclosure, provenance hashes, derivative opportunities and the route matrix.

Pricing is explicitly `UNTESTED`; no sale/revenue is invented.

## Derivative leverage

Channel gaps are accumulated into deduplicated derivative opportunities (for example EPUB book, Notion template, printable/design bundles). This enables one accepted Knowledge Package to produce multiple SKUs and multiple channel surfaces without repeating deep research.

## Publication boundary

`founder_required=true` and `external_publication_authorized=false` are invariant in the master package and every listing draft. Platform fees/rules are dated observations, never stable H03 business truth; they must be rechecked before live submission.

Artifacts:
- `company/h03/runtime/commerce-channel-registry.v1.json`
- `company/h03/contracts/commerce-package.v1.schema.json`
- `company/h03/contracts/channel-listing-draft.v1.schema.json`
- `company/h03/lib/commerce_router.py`
- `company/h03/evidence/H03-COM-001/`
