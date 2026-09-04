# Provider-original intake v0.1 (FA-131)

`lib/provider_original.py:intake_provider_original` accepts a local artifact from
any provider and emits normalized master-ingestion attempt evidence. It performs
no provider calls. `provider_id` and declared MIME are supplied lineage claims;
neither proves remote origin nor determines the decoded media type.

```python
receipt = intake_provider_original(
    source_path='downloads/original.webp', staging_root='job/staging',
    attempt_id='attempt-001', semantic_asset_id='FASA-EXAMPLE_001',
    blueprint_id='FABP-EXAMPLE_001', provider_id='provider-example',
    expected_sha256=download_sha256,  # optional independently captured pin
    declared_mime_type='image/webp',  # optional untrusted transport claim
)
```

The source is read once into a bounded byte snapshot. Intake derives SHA-256,
magic signature, actual JPEG/PNG/WebP/TIFF format and MIME, encoded pixel width
and height, decoder mode, byte count and alpha facts. Width/height describe the
encoded raster; EXIF orientation is neither applied nor rewritten. Verification
and full decode run against the same snapshot before any staging writes.
Valid extensions must match content (JPEG and TIFF aliases, including uppercase,
are accepted). Extensionless downloads are allowed. A conflicting declared MIME
is retained with `declared_mime_matches: false`; it cannot override actual facts.

Alpha evidence distinguishes `has_alpha_channel` from `has_transparency`.
An RGBA PNG whose alpha values are all 255 is opaque. PNG palette and RGB tRNS
transparency are decoded and measured even when no alpha band exists.
`alpha_min` and `alpha_max` record actual decoded extrema on the 0–255 scale.
Decode-time RGBA conversion only measures transparency; it is never saved.

`master_ingestion.stage_master_snapshot` stages exactly those original bytes at
`blobs/sha256/<prefix>/<sha256>` using publish-once hard links from a fully written,
fsynced temporary file. Files receive read-only permissions on Linux. Existing
blobs and receipts are compared before reuse and are never overwritten. This is
an application immutability contract, not protection against a privileged host
operator: tampering or a missing already-pinned blob fails closed on retry.
Original source files and filenames remain untouched; extensionless CAS storage
deduplicates `.jpg`/`.jpeg` aliases without assigning a new media encoding.

Each attempt preserves provider/source lineage, media facts, source hash and byte
count. The same hash is passed to the State Manager proposal. Exact attempt retries
return their original receipt, including its historical `blob_reused` flag;
different attempts retain independent receipts while reusing one blob. Conflicting
attempt IDs fail before publishing a second blob. Concurrent publication cannot
replace existing bytes. A crash between blob publication and receipt publication
can leave an unreferenced immutable blob; retry safely completes the receipt.

The receipt retains the existing `master-ingestion-attempt.v1` envelope with a
typed `provider_original` extension, specified by
`schemas/provider-original-intake.schema.json`. `staged_index` can consume it.
Generic `stage_master` remains backward compatible for non-raster assets; provider
callers must explicitly use this stricter intake entry point. Runtime producer
dispatch wiring belongs to downstream tasks.

Intake does not claim canonical truth or promote task state: every receipt remains
`STAGED_NOT_CANONICAL`, `canonical_truth: false`, with a State Manager commit
required. No lossy save, alpha flattening, derivative generation, semantic asset
creation or source relabeling occurs.

Boundaries and typed failures:

- JPEG, PNG, WebP and TIFF only; unknown magic fails `MEDIA_MAGIC_UNSUPPORTED`.
- Empty/unreadable/over-limit sources fail before staging. v0.1 caps inputs at
  128 MiB and rasters at 40 million pixels to bound decode resources.
- Extension disagreement fails `EXTENSION_CONTENT_MISMATCH`.
- Structural errors, truncation, decoder warnings and PNG CRC errors fail
  `MEDIA_DECODE_FAILED`. JPEG/PNG require their final terminator; WebP requires
  exact RIFF length. Trailing data after JPEG/PNG terminators is intentionally
  rejected by this conservative intake contract.
- Animation and multipage containers fail `MULTIFRAME_UNSUPPORTED`; first-frame
  facts cannot stand in for a complete master.
- Pillow's permissive global truncated-image mode fails
  `UNSAFE_DECODER_CONFIGURATION` rather than weakening validation.
- Expected hash mismatch fails `SOURCE_HASH_MISMATCH`; stored-byte mismatch or a
  missing previously pinned blob fails `CONTENT_ADDRESS_COLLISION`.
- Unsafe attempt paths or symlinked staging subdirectories fail closed.

Acceptance fixtures are synthetic and require no external service. Eight pinned
files in `fixtures/provider-original-v1/manifest.json` cover all four formats,
opaque RGB, opaque RGBA, partial alpha, PNG palette transparency and RGB tRNS.
`build_assets.py` regenerates fixtures and schema using the pinned Pillow runtime.

```sh
.venv/bin/python -m pytest company/factory-asset/tests/test_provider_original.py \
  company/factory-asset/tests/test_master_ingestion.py -q
```

Tests cover exact source preservation, normalized schema/lineage, all format and
extension combinations, malformed/truncated media, CRC corruption, byte/pixel
limits, transparency, alias deduplication, concurrent retries, attempt conflicts,
source mutation after snapshot, missing/tampered blobs and path confinement.
