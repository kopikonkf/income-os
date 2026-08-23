---
name: wake-executive
description: Send a STRATEGIC/CRITICAL report to the ChatGPT Executive (Plus account) via BrowserOS neo CDP :9110 (C:\DIE\bin\wake_executive.py). Use sparingly per Executive wake gate - max 4/day, gap >= 90 minutes, only for CRITICAL or STRATEGIC company-wide matters. Outbound VPS->chatgpt.com; NOT part of Runtime MCP.
---

# wake_executive

Kirim laporan STRATEGIS/CRITICAL ke ChatGPT Executive (akun Plus, observability
company-wide) lewat BrowserOS neo.

## Gate WAJIB dipatuhi

- Max **4 wake/hari**, gap antar-wake **>= 90 menit**.
- Hanya untuk hal **CRITICAL** (insiden/blocker company) atau **STRATEGIC**
  (milestone, keputusan desain yang butuh visibilitas/verdict Executive).
- Bukan untuk update rutin - update rutin lewat Kanban/event kanonik.

## Cara pakai

```powershell
# Kirim ke thread pinned Executive (default)
python C:\DIE\bin\wake_executive.py "<laporan ringkas>"

# Thread baru + pin (jarang - kalau konteks thread bengkak)
python C:\DIE\bin\wake_executive.py --new "<laporan>"

# Lihat percakapan terbaru (probe tanpa kirim)
python C:\DIE\bin\wake_executive.py --list
```

Prasyarat: BrowserOS neo running (CDP :9110). Kalau gagal konek, cek proses
BrowserClaw/chrome - BrowserOS dikelola terpisah, jangan restart sembarangan;
laporkan gagal wake ke Founder.

## Format laporan

Ringkas, struktur: (1) kabar utama 1-3 poin, (2) keputusan yang butuh
visibilitas/verdict, (3) artefak/referensi (PR/event id), (4) pertanyaan eksplisit
bila butuh verdict. Bahasa Indonesia atau English, maksimal ~200 kata.
Jangan kirim secret/token. Timeout balasan bisa lama (LLM) - beri slack 5 menit.
