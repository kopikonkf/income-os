# fx-08 - no-raw-access: 6 payload injeksi ditolak sebelum menyentuh reader

Membuktikan D5 §2 (§5): tidak ada SQL mentah, tidak ada path traversal, tidak
ada shell, tidak ada kredensial. Enam payload (SQL / path / shell /
kredensial / .env / field liar) harus ditolak validate() dengan kode
E_NO_RAW_ACCESS atau E_TOO_LARGE, dan setiap penolakan tercatat rejected: true
di ACCESS.jsonl. Ambang alarm: rejected >= 1 -> WARNING di briefing.
