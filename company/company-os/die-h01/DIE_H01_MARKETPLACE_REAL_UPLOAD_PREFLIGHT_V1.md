# DIE-H01 Marketplace Real-Upload Technical Preflight v1

Task: H01-109A. Real upload remains H01-109B / FOUNDER_REQUIRED.

H01-109A proves the local handoff from an H01 postproduction workspace through H01-134 delivery packages, H01-135 submission-ready projection, and H01-136 deterministic transport/idempotency. It performs no marketplace login, upload, submit, publication, credential access, or spend action.

Run with the accepted H01 Python environment and an isolated output root under `/var/lib/die/h01/preflight/H01-109A`. The live `/var/lib/die/h01/submission-ready` index is read only for diagnostics. The preflight snapshots source hashes before and after packaging/projection and fails if the workspace changes.

A zero eligible count is an honest PASS: the technical path is valid, but H01-109B must not start until an asset has rights PASS, Founder QC PASS, and appears in submission-ready. H01-136 exact replay must produce one durable receipt, while changed content for the same marketplace/semantic-asset scope must be duplicate-blocked.

## Founder handoff runbook

After eligibility exists, Founder selects the exact hash-bound submission-ready package, performs marketplace account/authentication and final visual QC manually, uploads that exact package, and records only the opaque remote acknowledgement/moderation state required by H01-136. Automation must not capture account secrets. Real submission/publication/spend authority remains Founder-only.

## Live proof 2026-09-14

Workspace `/var/lib/die/h01/runs/H01-108/055-sunflower-manus-a1` produced six COMPATIBLE marketplace packages. All six stayed non-eligible because rights were REVIEW_REQUIRED and Founder QC was NOT_RECORDED. Isolated projection: 0 eligible / 6 skipped. Live submission-ready: 0 eligible. H01-136 exact replay was idempotent, duplicate-scope mutation was blocked, source hashes were unchanged, and all external actions remained NONE.

Therefore H01-109A is technically PASS while H01-109B remains blocked on eligibility.
