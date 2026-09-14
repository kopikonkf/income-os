# DIE H01 Phase-0 Production Intent v1

Task: H01-132A

## Purpose

H01-132A binds the immutable daily Demand Intelligence selection to a provider-independent Phase-0 production intent. It does not generate SVG, does not dispatch a provider, and does not join Human Atlas.

Canonical input chain:

```text
H01-101 queue identity
  + H01-130A demand record
  + H01-133A frozen selector item
        ↓
H01-132A Phase-0 production intent
```

Each intent hash-binds the exact queue row, selector item, selector manifest, demand record, demand materialization, and evidence references.

## Phase-0 boundary

Every intent enforces:

- standalone noun only;
- `human_context = null`;
- empty family hypotheses;
- no longtail;
- no Object Atlas × Human Atlas cross-join;
- no provider routing in the semantic intent;
- no production/submission/publication/spend authority.

Any selector item containing Human Atlas context or family hypotheses is rejected fail-closed.

## Commercial basis

H01-132A does not invent buyer segments or use cases.

Evidence-ranked marketplace nouns receive only a bounded commercial envelope: generic stock-marketplace demand for an editable standalone vector of the exact noun is supported, while industry, demographic, named-buyer and other unsupported claims remain forbidden.

Macro or attention evidence can only weaken the commercial assertion. Fallback nouns explicitly record that no demand-evidence-specific buyer claim is supported and may use only baseline standalone editable-vector utility.

This commercial basis is intended as the deterministic input to H01-102A Commercial Blueprint v3.

## Runtime state

Canonical Linux output root:

`/var/lib/die/h01/production-intent/phase0`

Layout:

```text
<day_key>/<cycle_id>/
  intents/<intent_id>.json
  manifest.json
<day_key>/latest.json
```

Intent and manifest files are immutable/collision-checked. `latest.json` is only a pointer.

## Live acceptance 2026-09-14

Input daily cycle:

`H01-DCYCLE-AC9AEEDEA79D6F52BA60FF98`

Frozen selector:

`H01-DAILY-52BA25C07ED0E582F7D47BFB`

Result:

- 100 selected nouns bound;
- 4 evidence-ranked intents;
- 96 source-order fallback intents;
- 100/100 exact H01-101 queue identities preserved;
- 0 Human Atlas contexts;
- 0 family hypotheses;
- 0 longtails;
- 0 Object×Human cross-joins;
- 0 provider-routing leakage into semantic intent;
- all authority flags false.

Manifest:

`H01-P0MAN-6267BB795752A51868B0EEE0`

Manifest SHA-256:

`ae2a130a954c6b07775a987d670896d40965e55ff671938b31335b37d267d6f6`

A second execution with the same frozen inputs produced the same manifest ID and manifest hash.
