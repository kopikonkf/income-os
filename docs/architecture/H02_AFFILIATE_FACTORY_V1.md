# DIE H02 — Affiliate Factory V1

Status: FOUNDATION / BUILD-NEXT  
Date: 2026-09-15  
Holding: DIE H02  
Principle: **BUILD > SHIP > CUAN**

## 1. Scope

H02 focuses only on:

- **Affiliate Commerce**
- **Audience / Content distribution**

Initial market: **Indonesia first**.  
US expansion is deferred until the Indonesia lane is mature and generating durable conversion evidence.

Initial commerce rails:

- TikTok Shop
- Shopee

Other Indonesia marketplaces such as Tokopedia, Lazada, and Blibli are signal/corroboration sources first; they are not required as V1 conversion rails.

## 2. V1 Operating Loop

Keep the system minimal:

```text
DEMAND / SIGNALS
    -> WORTH-PROMOTING GATE
    -> PRODUCT TRUTH PACKET
    -> CREATIVE COGNITION
    -> VIDEO ARTIFACT
    -> SOCIAL PROMOTION
    -> HUMAN SUBMIT
    -> CLICK / ORDER / COMMISSION
    -> LEARNING
    -> SIGNALS
```

The objective is not to maximize automation. The objective is to prove a repeatable path from current demand to affiliate revenue.

## 3. Demand / Signals Engine

The engine must detect **what is worth promoting now or before an upcoming demand wave**, not merely products with large historical sales totals.

Three horizons:

- **NOW** — today / next 24–72 hours
- **NEAR** — current week / next 1–4 weeks
- **FORWARD** — seasonal or event-driven opportunities 1–4 months ahead

Signal classes:

- commerce proof
- demand/search velocity
- social/content velocity
- affiliate economics
- content gap / saturation
- seasonal/event timing
- policy/compliance risk

Do not trust one platform as SSOT. A large cumulative sold count is not sufficient proof of current demand.

Every observation should retain provenance and time context so stale seasonal demand can be rejected.

Conceptual opportunity model:

```text
OPPORTUNITY =
    current_demand
  + demand_velocity
  + search_momentum
  + social_momentum
  + affiliate_economics
  + content_gap
  + seasonal_fit
  - saturation
  - stale_penalty
  - event_expiry
  - policy_risk
```

V1 uses simple heuristics. Real H02 click/order/commission receipts will later determine better weights.

## 4. Worth-Promoting Gate

The gate protects scarce creative-generation capacity.

A candidate should not automatically become a production job because it is a bestseller.

Evaluate at minimum:

- current momentum
- commission/economics
- seller/product quality
- product truth availability
- visual/demo suitability
- content opportunity
- saturation
- seasonal validity
- compliance/claim risk

Possible lifecycle states:

```text
DISCOVERED
PRE_RISE
RISING
ACCELERATING
PEAK
DECELERATING
FALLING
EXPIRED
```

## 5. Product Truth Packet

Creative workers must not invent product claims.

Minimum conceptual object:

```text
product_id
product_name
brand
marketplace
price
variants
official_features[]
seller_claims[]
rating
sales_signal
commission
allowed_claims[]
prohibited_claims[]
affiliate_destination
source_ref
captured_at
```

This packet is the bounded truth source for creative generation.

## 6. Creative Kernel

Initial cognition surface: **ChatGPT free account**.

Initial video surface: **Google Flow / Veo**.

Baseline creative pattern from the H02 tutorial:

- product + suitable character/reference
- storyboard
- Scene 1: hook / product introduction
- Scene 2: use / features / benefits grounded in product truth
- Scene 3: closing / CTA
- vertical 9:16 video

V1 does **not** force one persistent human-like avatar across every product category.

During the generalist/gado-gado phase, casting should match product context. Example:

- modest fashion -> suitable female presenter
- kitchen -> suitable household/kitchen presenter
- automotive -> suitable automotive/mechanic presenter
- gadget -> suitable tech presenter

Persistent niche identity becomes valuable after a niche proves itself and receives its own social surface.

## 7. Promotion Surfaces

Initial social distribution targets include:

- TikTok Video
- Shopee Video
- Instagram Reels
- Facebook Page / Groups where appropriate
- X
- YouTube
- Threads
- other channels only when useful

One master product opportunity may create multiple platform-native executions. Do not require identical copy/content across every channel.

### Threads special role

Threads is treated as a **narrative/social traffic engine**, not merely another video sink.

Conceptual conversion cycle:

