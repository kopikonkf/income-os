# H03-ATTR-001 — Product / Listing / Campaign / Creative / Channel Attribution Spine v1

Status: DONE / PASS
Date: 2026-09-09

The attribution identity joins `problem_seed_id -> product_id -> commerce_package_id -> listing_id -> campaign_id -> creative_id -> channel_id` and carries deterministic UTM source/medium/campaign/content identity.

Acquisition channel and sales-listing channel are separate fields. A creative on X can therefore attribute toward a Payhip/Gumroad/book-store listing without conflating traffic source and checkout surface.

Current acceptance materializes 13 planned identities for content-ready Commerce routes. Every destination remains `UNPUBLISHED`; observed event count is 0.

Funnel states are `UNOBSERVED`, not numeric zero. Observed events require source-event identity plus evidence refs. `ORDER`, `REVENUE`, and `REFUND` require order identity; revenue/refund additionally require explicit money. Therefore the contract cannot manufacture conversion or revenue from missing telemetry.

Supported observed event types: impression, click, product view, add-to-cart, order, revenue, refund.

No publication or canonical economic commit authority is granted.
