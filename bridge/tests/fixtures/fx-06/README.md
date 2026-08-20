# fx-06 - akurasi system_health & pemisahan lapisan reader/projection

Membuktikan projection.py hanya membaca field KANONIK dari ReaderResult (bukan
nama kolom Hermes mentah seperti "Name" / "Last run") dan system_health
mengagregasi gateway+cron+events dengan completeness/source_trust yang jujur.
Reader di-stub dengan field kanonik; kalau projection bergantung pada nama
kolom Hermes, test gagal. Juga membuktikan reader gagal terlihat buta
(completeness: degraded, trust: DEGRADED) tanpa melempar.
