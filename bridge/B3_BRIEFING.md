# TUGAS CLINE — LENGKAPI INFRASTRUKTUR ORGANISM TEST B3 (untuk agent pelaksana)

> Target: cline (pane w8:pH). Kerjakan di `C:\DIE`. Laporkan via file `C:\DIE\bridge\P1_REPORT.md` (timpa, pakai tool write file — jangan kirim ke pane).

## Latar

Bridge P0+P1 SELESAI. Sekarang mempersiapkan **Organism Test Phase A (spec `D:\Digital_Income_Empire\Docs\Claude Opus 5\deliverables\cleaned\v2\S2-B3-Organism-Test-v0.md`)**. Prasyarat mission nyata belum ada (itu keputusan Founder), TAPI infrastruktur tes bisa disiapkan sekarang secara paralel.

## Yang sudah ada (JANGAN rusak)

- `C:\DIE\bridge\tests\fixtures\`: fx-02, fx-04, fx-06, fx-07, fx-08, fx-08c, fx-08d ✅
- `C:\DIE\bridge\tests\`: test_fx02_fx04.py, test_fx07.py, test_fx08.py, test_opus5_contract.py, test_projection.py, conftest.py (17 pytest PASS)
- `C:\DIE\bin\`: die_accept.py (gerbang penerimaan worker), die_event.py (penulis tunggal), die_snapshot.ps1 (snapshot filesystem)
- `C:\DIE\workspaces\T-0001\`: job dummy lengkap (JOB.json, convert.py, RESULT.json, evidence\ — referensi format)

## Tugas (urut)

### 1. Fixture fx-01, fx-03, fx-05 (Worker Contract — B3.5, D6 §7)

Buat di `C:\DIE\bridge\tests\fixtures\fx-01\`, `fx-03\`, `fx-05\` (ikuti pola fx-02/fx-04 yang ada: folder `input\` + `expected.json` + `README.md` satu paragraf):

- **fx-01** happy path: `input\JOB.json` = job T-0001 (CSV→Markdown, 3 AC, format sama persis dengan `workspaces\T-0001\JOB.json`) + `input\RESULT.json` = `status: done` dengan evidence memetakan AC-1..AC-3 + test `pass` + `input\changed-paths.json` hanya berisi path di dalam workspace. Expected: `die_accept.py` → `accepted_status: done`, `problems: []`, exit 0.
- **fx-03** test gagal: `input\RESULT.json` = `status: done` + `tests: [{name:"AC-2", result:"fail"}]`. Expected: `accepted_status: partial`, `problems` memuat `D6-5.3`.
- **fx-05** resume: folder workspace fixture berisi `PROGRESS.md` (2 dari 3 langkah) + `out.md` DIHAPUS. Expected: job dijalankan ulang melanjutkan dari langkah 3, hasil identik dengan fx-01, `RESULT.json` mencatat `resumed: true`. (Kalau menjalankan ulang butuh worker nyata dan tidak memungkinkan di lingkungan tes, tulis fixture sebagai data golden + test yang memverifikasi `PROGRESS.md` terbaca dan logika resume — tandai di README kalau butuh worker live.)

Tulis test pytest `test_fx01_fx03_fx05.py` yang menjalankan `die_accept.py` terhadap fixture (pola `test_fx02_fx04.py`). Jalankan dengan python 3.11 (`C:\Users\aethers\AppData\Local\Programs\Python\Python311\python.exe`).

### 2. `die-conformance.ps1` (B3.5 runner gabungan)

Buat `C:\DIE\bin\die-conformance.ps1` dengan param `-Out <path>`:
- Jalankan `python -m pytest C:\DIE\bridge\tests -q` (fx-06..fx-08 murni cepat).
- Gabungkan hasil ke satu JSON: `{run_at, pytest: {passed, failed, failed_names}, fixtures_checked: [...], verdict: "PASS"|"FAIL"}`.
- Tulis ke `-Out` (untuk conformance-d1.json / conformance-d7.json di B3).
- Pola gaya die_snapshot.ps1 (param `-Out`, stdlib, tanpa dependency).

### 3. Template `day-N.json` + `SCOREBOARD.md` (B3.3)

- Buat template `C:\DIE\state\organism-test\_template_day.json` sesuai skema B3.3 (day/date/phase/briefing/projection_accuracy/truth_vs_projection_drift/events/wake/boundary/proposals/heartbeat/fault_injection/source_trust_by_surface/notes) — semua field, nilai kosong/null.
- Buat template `C:\DIE\state\organism-test\_template_scoreboard.md` sesuai B3.3/SCOREBOARD (tabel 7 baris × metrik + kolom LULUS/GAGAL).

## Batas

- Python 3.11 stdlib. Jangan commit/push. Jangan ubah file bridge yang sudah verified (reader/schema_guard/projection/mcp_server/config).
- Jangan sentuh `C:\DIE\bin\die_cron.py`, `die_event.py`, `die_accept.py` (kecuali temuan nyata — laporkan, jangan langsung ubah).
- Fixture yang baru harus lolos `die_accept.py` EXISTING (jangan modifikasi die_accept.py).

## Laporan (timpa `C:\DIE\bridge\P1_REPORT.md`)

- Selesai: [file dibuat]
- Verifikasi: [pytest count, contoh output die_accept untuk fx-01/03, hasil die-conformance.ps1]
- Blocker: [kalau ada]