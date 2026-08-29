# Human-Centric Demand Atlas Canon v1

Status: CANON v1 — effective when merged
Scope: Holdings R&D and M-001 opportunity intelligence
Authority: Founder decision dated 2026-08-23; subordinate to `CONSTITUTION.md`
Runtime effect: knowledge only; no production, publication, spend, or state mutation

Purpose: map human existence into commercially valuable representations, then
send only evidence-backed candidates through the Worth-Making Gate.

## H1 — Holdings North Star

The holdings BHAG is `$1B / 3Y`, evaluated through **net profit and run-rate**.

| Measure | Canonical meaning |
|---|---|
| Net profit | Gross revenue less all attributable platform fees, tool/compute costs, and valued operating time |
| Annualized run-rate | Latest normalized monthly net profit multiplied by 12 |
| Gross revenue | Diagnostic input; never a substitute for net profit |
| Valuation | Possible outcome; never the operating target |

Report net profit and annualized run-rate side by side. Do not add them as if
they were the same accounting period. The BHAG is a design constraint for
scalability, not a revenue forecast and not permission to weaken evidence gates.

## H2 — Candidate-Space Equation

```text
HUMAN × ACTIVITY × OBJECT × PLACE × TIME × DEMOGRAPHIC
× EMOTION × PROBLEM × INDUSTRY × COMMERCIAL_INTENT
```

| Field | Question answered | Example scope |
|---|---|---|
| `human` | Who experiences or communicates the demand? | role, life stage, capability |
| `activity` | What are they doing? | lifecycle, work, care, leisure |
| `object` | What thing or system is involved? | tool, device, document, environment |
| `place` | Where does it occur? | home, clinic, office, transit |
| `time` | When or under what timing condition? | daypart, season, event, urgency |
| `demographic` | Which population context matters? | age, profession, household, accessibility |
| `emotion` | What human state changes the representation? | anxiety, relief, trust, celebration |
| `problem` | What pain, risk, or job needs communication? | confusion, illness, delay, compliance |
| `industry` | Which economic domain buys or uses it? | health, education, finance, hospitality |
| `commercial_intent` | What paid use is expected? | advertise, explain, teach, decorate, package |

The equation defines a combinatorial search space, not a claim that a fixed
number of useful ideas exists. Candidate cardinality may be reported only after
the registries are enumerated, normalized, and deduplicated. Until then,
`millions` or `billions` is `HYPOTHESIS`, never a measured fact.

## H3 — R&D Branches and Candidate Contract

Human existence is explored through five coordinated branches:

| Branch | Primary coverage |
|---|---|
| Human existence | body, mind, social roles, needs, desires |
| Activities and lifecycle | daily cycle, work, care, illness, hobbies, events |
| Objects and systems | physical objects, documents, interfaces, infrastructure |
| Emotions and states | cognitive, physical, relational, and situational states |
| Contexts | place, time, demographic, problem, industry, commercial intent |

An activity or object is not an opportunity by itself. R&D must connect it to a
buyer, use case, money signal, competition gap, differentiated representation,
and cheapest falsifiable test.

```yaml
candidate_id: ATLAS-CANDIDATE-ID
human: null
activity: null
object: null
place: null
time: null
demographic: null
emotion: null
problem: null
industry: null
commercial_intent: null
target_buyers: []
buyer_jobs: []
candidate_asset_types: []
eligible_surfaces: []
evidence:
  - claim: null
    label: OBSERVED|VERIFIED|INFERRED|HYPOTHESIS|UNKNOWN
    source_ref: null
worth_making_score: null
confidence: low|medium|high
status: observed|inferred|hypothesis|unknown
```

## H4 — Worth-Making Gate

Hard veto before scoring: unresolved rights/IP, unsafe or deceptive use,
ineligible platform/content type, unclear production-tool commercial rights,
unauthorized spend, or no falsifiable buyer hypothesis.

| Factor | Weight |
|---|---:|
| Demand evidence | 20 |
| Commercial intent | 15 |
| Buyer utility | 15 |
| Competition gap | 10 |
| Visual scarcity or differentiation | 10 |
| Production feasibility | 10 |
| Eligible-platform fit | 10 |
| Repurposing potential | 5 |
| Speed to cheapest falsification | 5 |
| **Total** | **100** |

| Score | Decision |
|---:|---|
| 75–100 | Candidate for bounded validation after Founder gate |
| 60–74 | Research backlog; acquire evidence or narrow/merge |
| Below 60 | Defer or kill the hypothesis; preserve capacity |

The score is a decision aid, not scientific precision. Weak evidence lowers
confidence; it must never be replaced by invented numbers.

Evidence labels are mandatory:

- `OBSERVED` — directly visible in a marketplace, artifact, or receipt;
- `VERIFIED` — confirmed by an authoritative current source or executed receipt;
- `INFERRED` — reasoned from evidence but not directly measured;
- `HYPOTHESIS` — falsifiable proposition awaiting a test;
- `UNKNOWN` — not available and not invented.

## H5 — M-001 Operating Doctrine

```text
Research → produce → approve → license → measure ERVA → scale
```

- M-001 proves one primitive economic loop for Pillar E; it does not activate
  the other fourteen holdings pillars.
- A 20–40 asset micro-batch is a validation unlock test, not a permanent cap.
- After approval, paid license, and positive observed ERVA, a validated family
  may unlock up to 50–100 assets/day and target 1k–5k assets/month.
- Quantity remains bounded by unique research supply, QA, Platform Contracts,
  submission headroom, differentiation, cost, and observed economics.
- Zero Trash is routing: a clean Tier-1 mismatch may be transformed for another
  authorized route; rights/safety hard failures are quarantined or recreated.
- No generic `FAIL → social` route exists. Tier-2 requires material editorial
  transformation and separate Pillar A publication authority.
- Hermes orchestrates the loop; the Intelligence Director scores and specifies;
  workers execute bounded jobs; DIE State Manager remains the only state writer.


## H6 - Dual-Atlas Cross-Join Complement

The Human-Centric Atlas is the demand generator; the Object-Centric Atlas is the validated semantic-primitive generator. The `OBJECT` dimension SHOULD be populated through bounded retrieval from the cleaned Object Atlas rather than a duplicated static mega-list.

A commercial asset hypothesis is modeled as:

`Object Primitive ? Human Demand Context ? Product Expression`

Object primitives are media-agnostic. Product Expression is downstream and may range from primitive static assets through compositions, packs/bundles, templates, motion/video, and 3D/spatial assets.

Operational cross-join is retrieval- and constraint-based, not exhaustive Cartesian enumeration. Use demand-first or supply-first anchors, coherence constraints, bounded long-tail/context expansion, current Opportunity Signals, Demand Score, governed Worth-Making judgment, and only then Blueprint authoring.

Normative complement: `company/atlas/human-centric/CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md`. The preserved Qwen Cross-Join files remain provenance foundations and do not override current authority contracts.
