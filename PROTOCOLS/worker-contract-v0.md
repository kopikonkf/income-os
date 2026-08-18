# D6 — PROTOCOLS/worker-contract-v0.md

<aside>
📁

Path repo: `PROTOCOLS/worker-contract-v0.md` · Ekstrak standalone dari `IDENTITY/hermes-operator/AGENTS.md` §5 (sumber kanonik) · Berlaku untuk semua worker CLI

</aside>

Kontrak antara Hermes (orchestrator) dan Worker (employee terikat kontrak). Worker v0: **opencode CLI**, satu worker aktif.

## 1. Prinsip

1. **Worker punya job, bukan mission.** Worker tidak menerima Northstar, strategi, nama pelanggan, atau konteks pasar.
2. **"done" tanpa evidence = blocked.** Tanpa pengecualian, tanpa negosiasi.
3. **Idempotent & resumable.** Child agent tidak durable (VERIFIED §2 brief: restart = batal), jadi job harus bisa dijalankan ulang tanpa merusak dan bisa dilanjutkan dari artifact terakhir.
4. **Satu job = satu workspace = satu artifact utama.**
5. **Least privilege.** Tanpa kredensial produksi, tanpa akses jaringan kecuali allowlist, tanpa tulis di luar workspace.
6. **Tidak boleh spawn worker lain.** Hanya Hermes yang mendelegasikan.

## 2. Input — Hermes → Worker

```json
{
  "task_id": "T-0001",
  "mission_id": "M-001",
  "goal": "Satu hasil yang dapat diverifikasi, satu kalimat imperatif",
  "context": "Fakta minimum untuk mengerjakan. Tanpa strategi, tanpa Northstar, tanpa data pelanggan.",
  "workspace": "/workspaces/T-0001",
  "constraints": {
    "time_budget_min": 30,
    "allowed_paths": ["/workspaces/T-0001"],
    "network": "none",
    "forbidden": [
      "credentials",
      "market submission",
      "spawning workers",
      "writes outside workspace",
      "destructive operations"
    ]
  },
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "statement": "Kriteria yang bisa dicek secara mekanis",
      "verify_with": "perintah, file, atau output yang membuktikannya"
    }
  ]
}
```

**Aturan penyusunan input:**

- `goal` harus bisa dinilai benar/salah tanpa penafsiran strategis.
- Setiap `acceptance_criteria` wajib punya `verify_with`. Kriteria tanpa cara verifikasi tidak boleh dikirim.
- `context` sekecil mungkin. Jika worker butuh tahu "mengapa", job-nya salah disusun.

## 3. Output — Worker → Hermes

```json
{
  "task_id": "T-0001",
  "status": "done | partial | blocked | failed",
  "summary": "Apa yang dikerjakan, faktual dan singkat",
  "artifact": [
    { "path": "relatif/terhadap/workspace", "kind": "file | dir | patch", "description": "" }
  ],
  "evidence": [
    {
      "type": "command_output | file_diff | log | screenshot",
      "ref": "path atau lokasi log",
      "claim": "kriteria mana yang dibuktikan (mis. AC-1)"
    }
  ],
  "tests": [
    { "name": "", "command": "", "result": "pass | fail", "output_ref": "" }
  ],
  "errors": [
    { "where": "", "message": "", "retryable": true }
  ],
  "next_action": "Satu langkah berikutnya yang disarankan, atau null"
}
```

## 4. Semantik status

| Status | Arti | Syarat |
| --- | --- | --- |
| `done` | Semua acceptance criteria terpenuhi dan terbukti | Setiap AC punya evidence/test; semua test `pass` |
| `partial` | Sebagian AC terpenuhi | Sebutkan AC mana yang belum, dan kenapa |
| `blocked` | Tidak bisa lanjut karena sesuatu di luar kendali worker | Sebutkan penghalangnya secara konkret |
| `failed` | Dicoba dan gagal | Sertakan error + apakah retryable |

## 5. Aturan verifikasi Hermes (gerbang penerimaan)

Hermes menjalankan pemeriksaan ini sebelum menerima hasil. Setiap kegagalan pemeriksaan dicatat sebagai event.

1. `done` dengan `evidence` kosong → **dipaksa menjadi `blocked`** + event `ANOMALY`.
2. Ada acceptance criterion tanpa evidence/test yang memetakannya → turun ke `partial`.
3. Ada test dengan `result: "fail"` → tidak boleh `done`.
4. Artifact disebut tapi tidak ada di workspace → `failed`.
5. Ditemukan tulisan di luar `allowed_paths` → job ditolak, worker dihentikan, event `ANOMALY`, eskalasi ke Founder.
6. Ada tanda upaya menyentuh kredensial atau melakukan submission → pelanggaran kontrak; job ditolak dan dieskalasi.
7. Melewati `time_budget_min` tanpa heartbeat → `blocked`, bukan dibiarkan berstatus aktif.

## 6. Aturan resumability

- Worker menulis artifact dan evidence **saat berjalan**, bukan hanya di akhir. Pekerjaan yang hanya hidup di konteks child akan hilang saat restart.
- Setiap job punya berkas kemajuan sederhana di workspace (mis. `PROGRESS.md`) yang cukup bagi eksekusi berikutnya untuk melanjutkan tanpa mengulang dari nol.
- Job yang dijalankan ulang pada workspace yang sama tidak boleh menghasilkan duplikasi atau kerusakan (idempotent).

## 7. Conformance fixture (wajib — lihat Challenge C8)

Kontrak ini dianggap ditegakkan hanya jika ada berkas uji minimal di repo:

| Fixture | Input | Hasil yang diharapkan |
| --- | --- | --- |
| `fx-01-happy` | Job sederhana dengan 1 AC | `done` dengan evidence yang memetakan AC-1 |
| `fx-02-no-evidence` | Output mengklaim `done` tanpa evidence | Hermes mengubahnya menjadi `blocked` |
| `fx-03-failing-test` | Test `fail` tapi status `done` | Hermes menolak, status turun |
| `fx-04-out-of-scope-write` | Tulisan di luar `allowed_paths` | Job ditolak + eskalasi |
| `fx-05-restart` | Job diinterupsi lalu dijalankan ulang | Lanjut dari `PROGRESS.md`, tanpa duplikasi |

Tanpa fixture ini, kepatuhan kontrak adalah **ASSUMPTION**, bukan properti sistem.

## 8. Open questions

- `OPEN-W1` Ambang heartbeat per jenis job belum ditetapkan.
- `OPEN-W2` Bentuk sandbox/isolasi workspace di Windows belum diputuskan (lihat Challenge C4).
- `OPEN-W3` Kebijakan retry otomatis (berapa kali, dengan jeda berapa) belum ditetapkan.
- `OPEN-W4` Apakah `network: "allowlist"` diperlukan untuk job v0 pertama — belum diketahui sampai job nyata disusun.