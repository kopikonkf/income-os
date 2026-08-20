# P2_RESEARCH.md — Riset Implementasi P2 income-os-bridge

> **Goal:** Siapkan riset P2 (HTTP read-only + FTS5 search) supaya siap saat Founder approve.
> **Status:** Riset read-only. TIDAK ada file bridge yang diubah.
> **Date:** 2026-08-19
> **Source:** Inspeksi langsung state.db (mode=ro), baca bridge code (P1), SCHEMA_NOTES.md, P1_REPORT.md

---

## 1. FTS5 Search di state.db

### 1.1 Status FTS5 — VERIFIED LIVE

| Item | Status | Keterangan |
|------|--------|-----------|
| FTS5 compiled into SQLite | ✅ ENABLED | `sqlite_compileoption_used("ENABLE_FTS5")` = 1 |
| Virtual table `messages_fts` | ✅ EXISTS | 27 rows (sama dengan messages) |
| Virtual table `messages_fts_trigram` | ✅ EXISTS | Trigram tokenizer, substring search |
| State DB path (profile) | ✅ VERIFIED | `C:\Users\aethers\AppData\Local\hermes\profiles\income-operator\state.db` (495 KB) |
| State DB path (default) | ✅ EXISTS | `C:\Users\aethers\AppData\Local\hermes\state.db` (1.2 MB) |
| Read-only access | ✅ WORKS | `mode=ro` via URI参数 |

### 1.2 Schema FTS5 — Detail

**messages_fts** (default tokenizer — word-level):
```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,        -- isi pesan (kolom utama)
    tool_name,      -- nama tool jika ada
    tool_calls,     -- tool calls JSON jika ada
    content='messages',          -- external content table
    content_rowid='id'           -- rowid mapping ke messages.id
)
```

**messages_fts_trigram** (trigram tokenizer — substring):
```sql
CREATE VIRTUAL TABLE messages_fts_trigram USING fts5(
    content,
    tool_name,
    tool_calls,
    content='messages_fts_trigram_src',  -- view, bukan tabel langsung
    content_rowid='id',
    tokenize='trigram'
)
```

**View:** `messages_fts_trigram_src` — source view untuk trigram table.

**Indexing:** FTS5 auto-sync dengan messages table (content-sync via external content). Setiap INSERT/UPDATE ke messages → otomatis update di messages_fts.

### 1.3 Query Pattern yang Terbukti Jalan

#### Basic MATCH (word-level):
```sql
SELECT rowid, rank, snippet(messages_fts, 0, '<b>', '</b>', '...', 30)
FROM messages_fts
WHERE messages_fts MATCH 'hermes'
ORDER BY rank
LIMIT 5;
```
**Hasil:** 2 rows ditemukan, snippet menampilkan context dengan highlight.

#### Phrase query:
```sql
SELECT rowid, rank
FROM messages_fts
WHERE messages_fts MATCH '"income operator"'
ORDER BY rank;
```
**Hasil:** 0 rows (karena phrase exact-match belum ada di corpus saat ini).

#### FTS5 + sessions JOIN (paling relevan untuk P2):
```sql
SELECT s.id as session_id, s.title, s.started_at,
       f.rank, snippet(messages_fts, 0, '<b>', '</b>', '...', 30)
FROM messages_fts f
JOIN messages m ON f.rowid = m.id
JOIN sessions s ON m.session_id = s.id
WHERE messages_fts MATCH 'kanban'
ORDER BY f.rank
LIMIT 5;
```
**Hasil:** 2 rows, session `20260818_174...` ditemukan. Ini adalah query pattern utama untuk `search_sessions` di P2.

#### Trigram (substring match):
```sql
SELECT rowid, rank, snippet(messages_fts_trigram, 0, '<b>', '</b>', '...', 30)
FROM messages_fts_trigram
WHERE messages_fts_trigram MATCH 'cron job'
ORDER BY rank;
```
**Hasil:** 0 rows (trigram lebih cocok untuk substring panjang, bukan kata pendek).

### 1.4 Rekomendasi Query untuk P2 `search_sessions`

**Primary query (FTS5 word match):**
```sql
SELECT s.id, s.title, s.started_at, s.profile_name,
       f.rank, snippet(messages_fts, 0, '>>>', '<<<', '...', 40) as snippet
FROM messages_fts f
JOIN messages m ON f.rowid = m.id
JOIN sessions s ON m.session_id = s.id
WHERE messages_fts MATCH :query
ORDER BY f.rank
LIMIT :limit;
```

