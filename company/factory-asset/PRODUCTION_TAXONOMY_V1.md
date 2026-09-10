# Factory Production Taxonomy v1

Task: `FA-316`
Status: implementation candidate until governed publication

## Purpose

Keep semantic product identity separate from visual manifestation and file delivery. The canonical order is:

`Object Primitive -> Semantic Mode -> Production Preset -> Subject Specification -> Visual Requirement Spec -> Compiled Provider Prompt -> Master -> Derivatives -> Package`

## Terms

- **Object primitive / seed**: media-agnostic noun or semantic primitive from Object Atlas.
- **Media family**: native representation family. Current values are `RASTER`, `VECTOR`, `MOTION`.
- **Semantic mode / asset type**: commercial product form. Current values are `PHOTO`, `ISOLATED_OBJECT`, `ICON`, `OUTLINE`, `PATTERN`, `ANIMATION`.
- **Production preset**: versioned visual-manifestation defaults for one eligible semantic mode. A preset may type rendering language, style family, style variant, medium, stylization, composition/background defaults, fidelity defaults and prompt descriptors.
- **Subject specification**: structured truth about what the subject contains and how it remains recognizable. It is not a prose image prompt.
- **Visual Requirement Spec**: resolved, typed image requirements for one semantic asset after subject facts and preset defaults are combined.
- **Compiled provider prompt**: deterministic natural-language rendering of the resolved requirements. It is an execution artifact, not the source of semantic truth.
- **Master**: authoritative native artifact for one semantic asset.
- **Derivative**: representation/delivery output derived from an immutable master. Derivatives retain `semantic_identity_effect = NONE`.
- **Package**: governed delivery bundle plus metadata/QA/rights evidence; package count does not increase semantic asset count.

## Isolated-object style hierarchy

`ISOLATED_OBJECT` is a semantic mode. Its style-family axis is separate. Initial supported taxonomy values include `ILLUSTRATIVE_CLIPART`, `CARTOON`, `PHOTOREALISTIC`, `THREE_D_RENDERED`, `HAND_DRAWN`, `FLAT_GRAPHIC`, `MINIMALIST`, `PAPER_CUT`, `CLAY_TOY`, `PIXEL_RETRO`, and `STYLIZED_SEMI_ABSTRACT`.

A style family can have a style variant/medium. For example `CARTOON` may be `WATERCOLOR_CARTOON`, `FLAT_CARTOON`, `CEL_SHADED`, `ANIME_INSPIRED_GENERIC`, `STORYBOOK`, `COMIC`, `COLORED_PENCIL`, `CRAYON`, `GOUACHE`, `PASTEL`, `DOODLE`, or `SOFT_3D_CARTOON`. These are candidate manifestation labels; they are never file derivatives.

## Compatibility truth

`ISOLATED_CARTOON_WATERCOLOR_L0` remains the historical FA-124 accepted manifestation identifier. It is not reinterpreted as the only style represented by the Founder reference archive. A separate source-aligned candidate preset may coexist without rewriting historical receipts.

The active runtime remains unchanged by this taxonomy task. No provider call, production cadence change, marketplace action or scale authorization is implied.
