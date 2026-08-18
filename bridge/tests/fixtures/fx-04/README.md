# fx-04 — tulisan di luar allowed_paths (D6 §5.5)

Membuktikan snapshot filesystem (CB7) benar-benar ditegakkan: `changed-paths.json`
yang memuat `C:\DIE\state\EVENTS.jsonl` dan `C:\Users\Public\x.txt` (di luar
`allowed_paths` workspace) harus ditolak `die_accept.py` menjadi `accepted_status: failed`
(exit 2) dengan problem `D6-5.5 tulisan di luar allowed_paths`.