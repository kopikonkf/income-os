# FA-033 pattern tile QA

`lib/pattern_qa.py:verify_pattern(request, production_result)` checks actual
FA-032 SVG and PNG bytes without changing either artifact. It returns a
deterministic `die.factory-asset.pattern-qa.v1` receipt validated against
`schemas/pattern-qa.schema.json`.

The supported profile is deliberately the current FA-032
`SCATTERED_DIAMONDS` producer version 1.0.0: one solid tile background and
1..128 closed, editable diamond paths. New SVG shapes/styles or wrapped
edge-crossing motifs require a separate explicit profile.

Checks run in order and stop at the first failure:

1. **Lineage:** validate request/native receipt, its digest, actual master and
   preview hashes/byte sizes, producer/job/recipe pins, dimensions and repeats.
2. **Editable paths:** strictly parse flat SVG M/L/Z polygons. Reject image,
   text, script, foreignObject, use, grouping, transforms, CSS, external
   references, DTD/entities, unsupported path commands and degenerate paths.
3. **Tile bounds:** exact viewBox and background extent, actual path count,
   bounded coordinates, recipe diamond dimensions and palette.
4. **Seams:** motif vertices remain inside the tile with the FA-032 one-unit
   background border. No unmatched edge-crossing or clipping is accepted.
5. **Renderability:** reconstruct pixels from actual SVG geometry. Check the
   exact continuous boundaries at x=0/width and y=0/height; comparing adjacent
   pixel centers (0 versus width-1) would incorrectly reject valid edge-near
   motifs.
6. **Preview consistency:** reopen a single RGB PNG of the pinned dimensions.
   Every repeated preview tile must match the independently SVG-derived render,
   including all pixels across internal repeat joins. Producer motif arrays
   and claimed QA booleans do not substitute for artifact inspection.

Input limits are 1 MiB SVG, 64 MiB PNG and 16 million preview pixels; oversize
requests fail closed before rendering. No URL fetching, provider calls, shell
execution or artifact rewriting occurs.

`PASS` requires every check to pass and no failure. Failure receipts contain
a stage/code and leave later checks `NOT_RUN`. Any available source hashes
refer to bytes actually read; missing artifacts never receive invented hashes.
The original semantic asset ID is retained and identity effect is `NONE`.

Compatibility is only `scope=FA032_PATTERN_TILE`. Marketplace compatibility
remains `COMPATIBILITY_UNKNOWN`; this QA does not authorize packaging,
submission, publication or rights claims.

## Linux acceptance

Use a disposable environment inside the isolated task checkout:

```sh
python3 -m venv .venv-fa033
.venv-fa033/bin/python -m pip install -r company/factory-asset/requirements-pattern-qa.txt
.venv-fa033/bin/python -m pytest -q company/factory-asset/tests/test_pattern_qa.py
.venv-fa033/bin/python -m pytest -q company/factory-asset/tests
.venv-fa033/bin/python -m pytest -q bridge/tests/test_one_canon_validator_v1.py
.venv-fa033/bin/python company/scripts/validate_one_canon.py --root .
git diff --cached --check
```

Tests use both canonical FA-032 fixtures and mutate actual SVG/PNG bytes.
Adversarial cases recompute claimed hashes so geometry and preview validation
must detect the defect independently. Repeated QA must leave source bytes and
timestamps unchanged. Full-suite PDF/OpenCV dependencies are pinned alongside
the focused QA dependencies for reproducible task-local acceptance.
