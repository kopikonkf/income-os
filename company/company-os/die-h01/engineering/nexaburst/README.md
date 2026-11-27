# H01 NexaBurst KW / PSR postproduction rescue

This directory preserves the live H01 operational sources that form the caller side
of the KW-Gemini metadata override seam rescued on 2026-11-27.

Source runtime snapshot:
- /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-kw-enrich.py
- /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-v2-worker-psr.py
- /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-psr-postprod-watchdog.sh

These files are H01-specific operational source snapshots, not an installer.
They intentionally retain production absolute paths so recovery can compare the
canonical repository copy with the deployed H01 copy.

No credential values are stored in these files. The enrichment worker reads keys
from external runtime storage; those credentials remain outside Git.

Contract preserved:
1. KW enrichment emits per-asset title, description, and keyword receipts.
2. The PSR V2 worker maps those fields to title_override,
   description_override, and keywords_override.
3. The worker passes the bounded override dictionary to
   postprocess_raster_workspace(metadata_overrides=...).
4. Assets without a receipt retain the legacy metadata fallback.
