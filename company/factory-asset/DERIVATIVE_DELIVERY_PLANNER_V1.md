# Marketplace-aware Derivative Delivery Planner v1

Task: `FA-132`
Status: PASS
Date: 2026-09-04

The planner consumes validated Blueprint derivative intent plus actual master facts from FA-131/provider-original intake or an accepted native master. It emits deterministic derivative actions without writing output bytes.

Key rules:
- exact provider-original bytes remain immutable;
- if provider original already equals a required delivery format, reuse the master bytes instead of transcoding;
- transparent/alpha-bearing raster -> JPEG requires explicit `FLATTEN_WHITE`;
- PNG/WebP/TIFF transparency is claimed only when the source actually has transparent pixels and alpha is preserved;
- JPEG -> PNG does not invent transparency;
- marketplace delivery compatibility is projected only from the pinned marketplace profile registry; UNKNOWN stays package-blocking;
- preview/internal derivatives are separate from marketplace delivery requirements;
- duplicate equivalent delivery variants collapse to one planned output with aliases;
- vector masters use native export/preview routes; raster masters are never silently promoted to vector;
- derivatives always have `semantic_identity_effect = NONE` and semantic asset count remains one.

The planner performs no derivative execution, upload, publication or spend.