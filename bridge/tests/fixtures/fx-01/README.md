# fx-01 — happy path worker contract (D6 §7)

Membuktikan gerbang penerimaan mengizinkan klaim `status: done` yang lengkap:
- `evidence` memetakan semua 3 AC (AC-1, AC-2, AC-3)
- `tests` berisi `pytest` dengan `result: pass`
- `artifact` file benar-benar ada di workspace
- `changed-paths.json` hanya berisi path di dalam `allowed_paths` workspace

Expected: `die_accept.py` → `accepted_status: done`, `problems: []`, exit 0.