**Fallback (LIKE — jika FTS5 gagal atau query non-text):**
```sql
SELECT s.id, s.title, s.started_at, s.profile_name,
       m.content as snippet
FROM messages m
JOIN sessions s ON m.session_id = s.id
WHERE m.content LIKE '%' || :query || '%'
ORDER BY m.timestamp DESC
LIMIT :limit;
```

**Session-level search (metadata only, tanpa FTS5):**
```sql
SELECT id, title, display_name, profile_name, started_at, message_count
FROM sessions
WHERE title LIKE '%' || :query || '%'
   OR display_name LIKE '%' || :query || '%'
ORDER BY started_at DESC
LIMIT :limit;
```

### 1.5 Limitasi FTS5 yang Perlu Diketahui

| Limitasi | Dampak | Mitigasi |
|----------|--------|----------|
| FTS5 hanya index `content`, `tool_name`, `tool_calls` dari messages | Tidak bisa search by role, timestamp, atau session metadata | Gabungkan FTS5 result dengan sessions table via JOIN |
| Phrase query membutuhkan exact word sequence | `"income operator"` tidak match `"income-operator"` | Gunakan OR: `"income" "operator"` atau trigram |
| Trigram tokenizer: token minimum 3 karakter | Query 1-2 karakter gagal | Fallback ke LIKE untuk query pendek |
| FTS5 rank = negatif (semakin kecil = semakin relevan) | Perlu invert untuk display | `ABS(rank)` atau `1/(1+ABS(rank))` untuk score |
| External content sync: INSERT ke messages tidak auto-sync ke FTS | Bergantung pada Hermes runtime yang melakukan sync | Verifikasi periodic: `COUNT(*)` messages vs FTS |

---

## 2. HTTP Read-Only Stdlib — Rancangan Endpoint

### 2.1 Pola dari Spec B2.0 P2

