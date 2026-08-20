# BRIEFING P1 — income-os-bridge (untuk agent pelaksana)

> Dibuat: 2026-08-19 oleh OpenCode (integrator). Kerjakan P1 sesuai dokumen ini.
> Target: cline di pane w8:pF. Laporkan hasilnya ke integrator (OpenCode) di pane w8:pD.

## Konteks

Project **Digital Income Empire (DIE)**: Hermes v0.20.4 (NousResearch vanilla, tanpa fork) sebagai AI Economic Operator. Bridge `C:\DIE\bridge\` adalah lapisan observasi read-only yang menghubungkan Hermes ke lane kognitif (ChatGPT #A). Sudah ada P0 (config/events/envelope/redact/briefing/cli) — **jangan rusak**.

- Spec lengkap: `D:\Digital_Income_Empire\Docs\Claude Opus 5\deliverables\cleaned\v2\S2-B2-income-os-bridge-spec.md` (BACA INI DULU).
- Keputusan terkait: `D:\Digital_Income_Empire\Docs\Claude Opus 5\deliverables\cleaned\v2\S2-B4-Keputusan-dan-Tangga-Prioritas.md`.
- Konstitusi & AGENTS: `C:\DIE\CONSTITUTION.md`, `C:\DIE\AGENTS.md`.

## Fakta terverifikasi LIVE di VPS ini (KOREKSI spec — jangan ikuti spec buta)

Hermes binary: `C:\Users\aethers\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`

| Spec bilang | REALITAS (verified) |
|---|---|
| `hermes kanban list --json` | ✅ BISA (return `[]`, JSON valid) |
| `hermes cron list --json` | ❌ TIDAK didukung. Hanya `hermes cron list [--all]` (output tabel). **Tidak ada `--json`** |
| `hermes gateway status --json` | ❌ TIDAK didukung. Hanya `hermes gateway status [--deep] [-l] [--system]` (output teks) |
| `hermes session list --json` | ❌ Subcommand yang benar = `hermes sessions list [--source X] [--limit N] [--workspace X]` — TIDAK ada `--json`, output tabel |

Implikasi: `get_cron_jobs`, `get_gateway_status`, `get_sessions` **tidak bisa CLI-JSON-first**. Strategi yang benar: parse output tabel teks (buat parser per subcommand) ATAU langsung pakai fallback DB `mode=ro`. Keputusan parsing-vs-DB ada di tanganmu, tapi DB fallback WAJIB tetap ada dan schema_guard tetap aktif. `get_kanban_rows` bisa CLI-first (JSON) dengan DB fallback.

### Lokasi DB Hermes (fallback, mode=ro wajib)

- Kanban: `C:\Users\aethers\AppData\Local\hermes\kanban.db`
- State (sessions/FTS5): `C:\Users\aethers\AppData\Local\hermes\state.db`
- **PROFILE aktif = `income-operator`** → state juga bisa di `C:\Users\aethers\AppData\Local\hermes\profiles\income-operator\state.db` (cek dua-duanya, pilih yang ada datanya).
- Kronologi: profile default = vanilla; `income-operator` = identity DIE (SOUL/MEMORY/AGENTS). Profile sekarang default & gateway jalan di bawahnya (PID 17556).

### Gotcha yang baru saja difix (JANGAN regresi)

`die_cron.py` sempat gagal `WinError 2` saat dijalankan cron karena environment `HERMES_HOME` di-set ke folder profile oleh gateway → fallback `HERMES_HOME\hermes-agent\venv\Scripts\hermes.exe` tidak ketemu. Sudah difix: hard-code `HERMES_AGENT_ROOT = C:\Users\aethers\AppData\Local\hermes`. **Reader-mu jangan bergantung pada `HERMES_HOME` env var** untuk menemukan binary/db; gunakan path absolut terverifikasi di atas.

## Tugas P1 (urut)

1. **Verifikasi schema + CLI output** → tulis `C:\DIE\bridge\SCHEMA_NOTES.md`:
   - Jalankan `hermes kanban list --json`, `hermes cron list`, `hermes gateway status`, `hermes sessions list --limit 5`, dan dump schema DB (`PRAGMA table_info`) untuk kanban.db + state.db (read-only).
   - Catat bentuk output aktual + nama tabel/kolom + perintah yang berhasil. Ini bahan `EXPECTED` di schema_guard.
2. **Implement `hermes_state_reader.py`** (5 fungsi: kanban, sessions, cron, gateway, capabilities) sesuai kontrak `ReaderResult` di spec B2.2.1. Field kanonik TETAP (projection andalkan itu).
3. **Implement `schema_guard.py`** — fail-closed hash kolom (`sha256:<daftar kolom terurut>`), `EXPECTED` diisi dari SCHEMA_NOTES.md, drift → trust DEGRADED.
4. **Implement `projection.py`** — 8 surface baru (system_state, active_missions, mission_get, workers, scheduled_jobs, capabilities, search_sessions, session_get) + gabung dengan recent_events/system_health yang ada di events.py. Envelope wajib (spec B2.3.1), batas 32KB, redact di jalur keluar.
5. **Implement `access_log.py`** (ACCESS.jsonl: ts, tool, args_hash, result_bytes, completeness, source_trust, rejected) + **`mcp_server.py`** (stdio, 11 tool read-only, skema spec B2.6, error E_NO_RAW_ACCESS dll, rate limit 60/jam).
6. **Fixtures + test**: `fx-06` (system_health accuracy) + `fx-08` (no-raw-access, 6 payload injeksi SQL/path/shell ditolak) + `fx-08c` (redact kredensial) + `fx-08d` (tidak ada tulis di luar state\projection). Test pytest di `tests\`.
7. **Regression**: semua test lulus. `source_trust` naik ke VERIFIED untuk minimal kanban & cron (setelah SCHEMA_NOTES.md terisi + parser/reader dipatch).

## Batas keras (jangan langgar)

- Python 3.11, **stdlib saja** (nol dependency baru). Jalankan dengan `C:\Users\aethers\AppData\Local\Programs\Python\Python311\python.exe`.
- Seluruh bridge **≤ 900 baris Python** (hitung `income_os_bridge\*.py`). Lewat → STOP & eskalasi.
- `projection.py` STABIL: hanya baca field kanonik ReaderResult, DILARANG SQL/subprocess/open di luar state\. Jangan rusak kontrak ini.
- Read-only ketat: DB `mode=ro`, tidak ada INSERT/UPDATE/DELETE/ATTACH, `shell=False`, allowlist perintah, tidak ada `eval`/`exec`/`os.system`.
- **Tidak pernah menulis ke `state\EVENTS.jsonl` / DECISIONS / ECONOMICS.** Hanya `state\projection\`.
- Redact wajib di semua jalur keluar (`sk-`, key, token, secret, password, Bearer, .env).
- Jangan sentuh `C:\DIE\bin\die_cron.py` / die_event.py (sudah live & diverifikasi). Jangan fork/patch Hermes.

## Verifikasi akhir (wajib dilaporkan)

1. `python -m pytest tests -q` → semua pass (jalankan dari `C:\DIE\bridge`).
2. `python -m income_os_bridge system_health` → envelope valid, source_trust VERIFIED untuk kanban/cron.
3. `python -m income_os_bridge recent_events --limit 5` → masih jalan (P0 tidak rusak).
4. Satu demonstrasi mcp_server stdio: initialize → tools/list → satu tool call → respon envelope.

## Cara lapor (ke integrator/OpenCode w8:pD)

Ringkas, format:
- Selesai: [apa yang selesai, file mana]
- Verifikasi: [hasil pytest, contoh output]
- SCHEMA_NOTES.md: [ringkasan 5 baris bentuk schema aktual]
- Deviation dari spec: [apa yang beda + alasan]
- Blocker: [kalau ada]

JANGAN commit/push. JANGAN ubah di luar `C:\DIE\bridge\` dan `C:\DIE\logs\`.