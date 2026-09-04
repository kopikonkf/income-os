# Procedural Pattern Engine v0.1 acceptance

FA-034 accepts the offline FA-031 → FA-032 → FA-033 path for the pinned
`SCATTERED_DIAMONDS` fixtures. Each request generates a native editable SVG tile
and tiled PNG preview. A second independent directory must contain identical
master/preview bytes and the same native receipt. Independent QA checks source
hashes, bounds, editable paths, seams and every preview repeat before packaging.

`company/factory-asset/lib/pattern_engine_acceptance.py` adds an offline acceptance
driver. It composes an internal dry-run package with the editable SVG delivery
and tiled PNG preview. Package files are reopened and checked against original
bytes and manifest hashes/lengths. Both source artifacts retain their bytes and modification times.
The Blueprint identity invariant must classify the derivative change as
`PACKAGING_VARIANT`; both derivatives retain one semantic asset ID. The two
canonical color/seed fixtures share that identity and are not counted as two
commercially distinct assets.

The acceptance root must be new, so rerunning cannot overwrite existing evidence.
A producer result that fails QA cannot reach packaging. Existing negative QA
fixtures cover broken seams, malformed/out-of-bounds paths, raster/font/script
masquerades, resealed preview drift, missing artifacts and resource limits.

## Reproduction

Use Python 3.12 and `company/factory-asset/requirements-pattern-qa.txt` in an
isolated Linux virtual environment. From the repository root:

```sh
python -m pytest -q company/factory-asset/tests/test_pattern_engine_acceptance.py company/factory-asset/tests/test_procedural_pattern.py company/factory-asset/tests/test_pattern_qa.py company/factory-asset/tests/asset_identity_invariants
python -m pytest -q company/factory-asset/tests
python company/factory-asset/bin/run_pattern_engine_acceptance.py --output-dir /tmp/fa034-new-acceptance
```

The FA-034 receipt records the independently generated fixture hashes and the
exact Linux validation commands. Temporary acceptance artifacts belong only to
the isolated checkout and are not production masters.

## Scope and disable path

Acceptance certifies FA032 tile geometry and internal package integrity only.
Marketplace compatibility remains `COMPATIBILITY_UNKNOWN`; the synthetic
metadata/rights references grant no clearance or submission authority. EPS is
outside this acceptance: review found that the existing `native_vector.export_eps`
does not preserve pattern fill colors. EPS delivery needs a separately verified
export repair before it can be certified for colored patterns. No provider,
browser, upload, spend or production scheduler hook is used.

Disable by stopping calls to this offline driver. Native masters are preserved;
there is no live runtime migration or deployment to roll back. Broader pattern
recipes, semantic eligibility and orchestration remain separate tasks.
