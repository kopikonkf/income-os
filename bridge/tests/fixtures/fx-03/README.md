# fx-03 — test gagal (D6 §5.3)

Membuktikan gerbang menurunkan `accepted_status` ke `partial` saat ada test dengan `result: fail`.

Input `RESULT.json` berisi `tests: [{name: "pytest", result: "fail"}]`.
Expected: `die_accept.py` → `accepted_status: partial`, `problems` memuat `D6-5.3`, exit 2.