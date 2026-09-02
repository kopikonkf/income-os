# Submission Dry-Run Composer v1

`SUB-001D` composes a deterministic marketplace-ready *plan* from one immutable `die.asset.submission-package.v1`, its exact metadata payload, a PASS platform metadata mapping, and one artifact basename.

The composer emits the artifact reference, mapped metadata, ordered planned actions, exact lineage hashes, and a reproducible `composition_sha256`. Canonical JSON uses sorted keys and compact separators so identical inputs produce the same digest and fixture output.

The planned action sequence is `ATTACH_ARTIFACT`, `APPLY_MAPPED_METADATA`, then `STOP_BEFORE_SUBMISSION`. Every planned action is non-external. This layer performs no marketplace login, no credential access, no browser/API submission, and no publication. It does not grant submission authority; Founder authority remains a separate `SUB-001B` boundary and later adapter/execution layers must re-check it.

Composition fails closed when the metadata hash differs from the immutable package pin, when the package is not PREPARED/fail-closed, when platform mapping is not PASS, or when the artifact name is not one normalized basename.
