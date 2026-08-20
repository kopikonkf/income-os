# D5 — PROTOCOLS/a2a-combus-chatgpt-hermes.md

<aside>
📁

Path repo: `PROTOCOLS/a2a-combus-chatgpt-hermes.md` · Kelas: protokol · Tunduk pada `CONSTITUTION.md` · Status: PHASE A (read-only) belum dijalankan

</aside>

Lapisan komunikasi semantik antara runtime cognition (compatibility name: ChatGPT #A) dan Hermes (operator), tanpa Founder sebagai perantara pesan. Canonical truth berada di DIE State Layer; dokumen ini mendefinisikan topologi, permukaan akses, primitif, dan gerbang fase.

## 1. Topologi dua lane

```
                          FOUNDER (sovereign)
                                 |
              approval / ratification / final decision
                                 |
  LANE 1 - COGNITIVE (low volume, human-like, ban-safe)
  ChatGPT #A  <--->  BrowserOS neo (MCP 127.0.0.1:9010, 18 tools)  <--->  HERMES
     architect          real Chromium, persistent login profile          operator
                        role: (a) wake actuator, (b) observe/propose
                        NO internal scheduler -> catch-up scheduled by Hermes cron

  LANE 2 - PRODUCTION (high volume, throughput-first)
  ChatGPT #B + web-chat AIs <---> Proxima V2 (127.0.0.1:3211, OpenAI-compatible)
                                  + OAuth project (:8456, 5 providers)   <---> HERMES
                        role: bulk generation of code/text/visual/template assets

                                 HERMES (one control plane)
                                 |         |          |
                            Kanban    cron/memory   WORKERS (opencode CLI)
                                                        |
                                                   ARTIFACT -> MARKET -> REVENUE
```

**Aturan pemisahan lane (tidak boleh dilanggar):**

|  | Lane 1 — Cognitive | Lane 2 — Production |
| --- | --- | --- |
| Peserta | ChatGPT #A (architect) | ChatGPT #B + web-chat AI |
| Transport | BrowserOS neo (browser asli) | Proxima V2 / OAuth multiplexer |
| Volume | Rendah, jarang, sadar-konteks | Tinggi, berulang, tanpa konteks strategis |
| Kebutuhan | Human-like, ban-safe, sesi login persisten | Throughput, endpoint OpenAI-compatible |
| Isi | Tesis, usulan, tantangan, keputusan | Asset, draft kode, template, teks produksi |
| Dilarang | Traffic produksi bervolume | Konteks strategis / Northstar / kredensial |

Alasan pemisahan: mengalirkan traffic architect lewat Proxima menghilangkan sifat human-like dan sesi persisten; mengalirkan volume produksi lewat browser asli menghancurkan throughput dan menaikkan risiko akun. Keduanya merusak.

## 2. Design rule: no-raw-access

ChatGPT #A **tidak pernah** mendapatkan: shell, filesystem, akses SQLite/DB, kredensial atau secret, kemampuan spawn/kill worker, penulisan langsung ke memory Hermes.

Alasan: substrat kognitif berada di lingkungan yang tidak dikendalikan (akun pihak ketiga, transport browser). Kompromi di sana tidak boleh berarti kompromi pada VPS.

Konsekuensi teknis: karena `hermes mcp serve` adalah **messaging bridge saja** — `conversations_list`, `conversation_get`, `messages_read`, `attachments_fetch`, `events_poll`, `events_wait`, `messages_send`, `channels_list`, `permissions_list_open`, `permissions_respond` — dan **bukan runtime introspection** (VERIFIED §2), maka dibutuhkan **Semantic Projection Layer**: projection service mengompilasi canonical DIE state bersama typed operational evidence dari Hermes menjadi pesan/artefak semantik yang dikirim lewat bridge. Proyeksi ini adalah satu-satunya jendela runtime cognition ke sistem.

Catatan status: ChatGPT Free terbukti secara empiris bisa terhubung ke custom MCP di lingkungan ini, tapi itu **environment-specific, bukan capability resmi** (VERIFIED §2). Protokol ini karena itu tidak boleh mengasumsikan konektivitas MCP langsung sebagai jaminan; jalur artefak (pesan + attachment lewat bridge) adalah jalur cadangan yang harus selalu berfungsi.

## 3. Minimum shared state (9 kategori)

Hanya sembilan kategori ini yang dibagikan. Apa pun di luar ini tidak masuk lane kognitif.

**Persistence invariant:** kolom authority/source di bawah tidak berarti physical writer. Seluruh canonical event, evidence, decision, mission state, telemetry ekonomi, dan projection checkpoint ditulis hanya oleh DIE State Manager setelah validasi.

| # | Kategori | Isi | Semantic authority/source | Akses runtime cognition |
| --- | --- | --- | --- | --- |
| 1 | **Northstar** | Mission, vision, constraints, autonomy level | Founder | read |
| 2 | **World** | Fakta lingkungan: infra yang ada, batas kemampuan, status transport | Hermes | read |
| 3 | **Empire** | Aset yang dimiliki: produk, channel, akun, artifact terkirim | Hermes | read |
| 4 | **Mission** | Mission aktif: goal, status, budget, kill criteria, job terkait | Hermes | read + propose |
| 5 | **Experiment** | Hipotesis berjalan, desain tes, hasil | Hermes | read + propose |
| 6 | **Decision ledger** | Keputusan + pemutus + alasan (append-only) | Authorized decider; Hermes dapat submit operational record | read |
| 7 | **Telemetry** | Biaya, throughput, tingkat kegagalan, waktu siklus | Hermes | read |
| 8 | **Event stream** | Kejadian berklasifikasi (§6) | Hermes | read |
| 9 | **Capability** | Daftar kemampuan + status VERIFIED/ASSUMED/ABSENT | Hermes | read |

## 4. Observation surface (read-only)

Dikompilasi dari canonical DIE State Layer plus typed operational evidence dari Hermes/runtime sources; tidak ada satu pun yang memberi akses mentah.

| Nama | Mengembalikan | Catatan |
| --- | --- | --- |
| `system_health` | Status Hermes, cron terakhir jalan, alarm aktif | Termasuk staleness lane kognitif |
| `system_state` | Autonomy level, batas aktif, mode degradasi | Ringkas |
| `active_missions` | Daftar mission + status + kill criteria | Tanpa detail job |
| `mission_get` | Satu mission: job, evidence, biaya, riwayat keputusan | Detail terbatas |
| `workers` | Worker terdaftar + status + reliabilitas ringkas | Tanpa akses kontrol |
| `scheduled_jobs` | Cron aktif + jadwal berikutnya | Read-only |
| `capabilities` | Kemampuan + status verifikasi | Basis perencanaan |
| `recent_events` | Event terbaru berklasifikasi | Untuk catch-up |
| `search_sessions` | Pencarian atas riwayat (FTS5) | Hasil terpotong |
| `session_get` | Satu sesi/percakapan operasional | Tanpa kredensial |

Aturan proyeksi: setiap respons menyertakan `as_of` (waktu) dan `completeness` (lengkap/terpotong). Data terpotong yang tidak ditandai adalah bug protokol.

## 5. Control surface (mutasi terbatas)

Hanya lima jalur mutasi, semuanya tidak destruktif dan semuanya tercatat.

| Nama | Efek | Batas |
| --- | --- | --- |
| `propose_mission` | Menambah usulan ke antrean; **bukan** commit | Wajib menyertakan kill criteria + jalur pembeli |
| `pause_mission` / `resume_mission` | Menjeda / melanjutkan mission | `resume` hanya untuk mission yang dijeda oleh usulan yang sama |
| `request_audit` | Meminta Hermes menyusun laporan audit | Rate-limited |
| `challenge_mission` | Menandai mission dipertanyakan → `paused` | Wajib menyertakan alasan + kill shot |
| `escalate` | Meneruskan keputusan ke Founder | Wajib satu keputusan, opsi, dan batas waktu |

**Eksklusi permanen (tidak boleh ada di surface mana pun, di fase mana pun):** eksekusi shell, tulis/hapus file, tulis ke database, akses atau pembuatan kredensial, kontrol worker (spawn/kill/reassign), pengiriman ke pasar, pengeluaran uang, perubahan dokumen konstitusional.

## 6. Communication primitives & semantic objects

### 6.1 Dua belas primitif

| Primitif | Pengirim | Arti | Balasan wajib |
| --- | --- | --- | --- |
| `OBSERVE` | ChatGPT #A | Ambil snapshot state | Snapshot + `as_of` |
| `QUERY` | ChatGPT #A | Pertanyaan spesifik atas state/riwayat | Jawaban + sumber |
| `PROPOSE` | ChatGPT #A | Usulan mission/eksperimen/perubahan | `accepted` / `rejected(alasan)` / `deferred(pemicu)` / `escalated` |
| `REQUEST` | ChatGPT #A | Minta audit/laporan | Jadwal atau hasil |
| `COMMIT` | Hermes | Mengikat mission menjadi truth | Event tercatat |
| `DELEGATE` | Hermes | Mengirim job ke worker | Job id |
| `REPORT` | Hermes | Hasil, evidence, telemetry | — |
| `SIGNAL` | Hermes | Event terklasifikasi, termasuk pemicu wake | — |
| `AUDIT` | keduanya | Pemeriksaan terstruktur atas keputusan/hasil | Temuan |
| `CHALLENGE` | keduanya | Sanggahan berargumen | Jawaban atau eskalasi |
| `LEARN` | keduanya | Pembelajaran yang mengubah artefak | Perubahan konkret |
| `ESCALATE` | keduanya | Serahkan ke Founder | Keputusan Founder |

Aturan: `COMMIT`, `DELEGATE`, `REPORT`, dan `SIGNAL` **hanya** boleh berasal dari Hermes. Jika muncul dari sisi kognitif, itu pelanggaran protokol → `ANOMALY`.

Dalam persistence boundary, `COMMIT` adalah semantic request dari Hermes, bukan direct storage write. Mission/decision/event baru canonical setelah DIE State Manager memvalidasi dan mengembalikan committed ID/version.

### 6.2 Objek semantik

| Objek | Field minimum |
| --- | --- |
| `MISSION` | id, goal, buyer_path, budget, deadline, **kill_criteria**, status, owner |
| `OPPORTUNITY` | id, hipotesis pasar, bukti, biaya uji termurah, risiko |
| `THESIS` | id, klaim, label bukti (FACT/EVIDENCE/INFERENCE/HYPOTHESIS/SPECULATION), falsifikasi |
| `DECISION` | id, pilihan, pemutus, alasan, alternatif yang ditolak, timestamp |
| `DIRECTIVE` | id, instruksi operasional dari Founder, ruang lingkup, batas |
| `EXPERIMENT` | id, hipotesis, desain, biaya, kriteria sukses, kriteria mati |
| `TELEMETRY` | periode, biaya, throughput, kegagalan, waktu siklus |
| `EVENT` | id, kelas, sumber, ringkasan, timestamp |
| `ANOMALY` | id, apa yang tak terduga, dampak, dugaan sebab, tindakan sementara |
| `AUDIT` | id, ruang lingkup, metode, temuan, rekomendasi |
| `LEARNING` | id, observasi, hipotesis, perubahan artefak, hasil setelahnya |

Setiap objek wajib punya id stabil dan tercatat di canonical DIE State Layer melalui State Manager. Objek yang hanya hidup di dalam percakapan tidak dianggap ada.

## 7. Event classification & cognitive gate

| Kelas | Contoh | Aksi |
| --- | --- | --- |
| `INFO` | Job selesai normal, cron jalan | Catat saja |
| `NOTICE` | Retry, sedikit di atas estimasi biaya | Catat, masuk ringkasan harian |
| `WARNING` | Job gagal berulang, worker melambat, evidence tidak lengkap | Masuk ringkasan + antrean catch-up |
| `CRITICAL` | Mission terhenti, kehilangan transport, biaya melampaui batas, pelanggaran batas authority | **WAKE** lane kognitif + eskalasi jika perlu |
| `STRATEGIC` | Pendapatan pertama masuk, kill criteria terpenuhi, sinyal pasar bertentangan dengan tesis | **WAKE** lane kognitif |

**Cognitive gate:** hanya `CRITICAL` dan `STRATEGIC` yang membangunkan ChatGPT #A. Sisanya menumpuk untuk catch-up. Alasannya ekonomis: substrat kognitif terbatas kuotanya, dan wake yang murah akan menjadi kebisingan.

## 8. Runtime & temporal asymmetry

- **Hermes:** berjalan 24/7, punya cron durable (VERIFIED).
- **ChatGPT #A:** dorman secara default; hanya hidup saat dibangunkan (Cognitive Wakefulness, D2 §12).
- **Aktuator wake:** BrowserOS neo — tool `run`/`evaluate` menyuntikkan sinyal wake ke sesi ChatGPT #A di browser asli, dengan laju yang human-like (VERIFIED §2).
- **Tidak ada scheduler di dalam lane browser** (VERIFIED). Semua penjadwalan berasal dari cron Hermes.

### Mode wake

| Mode | Kapan | Mekanisme | Status |
| --- | --- | --- | --- |
| **PULL v0** | Sekarang (PHASE A) | Sesi dibuka → ChatGPT #A menarik `recent_events`  • ringkasan catch-up; dijadwalkan dari cron Hermes | Rencana v0 |
| **PUSH v0.2+** | Setelah PHASE A terbukti | Hermes menyuntikkan `SIGNAL` saat event `CRITICAL`/`STRATEGIC` | Gated |

### Kegagalan yang wajib punya alarm

1. Lane kognitif **stale** lebih dari ambang → alarm ke Founder (ambang: `OPEN-P4`).
2. Wake terkirim tapi tidak ada balasan dalam N siklus → `ANOMALY`.
3. Snapshot proyeksi gagal dibuat → lane kognitif dianggap buta; Hermes masuk mode degradasi (hanya menyelesaikan mission yang sudah di-commit).

Catatan risiko (lihat Challenge C2): transport berbasis UI bisa gagal secara silent. Karena itu heartbeat lane kognitif adalah bagian dari protokol, bukan tambahan opsional.

## 9. Phase gating

| Fase | Ruang lingkup | Yang aktif | Gerbang keluar |
| --- | --- | --- | --- |
| **PHASE A — Read-only (Organism Test v0)** | Observasi saja | Observation surface, PULL wake, event classification, catch-up harian | Selama 7 hari berjalan: proyeksi akurat (cocok dengan event log), nol pelanggaran no-raw-access, minimal satu catch-up menghasilkan usulan yang berguna |
| **PHASE B — Controlled mutation** | Mutasi terbatas + PUSH | Control surface (propose/pause/resume/audit/challenge/escalate), PUSH wake untuk CRITICAL/STRATEGIC | 10 usulan diproses dengan balasan lengkap, nol mutasi di luar surface, nol aksi irreversible tanpa approval |
| **PHASE C — Full control (dalam batas)** | Otonomi lebih luas | Sesuai autonomy level A2/A3 di CONSTITUTION | Ditentukan Founder; tidak didefinisikan sekarang |

Aturan: fase tidak naik karena waktu berjalan, hanya karena gerbang terpenuhi dan Founder meratifikasi. Eksklusi permanen §5 berlaku di semua fase.

## 10. Open questions

- `OPEN-P1` Bentuk konkret Semantic Projection Layer di atas messaging bridge (skema pesan, ukuran maksimum, cara paginasi) belum ditentukan.
- `OPEN-P2` Bagaimana ChatGPT #A memverifikasi bahwa proyeksi tidak menyesatkan — tidak ada jalur verifikasi independen. Belum terpecahkan.
- `OPEN-P3` Apakah konektivitas MCP dari akun kognitif akan tetap tersedia; bersifat environment-specific (VERIFIED §2), jadi jalur cadangan berbasis pesan/attachment wajib ada. Ketahanannya belum diuji.
- `OPEN-P4` Ambang staleness dan jumlah siklus tanpa balasan sebelum `ANOMALY` belum ditetapkan.
- `OPEN-P5` Rate limit yang aman untuk aktuator wake (agar tetap human-like) belum diukur.
- `OPEN-P6` Cara mengikat identitas pesan antar lane (korelasi id) saat Lane 2 menghasilkan asset untuk mission yang dibahas di Lane 1 — belum dirancang.
- `OPEN-P7` Apakah `pause_mission` di tangan sisi kognitif bisa dipakai sebagai vektor denial-of-service tak sengaja; belum ada batas laju yang ditetapkan.