```text
current topic / relatable problem / useful tip
    -> useful discussion
    -> natural bridge to relevant product
    -> affiliate CTA
    -> follow-up comments completing the cycle
```

The long-term learning object is the relationship:

```text
TOPIC x PRODUCT x FORMAT x AUDIENCE -> CONVERSION
```

## 8. Android Promotion / Research Surface

Android is an operational surface for social/mobile-native workflows, not the main cognition engine.

Desktop/web remains valid for:

- web AI research
- structured market research
- Google Trends / official dashboards
- creative cognition
- Google Flow
- Mission Control / analytics

Android is intended for:

- mobile-native social apps
- app-native search and discovery
- publishing preparation
- comments / inbox / notifications
- creator/affiliate surfaces unavailable or weaker on desktop

WSA is **not** a V1 dependency. The concrete Android runtime/emulator will be selected only after the new VPS is available and virtualization is proven.

V1 target: **one Android promotion device/context, one account per social platform**. No app cloning is required for the initial phase.

Research observations from personalized feeds must be treated as sensor data, not market-wide ground truth.

## 9. Actor Boundary

### Global Hermes

Role: top-level orchestration.

Global Hermes should reason about intents such as:

```text
promote PRODUCT-X
research CATEGORY-Y
prepare CAMPAIGN-Z
```

It should not own low-level Android coordinates or UI mechanics.

### H02 Specialized Hermes Profile

Role: manage the H02 promotional/research lane and platform state.

Responsibilities may later include:

- campaign queue
- platform/account state
- content packet routing
- publish readiness
- comments/inbox triage
- receipts and telemetry

### Android Adapter / Worker

Role: translate semantic actions into device operations.

Expected capability shape:

```text
device.status
app.launch
app.stop
ui.inspect
ui.tap
ui.type
ui.scroll
screen.capture
file.push
file.pull
intent.open
```

Likely low-level transport candidates include ADB plus Android UI automation. Exact implementation is deferred until VPS acceptance testing.

### Founder

V1 publication remains **manual-submit / Founder authorized** until the engine has earned autonomous publication through repeated evidence.

## 10. V1 Autonomy Rule

Preparation can become automated before publication.

Preferred progression:

```text
research
-> prepare creative
-> prepare platform post
-> READY_FOR_SUBMIT
-> Founder QC
-> manual Publish
```

Autonomous publication is a later maturity gate, not a V1 requirement.

## 11. New VPS Acceptance Gate

Before building Android automation, prove the runtime:

```text
[ ] virtualization extensions exposed to guest
[ ] accelerated Android runtime boots reliably
[ ] required Google/mobile services usable
[ ] TikTok app login persists across reboot
[ ] Shopee app login persists across reboot
[ ] Instagram / Threads / Facebook / X / YouTube sessions persist as needed
[ ] media push/upload works
[ ] app search/discovery surfaces usable
[ ] comments/inbox usable
[ ] Android/browser coexistence acceptable
[ ] resource usage acceptable on 8 vCPU / 32 GB RAM host
```

If this gate fails, change the Android runtime implementation; do not redesign the H02 business pipeline.

## 12. Build Order After VPS Availability

Keep tasks atomic:

1. VPS and virtualization preflight.
2. Select and seal one Android runtime.
3. Install/log in one account per initial social app.
4. Prove restart/session persistence.
5. Prove media transfer and manual post preparation.
6. Probe exact Indonesia TikTok/Shopee research and affiliate surfaces.
7. Implement minimal signal collection and freshness/provenance schema.
8. Implement Worth-Promoting V0 heuristic.
9. Run one product end-to-end through ChatGPT -> Flow -> promotion-ready package.
10. Founder manually publishes.
11. Record click/order/commission receipts.
12. Iterate only from observed bottlenecks and revenue evidence.

## 13. Non-Goals for V1

Do not build yet:

- multi-account farms
- app cloning at scale
- autonomous mass publishing
- large orchestration abstractions before the first revenue loop works
- sophisticated ML scoring before conversion receipts exist
- separate codebases for every marketplace or social platform
- US lane before Indonesia V1 is mature

## 14. Definition of Success

H02 V1 succeeds when DIE can repeatedly perform:

```text
fresh opportunity
-> worth-promoting decision
-> truthful creative
-> video artifact
-> platform-native promotion package
-> Founder publish
-> attributable click/order/commission
```

The first meaningful milestone remains simple:

**SHIP content that generates real affiliate revenue, then scale what worked.**
