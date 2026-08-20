# P1_REPORT.md — Fix Encoding + Verifikasi Final + B3 Infrastructure

## Fix (NEXT_BRIEFING.md)
**File diubah:** `income_os_bridge/cli.py` (2 perubahan)

1. **Fix UnicodeEncodeError di stdout Windows** (baris 64-65): Ditambahkan `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` di awal `main()`. Windows default stdout encoding adalah cp1252, tidak bisa encode karakter non-ASCII seperti `→` (U+2192) yang ada di markdown BRIEFING.md. Reconfigure memaksa UTF-8 dengan fallback replace.

2. **Handle `None` return dari projection functions** (baris 23-31): `_proxy()` sekarang cek `if res is None` dan mengembalikan envelope error bersih (mirip MCP server: `E_NOT_FOUND`, `source_trust: ASSUMED`, `data: null`) вместо `null` mentah. Menaikkan konsistensi CLI dengan MCP stdio behavior.

## Verifikasi (NEXT_BRIEFING.md)
**pytest:** `python -m pytest tests -q` → **17 passed** (0 failed, 0 error)

**Surface CLI (semua 11 surface berjalan):**
- `briefing_get` → envelope `{as_of, markdown}` ✓ (karakter `→` ter-render benar)
- `system_health` → envelope VERIFIED ✓ (gateway, cron, alarms, cognitive_lane_stale_min)
- `recent_events --limit 5` → envelope ✓ (5 event, truncated=true)
- `mission_get --mission_id M-999` → error bersih envelope `E_NOT_FOUND`, **bukan stack trace** ✓
- `search_sessions --query halo` → envelope ✓ (2 hit, session_id + title)
- `session_get --session_id test` → error bersih envelope `E_NOT_FOUND` ✓
- `system_state` → envelope ASSUMED ✓
- `active_missions` → envelope VERIFIED ✓ (empty array)
- `workers` → envelope VERIFIED ✓ (empty array)
- `scheduled_jobs` → envelope VERIFIED ✓ (4 cron jobs)
- `capabilities` → envelope ASSUMED ✓ (11 capabilities)

**MCP stdio end-to-end test:**
```
initialize → tools/list (11 tools) → tools/call briefing_get → tools/call system_health → tools/call mission_get M-000
```
Semua langkah PASS. `mission_get M-000` mengembalikan `isError: true` dengan `E_NOT_FOUND: mission_id/session_id tidak ada` — **bukan stack trace**.

**BRIEFING.md regenerasi:** `python -m income_os_bridge briefing --out C:\DIE\state\projection` → berhasil, `source_trust: VERIFIED`, BRIEFING.md valid berisi 7 bagian, ≤ 8 KB.

---

## B3 Infrastructure (B3_BRIEFING.md)

### 1. Fixture fx-01, fx-03, fx-05 (Worker Contract — B3.5, D6 §7)

**File dibuat:**
- `tests/fixtures/fx-01/input/` — JOB.json, RESULT.json, changed-paths.json, sample.csv, convert_fx01.py, convert_test_fx01.py, out.md, PROGRESS.md, evidence/, expected.json, README.md
- `tests/fixtures/fx-03/input/` — JOB.json, RESULT.json (tests: fail), changed-paths.json, sample.csv, convert_fx03.py, convert_test_fx03.py, out.md, PROGRESS.md, evidence/, expected.json, README.md
- `tests/fixtures/fx-05/input/` — JOB.json, RESULT.json (resumed: true), changed-paths.json, sample.csv, convert_fx05.py, convert_test_fx05.py, out.md, PROGRESS.md (2/6 langkah), evidence/, expected.json, README.md

**Test file:** `tests/test_fx01_fx03_fx05.py` (3 test functions)

**Hasil pytest:** 20 passed (17 existing + 3 new)

**Verifikasi die_accept.py:**
- fx-01 (happy path): `accepted_status: done`, `problems: []`, exit 0 ✓
- fx-03 (test fail): `accepted_status: partial`, `problems` memuat `D6-5.3`, exit 2 ✓
- fx-05 (resume golden): `accepted_status: done`, `resumed: true`, PROGRESS.md terbaca ✓

### 2. `die-conformance.ps1` (B3.5 runner gabungan)

**File dibuat:** `C:\DIE\bin\die-conformance.ps1`

**Fungsi:** Jalankan `python -m pytest C:\DIE\bridge\tests -q` → gabungkan hasil ke JSON `{run_at, pytest: {passed, failed, failed_names}, fixtures_checked: [...], verdict: "PASS"|"FAIL"}` → tulis ke `-Out`

**Hasil test:**
```
PS> powershell -File C:\DIE\bin\die-conformance.ps1 -Out C:\DIE\state\projection\conformance-d1.json
Verdict: PASS (20 passed, 0 failed)

PS> powershell -File C:\DIE\bin\die-conformance.ps1 -Out C:\DIE\state\projection\conformance-d7.json
Verdict: PASS (20 passed, 0 failed)
```

**Output JSON contoh:**
```json
{
  "run_at": "2026-08-19T08:42:37.6534781+00:00",
  "fixtures_checked": ["fx-01","fx-02","fx-03","fx-04","fx-05","fx-06","fx-07","fx-08","fx-08c","fx-08d"],
  "pytest": {"failed_names": [], "failed": 0, "passed": 20},
  "verdict": "PASS"
}
```

### 3. Template `day-N.json` + `SCOREBOARD.md` (B3.3)

**File dibuat:**
- `C:\DIE\state\organism-test\_template_day.json` — Skema lengkap B3.3: day/date/phase/briefing/projection_accuracy/truth_vs_projection_drift/events/wake/boundary/proposals/heartbeat/fault_injection/source_trust_by_surface/notes (semua field null/kosong)
- `C:\DIE\state\organism-test\_template_scoreboard.md` — Tabel 7 metrik × 7 hari + kolom LULUS/GAGAL + ringkasan keputusan gerbang

## Verifikasi Akhir
- `python -m pytest tests -q` → **20 passed** (0 failed)
- `python -m income_os_bridge briefing_get` → envelope OK, UTF-8 OK
- `python -m income_os_bridge system_health` → envelope VERIFIED
- `die-conformance.ps1` → PASS (20/20) untuk d1 dan d7

## Blocker
Tidak ada blocker. Semua tugas NEXT_BRIEFING.md dan B3_BRIEFING.md selesai.