P2 menambahkan HTTP transport di samping MCP stdio (P1). HTTP = untuk akses dari luar VPS (misal: ChatGPT #A via BrowserOS neo). MCP stdio = tetap untuk internal bridge.

### 2.2 Rancangan Endpoint

```
BIND: 127.0.0.1:8457 (localhost only — tidak expose ke jaringan)
AUTH: Bearer token (header Authorization: Bearer <token>)
FORMAT: JSON (Content-Type: application/json)
```

| Endpoint | Method | Deskripsi | Rate Limit |
|----------|--------|-----------|------------|
| `/health` | GET | Status bridge + uptime + version | 60/min |
| `/v1/surface/{name}` | GET | Baca observation surface (read-only) | 60/min |
| `/v1/surface/{name}` | POST | Baca surface dengan args (POST body = JSON args) | 60/min |
| `/v1/events` | GET | Event stream (query params: since_seq, limit, min_class) | 30/min |
| `/v1/search` | POST | Full-text search sessions (body: {query, limit}) | 20/min |
| `/v1/briefing` | GET | Baca BRIEFING.md terakhir | 10/min |

### 2.3 Implementasi — Pseudocode stdlib

```python
# P2: http_server.py — HTTP read-only endpoint
# Menggunakan http.server stdlib, TIDAK ada dependency tambahan

import json
import hashlib
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from . import config, projection, access_log

BEARER_TOKEN = None  # Dari config atau env var — LIHAT §4

class ReadOnlyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging; gunakan ACCESS.jsonl

    def _check_auth(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return False
        token = auth[7:]
        if not BEARER_TOKEN:
            return False
        return hashlib.compare_digest(token, BEARER_TOKEN)

    def _json_response(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._check_auth():
            return self._json_response(401, {"error": "unauthorized"})

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)

        if path == '/health':
            result = projection.system_health()
        elif path == '/v1/briefing':
            result = projection.briefing_get()
        elif path.startswith('/v1/surface/'):
            name = path.split('/')[-1]
            result = self._dispatch_surface(name, {})
        elif path == '/v1/events':
            result = projection.recent_events(
                since_seq=int(params.get('since_seq', [0])[0]),
                limit=int(params.get('limit', [50])[0]),
                min_class=params.get('min_class', ['INFO'])[0]
            )
        else:
            return self._json_response(404, {"error": "not found"})

        access_log.log(f"HTTP GET {path}", {}, len(json.dumps(result)), "complete", "VERIFIED")
        return self._json_response(200, result)

    def do_POST(self):
        if not self._check_auth():
            return self._json_response(401, {"error": "unauthorized"})

        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > config.MAX_RESP_BYTES:
            return self._json_response(413, {"error": "too large"})

        body = self.rfile.read(content_length)
        try:
            args = json.loads(body) if body else {}
        except:
            return self._json_response(400, {"error": "invalid json"})

        if path.startswith('/v1/surface/'):
            name = path.split('/')[-1]
            result = self._dispatch_surface(name, args)
        elif path == '/v1/search':
            result = projection.search_sessions(
                query=args.get('query', ''),
                limit=args.get('limit', 10)
            )
        else:
            return self._json_response(404, {"error": "not found"})

        access_log.log(f"HTTP POST {path}", args, len(json.dumps(result)), "complete", "VERIFIED")
        return self._json_response(200, result)

    def _dispatch_surface(self, name, args):
        dispatch = {
            'system_health': lambda a: projection.system_health(),
            'system_state': lambda a: projection.system_state(),
            'active_missions': lambda a: projection.active_missions(a.get('status', 'active')),
            'mission_get': lambda a: projection.mission_get(a.get('mission_id', '')),
            'workers': lambda a: projection.workers(),
            'scheduled_jobs': lambda a: projection.scheduled_jobs(),
            'capabilities': lambda a: projection.capabilities(a.get('status', 'any')),
            'recent_events': lambda a: projection.recent_events(
                a.get('since_seq', 0), a.get('limit', 50), a.get('min_class', 'INFO')),
            'search_sessions': lambda a: projection.search_sessions(
                a.get('query', ''), a.get('limit', 10)),
            'session_get': lambda a: projection.session_get(
                a.get('session_id', ''), a.get('max_turns', 20)),
        }
        handler = dispatch.get(name)
        if not handler:
            return {"error": f"surface '{name}' not found"}
        return handler(args)

def serve(host='127.0.0.1', port=8457):
    global BEARER_TOKEN
    BEARER_TOKEN = config.HTTP_BEARER_TOKEN
    server = HTTPServer((host, port), ReadOnlyHandler)
    server.serve_forever()
```

### 2.4 Perbedaan P1 (MCP stdio) vs P2 (HTTP)

| Aspek | P1 (MCP stdio) | P2 (HTTP) |
|-------|----------------|-----------|
| Transport | stdin/stdout JSON-RPC | HTTP/1.1 JSON |
| Auth | Tidak ada (local process) | Bearer token |
| Bind | Tidak ada (stdio) | 127.0.0.1:8457 |
| Rate limit | 60/jam (in-memory) | 60/jam per endpoint (in-memory) |
| Access log | ACCESS.jsonl (7 field) | ACCESS.jsonl (7 field, identik) |
| Tools | 11 tools | 10 endpoints (mirip) |
| Use case | Internal bridge (Hermes cron, CLI) | External access (BrowserOS neo, ChatGPT #A) |

---

## 3. Rate Limit & Access Log — Integrasi

### 3.1 Format ACCESS.jsonl yang Sudah Ada

```json
{"ts":"2026-08-19T05:08:28Z","tool":"system_health","args_hash":"44136fa355b3678a","result_bytes":1652,"completeness":"complete","source_trust":"VERIFIED","rejected":false}
```

**7 field (VERIFIED live, 9 records):**

| Field | Tipe | Deskripsi |
|-------|------|-----------|
| `ts` | string | ISO 8601 UTC timestamp |
| `tool` | string | Nama surface/endpoint yang dipanggil |
| `args_hash` | string | SHA256 hash args (16 char) — untuk audit tanpa expose isi |
| `result_bytes` | int | Ukuran response body dalam bytes |
| `completeness` | string | `complete` / `truncated` / `degraded` / `rejected` |
| `source_trust` | string | `VERIFIED` / `ASSUMED` / `DEGRADED` |
| `rejected` | bool | true = request ditolak (validation/rate limit) |

### 3.2 Integrasi P2 HTTP dengan ACCESS.jsonl

P2 HTTP server **wajib** menulis ke ACCESS.jsonl yang sama. Format identik. Penambahan field opsional untuk HTTP:

```json
{
  "ts": "2026-08-19T09:00:00Z",
  "tool": "HTTP GET /v1/surface/system_health",
  "args_hash": "44136fa355b3678a",
  "result_bytes": 1652,
  "completeness": "complete",
  "source_trust": "VERIFIED",
  "rejected": false,
  "transport": "http",
  "client_ip": "127.0.0.1"
}
```

**Catatan:** Field `transport` dan `client_ip` adalah ADDITION, bukan replacement. Field lama tetap kompatibel. Parser yang ada (projection.py) tidak terpengaruh.

### 3.3 Rate Limiting — Rancangan

```
Current P1: RateLimit class in mcp_server.py
  - deque-based, 60 requests per 3600s window
  - In-memory only (tidak persist antar restart)

P2 HTTP: Rate limit per endpoint
  - endpoint_keys: {"GET /health": deque, "GET /v1/events": deque, ...}
  - Limit: 60/min untuk read endpoints, 20/min untuk search
  - In-memory (sama dengan P1 — acceptable karena bridge single-process)
```

### 3.4 Monitoring via ACCESS.jsonl

Query untuk monitor usage:
```python
# Total requests per jam
# Total rejected per jam
# Surface mana yang paling banyak dipanggil
# Source trust distribution
# Response size distribution
```

---

## 4. Keputusan yang Harus Diambil Founder Sebelum P2

### DECISION-P2-1: Buka Port HTTP?

| Opsi | Pro | Con |
|------|-----|-----|
| **A: 127.0.0.1:8457 (localhost only)** | Aman dari jaringan luar | Hanya bisa diakses dari VPS itu sendiri |
| **B: 0.0.0.0:8457 (all interfaces)** | Bisa diakses dari luar VPS | Exposure ke jaringan — bahkan dengan bearer token |
| **C: 127.0.0.1 + SSH tunnel** | Akses dari luar via SSH | Butuh SSH setup di BrowserOS neo / ChatGPT #A |

**Rekomendasi:** Opsi A (localhost) dulu. BrowserOS neo berjalan di VPS yang sama → bisa akses 127.0.0.1 langsung. Jika perlu akses dari luar, tambah SSH tunnel nanti.

**Status:** MENUNGGU KEPUTUSAN FOUNDER

### DECISION-P2-2: Bearer Token

| Opsi | Pro | Con |
|------|-----|-----|
| **A: Random string 32 char** | Simpel, cukup aman untuk localhost | Static, tidak bisa rotate tanpa restart |
| **B: HMAC-based token** | Bisa rotate tanpa restart | Lebih kompleks |
| **C: No auth (localhost only)** | Paling simpel | Tidak ada audit trail per-client |

**Rekomendasi:** Opsi A. Generate token acak, simpan di `config.py` atau env var. Karena hanya localhost, risiko rendah. Token = authentication, bukan authorization (semua surface read-only).

**Status:** MENUNGGU KEPUTUSAN FOUNDER

### DECISION-P2-3: MCP Langsung dari Akun Kognitif — Terbukti Stabil?

| Fakta | Status |
|-------|--------|
| ChatGPT Free bisa connect ke custom MCP | ✅ VERIFIED (environment-specific, HANDOFF.md) |
| Konektivitas MCP dari akun kognitif stabil | ⚠️ BELUM DIUJI dalam waktu lama |
| ChatGPT Plus/Pro untuk stability | ⚠️ BELUM DIVERIFIKASI |
| BrowserOS neo sebagai actuator wake | ✅ VERIFIED (port :9010, 18 tools) |

**Pertanyaan untuk Founder:**
1. Apakah ChatGPT #A yang dipakai sekarang Free atau Plus/Pro?
2. Apakah konektivitas MCP sudah diuji dalam mode production (bukan cuma test)?
3. Jika MCP dari akun kognitif tidak stabil, apakah fallback ke artifact path (pesan + attachment) cukup?

**Status:** MENUNGGU KEPUTUSAN FOUNDER + VERIFIKASI

### DECISION-P2-4: Prioritas P2 vs Organism Test

| Opsi | Pro | Con |
|------|-----|-----|
| **A: P2 duluan sebelum Phase A** | HTTP ready saat Phase A dimulai | Tunda Phase A |
| **B: Phase A duluan, P2 paralel** | Phase A tidak tertunda | Phase A harus pakai MCP stdio (P1) saja |
| **C: Phase A + P2 bersamaan** | Paralel = cepat | Resource split, risiko bug lebih tinggi |

**Rekomendasi:** Opsi B. Phase A (Organism Test) = priority utama. P2 HTTP = enhancement, bisa ditambahkan setelah Phase A terbukti jalan. MCP stdio (P1) sudah cukup untuk Phase A.

**Status:** MENUNGGU KEPUTUSAN FOUNDER

---

## 5. Gap Antara P1 (Sudah Ada) dan P2 (Rencana)

| Komponen | P1 Status | P2 Kebutuhan | Gap |
|----------|-----------|-------------|-----|
| **Transport** | MCP stdio (stdin/stdout) | HTTP (127.0.0.1:8457) | Baru — perlu `http_server.py` |
| **Auth** | Tidak ada (local process) | Bearer token | Baru — perlu token generation + middleware |
| **FTS5 search** | Substring LIKE (projection.py) | FTS5 MATCH + snippet | Upgrade — ganti `search_sessions` implementation |
| **Access log** | ✅ Sama | ✅ Sama (tambah field `transport`) | Minor addition |
| **Rate limit** | ✅ 60/jam in-memory | ✅ 60/jam per-endpoint | Upgrade — per-endpoint tracking |
| **Surfaces** | 11 tools | 10 endpoints (mirip) | Mapping hampir 1:1 |
| **Envelope** | ✅ as_of/completeness/source_trust | ✅ Sama | Tidak ada perubahan |
| **Schema guard** | ✅ fail-closed | ✅ Sama | Tidak ada perubahan |
| **Redact** | ✅ credential/pattern redaction | ✅ Sama | Tidak ada perubahan |

### Estimasi Komponen Baru P2

| File | Estimasi Baris | Fungsi |
|------|---------------|--------|
| `http_server.py` | ~150 | HTTP server + routing + auth middleware |
| `config.py` (update) | +10 | HTTP_BEARER_TOKEN, HTTP_PORT, per-endpoint limits |
| `hermes_state_reader.py` (update) | +30 | FTS5 query functions (search_fts5, snippet) |
| `projection.py` (update) | +15 | Upgrade `search_sessions` ke FTS5 |
| `test_http.py` (baru) | ~80 | HTTP endpoint tests |
| **Total** | ~285 baris | Di atas P1 existing (849 baris) |

---

## 6. Rencana Implementasi P2 (Ketika Founder Approve)

```
LANGKAH 1: Generate bearer token
    → python -c "import secrets; print(secrets.token_urlsafe(32))"
    → Simpan di config.py atau .env

LANGKAH 2: Buat http_server.py
    → ReadOnlyHandler class
    → Auth middleware (bearer token check)
    → Routing: /health, /v1/surface/{name}, /v1/events, /v1/search, /v1/briefing
    → Rate limit per-endpoint
    → ACCESS.jsonl logging

LANGKAH 3: Upgrade search_sessions ke FTS5
    → Tambah fungsi search_fts5() di hermes_state_reader.py
    → Update projection.search_sessions() → FTS5 primary, LIKE fallback
    → snippet() untuk highlight

LANGKAH 4: Update config.py
    → HTTP_BEARER_TOKEN
    → HTTP_PORT = 8457
    → Per-endpoint rate limits

LANGKAH 5: Test
    → pytest test_http.py
    → Manual test: curl http://127.0.0.1:8457/health
    → Verify ACCESS.jsonl entries

LANGKAH 6: Register sebagai Windows service / scheduled task
    → Mirip dengan gateway: auto-start on login
    → Port 8457, bind 127.0.0.1
```

---

## 7. Catatan Penting

1. **TIDAK ada file bridge yang diubah dalam riset ini.** Semua inspeksi = read-only (mode=ro, baca code).
2. **FTS5 sudah terbukti jalan.** Tidak perlu install modul tambahan. Query pattern sudah diuji live.
3. **P2 = additive, bukan replacement.** MCP stdio (P1) tetap jalan. HTTP (P2) = transport tambahan.
4. **BrowserOS neo bisa akses 127.0.0.1:8457** karena berjalan di VPS yang sama. Tidak perlu exposed port.
5. **ACCESS.jsonl format existing sudah cukup.** Penambahan `transport` dan `client_ip` = backward compatible.

---

*Riset ini siap diperiksa Founder. Keputusan §4 adalah blocker untuk implementasi P2.*
