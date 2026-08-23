---
name: wake-chatgpt
description: Send a briefing message to the Division-01 ChatGPT conversation via the wake path (C:\DIE\bin\wake_division01.py). Use when you need to wake/notify Division-01 with a briefing, task instruction, or question. Outbound VPS->chatgpt.com transport; NOT part of Runtime MCP.
---

# wake_chatgpt

Kirim briefing ke Division-01 (akun ChatGPT div01) di thread percakapan persisten.

## Kapan dipakai

- Perlu menyampaikan briefing/instruksi/pertanyaan ke Division-01 (intelligence director M-001).
- Wake = outbound VPS -> chatgpt.com. BUKAN tool Runtime MCP; jangan expose ke connector inbound.

## Cara pakai

```powershell
# Kirim ke thread pinned (default - konteks terakumulasi)
python C:\DIE\bin\wake_division01.py "<briefing text>"

# Mulai thread baru + pin (hanya kalau thread lama bengkak / reset topik)
python C:\DIE\bin\wake_division01.py --new "<briefing text>"

# Lihat percakapan terbaru
python C:\DIE\bin\wake_division01.py --list
```

Prasyarat: Brave profil "plus" running dengan remote debugging port 9333
(scheduled task "DIE Wake Brave CDP" ONLOGON menjalankan health check
`C:\DIE\bin\wake_brave_health.ps1`; jalankan manual script tsb kalau error
"E_CONNREFUSED" / gagal konek :9333).

Output: balasan teks assistant dari Division-01 (stderr berisi metadata
conversation_id). Timeout bisa panjang (balasan LLM), beri slack 5 menit.

Aturan isi briefing: bahasa jelas, satu topik per wake, sertakan konteks misi
(M-001) bila relevan. Jangan kirim secret/token lewat pesan ini.
