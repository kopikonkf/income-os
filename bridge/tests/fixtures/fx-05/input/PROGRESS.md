# PROGRESS — T-FX05 (CSV → Markdown table) — RESUME

## Status
- [x] Baca JOB.json + CONTRACT.md + sample.csv
- [x] Tulis convert.py (CSV → Markdown table)
- [ ] Tulis test (pytest) untuk convert.py
- [ ] Jalankan pytest → hijau (AC-2): 1 passed, exit 0
- [ ] Verifikasi AC-1 (5 baris output: header + pemisah + 3 data) — exit 0, linecount=5
- [ ] Tulis RESULT.json

## Langkah terakhir yang selesai
Menulis convert.py. Langkah berikutnya: menulis test_convert.py

## Catatan
- `sample.csv`: header `name,qty,price` + 3 baris data (apple/banana/cherry).
- Fixture ini mensimulasikan workspace setelah 2 dari 6 langkah selesai.
- `out.md` DIHAPUS sengaja untuk mensimulasikan resume.
- Expected: job dijalankan ulang melanjutkan dari langkah 3, hasil identik dengan fx-01, `RESULT.json` mencatat `resumed: true`.