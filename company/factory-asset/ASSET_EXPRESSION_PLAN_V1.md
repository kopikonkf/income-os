# Asset expression plan v1 (FA-129)

The plan is the decision boundary before Blueprint authoring and producer selection.
A seed noun can produce zero, one or several commercially distinct expressions.
Nothing requires six outputs, one output per mode, or an output for every seed.

`schemas/asset-expression-plan.schema.json` is Draft 2020-12, tagged
`die.factory-asset.asset-expression-plan.v1`. Call
`lib/asset_expression_plan.py:validate_asset_expression_plan` before consuming a
plan: JSON Schema alone cannot check evidence references or repeated semantic IDs.
The function returns `None` on success and raises `AssetExpressionPlanError` with a
stable `code` on failure; it does not mutate the input or perform I/O beyond reading
its local schema.

## Decisions and pins

- `SELECT` requires one or more expressions and supporting evidence.
- `RESEARCH` and `REJECT` require zero expressions and an explicit rationale.
- Each selected expression pins a `FASA-...` semantic identity, buyer, commercial
  use case, product expression, semantic mode, exactly one producer class and one
  candidate marketplace route. Additional routes belong to later delivery
  planning for the same semantic identity.
- Each evidence reference resolves to a source reference, source SHA-256,
  provenance kind, rationale and a support scope matching the seed, buyer, use
  case, product expression, mode and marketplace. All referenced support scopes
  must match. Evidence collected about a photograph cannot justify an animation.
- `PHOTO` / `ISOLATED_OBJECT` use `RASTER_GENERATIVE`; `ICON` / `OUTLINE` use
  `NATIVE_VECTOR` or `PROCEDURAL_VECTOR`; `PATTERN` uses `PROCEDURAL_VECTOR`;
  `ANIMATION` uses `MOTION_RENDERER`. Unknown modes/classes fail closed.

The schema pins the selection's commercial meaning; the validator checks internal
consistency, not the truth or freshness of evidence. A source hash is a provenance
pin, not proof of a market claim. Evidence review must verify source bytes, content,
freshness, and buyer relevance before production. Candidate routes always remain
`CANDIDATE_REQUIRES_POLICY_CHECK`; validation conveys no rights, compatibility,
provider availability, submission permission, or frozen Blueprint approval.

## Semantic expansion versus delivery

An expression has no derivative list, format, dimensions, existing master input,
or conversion action. Delivery choices such as JPEG/PNG/WebP previews belong after
the validated master and preserve its semantic identity, as defined by
`derivative-recipe.schema.json`. A repeated commercial tuple with a different ID,
route or producer fails validation. Normalization catches case/whitespace changes;
paraphrases still require semantic near-duplicate review.

`force_all_modes` must be false and `expansion_rule` must be
`EVIDENCE_SUPPORTED_ONLY`. A caller cannot attach the same photograph evidence to
other modes. Six modes may be selected only if each independently meets the same
evidence contract; the contract forbids forced expansion, not well-supported
commercial breadth.

Animation is a new semantic product. It requires a temporal verb, observable visual
change and buyer utility. These fields prepare FA-130's temporal-value gate; their
presence alone does not make motion eligible. FA-130 scoring, FA-133 dispatch,
Blueprint compilation integration and packaging implementation remain separate
tasks. This module performs no generation or post-hoc static-to-motion conversion.

## Acceptance fixtures and verification

`fixtures/asset-expression-plan/{zero,one,multiple}.json` use the same shopping-bag
seed. Zero requests research; one selects a campaign photograph; multiple selects
that photograph, a wrapping-paper pattern and a checkout-completion animation.
The fixture briefs and hashes resolve to `synthetic-evidence.json`. They are
explicitly `SYNTHETIC_FIXTURE`, not real buyer or marketplace evidence.

From repository root run:

```sh
python -m pytest -q company/factory-asset/tests/test_asset_expression_plan.py
```

Tests cover all three cardinalities, REJECT, evidence/seed/route drift, missing
commercial pins, incompatible producers, unknown modes, forced all-mode policy,
derivative injection, duplicate semantic identities, and fixture source hashes.
