# DIE H01 Submission-Ready Projection v1

H01-135 provides a disposable, deterministic projection of marketplace packages that are safe to hand to a Founder or future submission transport.

Source package root defaults to `/var/lib/die/h01/delivery`. Projection root defaults to `/var/lib/die/h01/submission-ready`.

A package enters the projection only when all four checks agree:

1. package manifest `submission_eligible=true`;
2. marketplace compatibility is PASS/COMPATIBLE;
3. rights result is PASS;
4. Founder QC is PASS.

The projection never mutates provider originals, canonical masters, postproduction derivatives, or H01-134 package sources. It copies hash-verified package files into `<marketplace>/<semantic_asset_id>/`, writes `projection.json` per asset, and writes `submission-ready-index.json` at the root. The tree is fully rebuildable.

Stale projected entries are removed when their source package becomes ineligible. A non-empty directory without the DIE projection marker is rejected rather than cleaned, preventing accidental deletion of unmanaged files.

The projection grants no external action authority. It is a staging/readiness surface only.
