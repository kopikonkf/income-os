# TUGAS CLINE BARU — FIX ENCODING + VERIFIKASI FINAL (untuk agent pelaksana)

> Target: cline (pane w8:pH, nama "cline-p1"). Kerjakan di `C:\DIE\bridge`. Laporkan via file `C:\DIE\bridge\P1_REPORT.md` (tulis pakai tool write file — jangan kirim ke pane, jangan pakai browseros-neo).

## Latar

P1 bridge sudah selesai (dikerjakan cline sebelumnya, 17 pytest PASS, source_trust VERIFIED). Tugas sync briefing.py/cli.py juga sudah selesai (source_trust VERIFIED, BRIEFING.md ter-regenerasi 07:00:44Z). Tapi ketemu **1 bug saat verifikasi final** yang harus kamu fix:

### BUG: `python -m income_os_bridge briefing_get` → UnicodeEncodeError

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 1406
```

Penyebab: output JSON (yang berisi karakter non-ASCII seperti `→` dari markdown BRIEFING.md) di-print ke stdout console Windows yang default-nya cp1252. JSON output harus UTF-8.

## Tugas (urut)

1. **Fix encoding di CLI**: di `income_os_bridge/cli.py` (atau `__main__.py`), sebelum print, tambahkan `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (Python 3.7+, tersedia). Pastikan ini dipanggil di awal `main()` atau di `_out()`. JANGAN menulis literal UTF-8 ke file config; cukup reconfigure stdout.

2. **Verifikasi semua surface lewat CLI**: jalankan dari `C:\DIE\bridge`:
   - `python -m income_os_bridge briefing_get` → HARUS berhasil (envelope {as_of, markdown})
   - `python -m income_os_bridge system_health` → envelope VERIFIED
   - `python -m income_os_bridge recent_events --limit 5` → envelope
   - `python -m income_os_bridge mission_get --mission_id M-999` → error bersih (E_NOT_FOUND / E_NO_RAW_ACCESS), TIDAK stack trace
   - `python -m income_os_bridge search_sessions --query halo` → envelope (bisa kosong)
   - `python -m income_os_bridge session_get --session_id test` → error bersih atau envelope

3. **Uji MCP stdio end-to-end** (tulis script test sekali pakai di temp):
   - initialize → tools/list (11 tool) → tools/call briefing_get → tools/call system_health → tools/call mission_get dengan mission_id `M-000` (error bersih, isError true, bukan stack trace)

4. **pytest**: `python -m pytest tests -q` dari `C:\DIE\bridge` → semua pass (17+). Kalau ada test baru untuk encoding, tambahkan.

5. **Pastikan BRIEFING.md valid**: `python -m income_os_bridge briefing --out C:\DIE\state\projection` → BRIEFING.md source_trust VERIFIED.

## Batas

- Python 3.11 stdlib saja (`C:\Users\aethers\AppData\Local\Programs\Python\Python311\python.exe`).
- Seluruh bridge ≤ 900 baris.
- Hanya ubah `income_os_bridge\cli.py`/`__main__.py` + `tests\` kalau perlu. Jangan ubah reader/schema_guard/projection/mcp_server tanpa alasan kuat.
- Jangan commit/push. Jangan sentuh `C:\DIE\bin\die_cron.py`.

## Laporan (timpa `C:\DIE\bridge\P1_REPORT.md`)

- Fix: [file diubah, satu paragraf]
- Verifikasi: [hasil pytest + output 3 surface + hasil MCP test]
- Blocker: [kalau ada]