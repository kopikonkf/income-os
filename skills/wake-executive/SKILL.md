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

# Rotasi thread + pin (jarang; hanya lewat lifecycle governance)
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

## Security dan thread governance

- BrowserOS neo session cukup untuk wake Executive; jangan membuat Codex OAuth
  credential terpisah hanya untuk jalur ini.
- CDP :9110 wajib loopback-only dan principal-dedicated. Treat browser profile,
  cookies, dan full CDP as credential-equivalent.
- Web JWT harus tetap di page context; jangan log, return, atau persist nilainya.
- `--new` hanya setelah thread aktif dicatat sebagai superseded; tepat satu
  canonical Executive thread boleh aktif.
- Thread adalah continuity memory container, bukan Company Truth.
- Pada auth/CDP failure: jangan blind retry; emit alarm sanitized dan eskalasi.
