# DIE-H01 Blueprint -> Master Instruction -> Prompt Composer v2

Status: H01-102 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-102 separates **what the asset must be** from **how a provider is instructed to produce it**.

```text
H01 SVG Production Queue
        ↓
Blueprint v2                 provider-independent WHAT
        ↓ deterministic compile
Master Instruction v2        provider-independent normalized production contract
        ↓ provider-profile compose
Provider Prompt v2           provider-specific HOW / phrasing / bounded serialization
        ↓
web-ai-adapter (default) or optional native MCP transport
```

The Blueprint is semantic and commercial authority. Provider names, models, browser/CDP transport, MCP transport, prompt knobs, temperature and token settings are invalid Blueprint concerns. A provider can change without changing the asset identity or Blueprint.

## Blueprint v2 — WHAT

Schema: `contracts/h01-svg-blueprint-v2.schema.json`.

The Blueprint is locked to the Founder-approved H01 SVG MVP contract:

```text
media  = VECTOR
mode   = VECTOR_OBJECT
form   = SINGLE
preset = CLEAN_STOCK_VECTOR_V1
```

Its fields deliberately preserve the commercially important information that was too easy to lose in a short generic prompt:

- source queue/candidate and semantic asset identity;
- canonical subject name;
- recognition anchors and essential components/anatomy;
- proportion notes;
- material, color and texture notes;
- primary commercial use case, buyer value, stock suitability and reuse contexts;
- viewpoint and composition;
- visual hierarchy;
- vector style system and shape language;
- stroke, fill and depth policy;
- native editability requirement;
- bounded SVG complexity;
- trademark/copyright/text/watermark constraints;
- explicit native SVG output/safety subset.

The Blueprint does not contain a prose provider prompt. It is a typed, hashable requirement contract.

## Master Instruction v2 — normalized provider-neutral contract

Schema: `contracts/h01-svg-master-instruction-v2.schema.json`.

The compiler deterministically normalizes one Blueprint into these ordered sections:

```text
SUBJECT
COMMERCIAL
COMPOSITION
VECTOR_STYLE
COMPLEXITY
RIGHTS_AND_STOCK
SVG_OUTPUT
```

The result remains provider-neutral. It contains no Claude/Qwen/ChatGPT/Gemini/Manus routing choice and no browser/API transport choice. It carries the Blueprint SHA-256 and its own canonical SHA-256.

The Master Instruction is intentionally an intermediate representation rather than free-form creative prose. This gives downstream QA and H01-104 a stable contract to bind into request/receipt lineage.

## Prompt Composer v2 — HOW

Implementation: `engineering/svg_prompt_composer_v2.py`.

The Prompt Composer accepts only:

```text
validated Blueprint
+ matching Master Instruction
+ provider profile ID
```

Provider profiles live in `runtime/h01-svg-prompt-profiles.v2.json`. A profile may change only bounded presentation concerns such as opening/closing instruction and DIE's internal prompt-character budget. It may not remove or weaken Master Instruction clauses.

The registry currently carries `GENERIC_WEB_AI`, `CLAUDE_WEB`, `QWEN_WEB`, `CHATGPT_WEB`, `GEMINI_WEB`, and `MANUS_WEB`. These are formatting profiles, not routing authority and not statements of current provider capacity. `budget_semantics=DIE_INTERNAL_BOUND_NOT_VENDOR_MAXIMUM` is explicit so a budget cannot be misread as a vendor-published limit.

Every compiled provider prompt includes every Master Instruction clause verbatim. If the full semantic contract does not fit the selected DIE budget, compilation fails with `PROVIDER_PROMPT_BUDGET_EXCEEDED`. It does **not** summarize away constraints and does not dispatch a truncated prompt.

## H01-103 SVG subset alignment

The H01-102 output contract is constrained not to exceed the accepted H01-103 geometry engine:

```text
max SVG bytes        <= 1,048,576
max geometry elements<= 512
max sampled points   <= 8,192
max path d characters<= 32,768
max group depth      <= 64
```

Allowed geometry families are:

```text
g path rect circle ellipse line polyline polygon
```

Allowed path command families are:

```text
M L H V C S Q T A Z
```

Absolute or relative forms are compatible with H01-103. The prompt contract forbids script, external references, embedded raster images, `foreignObject`, text, style/defs/symbol/use constructs, and requires genuine editable visible vector geometry with a finite `viewBox`.

A tighter Blueprint is valid; it may choose lower bounds than the engine maximum. The H01-102 canary uses 512 KiB, 256 geometry elements, 4,096 sampled points, 16,384 path characters and group depth 32.

## Commercial stock constraints

The compiler does not reduce a noun to “draw X”. It carries forward:

```text
recognizable subject anatomy
+ thumbnail-readable anchors
+ commercial reuse context
+ clear subject hierarchy
+ stock suitability
+ editable vector structure
+ bounded visual complexity
+ trademark/copyright hygiene
+ explicit SVG safety/output contract
```

This is the main H01-102 upgrade over a generic master prompt. The same commercial/vector intent survives provider substitution.

## Determinism and lineage

Canonical JSON serialization is sorted and compact before hashing. The pipeline records:

```text
blueprint_sha256
master_instruction_sha256
provider_profile
provider_prompt_sha256
prompt_chars
prompt_budget_chars
semantic_omission_count = 0
```

Changing only provider profile changes the provider-prompt hash but not the Blueprint or Master Instruction hash. Recompiling the same Blueprint/profile yields byte-identical contracts.

## Authority boundary

Compilation grants no execution or marketplace authority:

```text
provider_call_authorized = false
submission_authorized    = false
publication_authorized   = false
```

`web-ai-adapter` remains the default provider ingress and native MCP remains optional. H01-104 owns the generalized native-SVG request/receipt contract and exactly-once provider execution boundary.

## Canary fixture

`fixtures/h01-102-book-blueprint.v2.json` is tied to the actual first-wave H01 queue lineage for `book` (`H01-SVGQ-CAND-0829866`, source `CAND-0829866`). It demonstrates a real standalone noun rather than an invented production class.

Across every current provider formatting profile, the canary compiles with zero semantic omissions and remains inside the selected DIE prompt budget. No provider call is made by H01-102.
