# fx-05 — resume (D6 §7)

Membuktikan logika resume: workspace berisi `PROGRESS.md` (2 dari 6 langkah selesai) + `out.md` DIHAPUS.

Expected golden data:
- `PROGRESS.md` terbaca dengan benar (langkah terakhir = "Menulis convert.py")
- `RESULT.json` hasilnya identik dengan fx-01 (accepted_status: done, semua AC terbukti)
- `RESULT.json` mencatat `resumed: true`

Catatan: Menjalankan ulang butuh worker nyata dan tidak memungkinkan di lingkungan tes otomatis. Fixture ini sebagai data golden + test yang memverifikasi `PROGRESS.md` terbaca dan `resumed: true` ada di RESULT.json.