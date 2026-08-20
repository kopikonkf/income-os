# SCHEMA_NOTES.md — hasil verifikasi schema aktual Hermes (P1, 2026-08-19)

Semua diverifikasi LIVE di VPS ini. Hash di `schema_guard.EXPECTED` diambil dari
daftar kolom di bawah (PRAGMA table_info, urutan deklarasi).

## 1. Bentuk output CLI (perintah yang BERHASIL)

| Perintah | Hasil | Catatan |
|---|---|---|
| `hermes kanban list --json` | `[]` (JSON valid) | JSON-first aman. Kolom card: `card_id/title/status/...` (kosong saat ini) |
| `hermes cron list` | Tabel teks | TIDAK ada `--json`. Tiap job: blok `<id> [active]` + `Name/Schedule/Next run/Last run/Deliver/Script/Mode/Workdir`. Parser: `_parse_cron` di reader |
| `hermes gateway status` | Teks | TIDAK ada `--json`. Berisi `Status: Ready` + `Gateway process running (PID: <n>)` |
| `hermes sessions list --limit N` | Tabel teks | TIDAK ada `--json`. Kolom: `Title/Workspace/Last Active/ID`. "Last Active" relatif ("23m ago") → tidak bisa jadi ISO → DB-first untuk sessions |

Provider/model diambil dari `config.yaml` (blok `model:` → `default`/`provider`),
bukan dari output gateway.

## 2. Schema DB fallback (mode=ro)

### `kanban.db` → tabel `tasks` (kartu = `kanban list`)
36 kolom (hash `sha256:eaf50a10...e0d0`):
`id, title, body, assignee, status, priority, created_by, created_at, started_at,
completed_at, workspace_kind, workspace_path, branch_name, project_id, claim_lock,
claim_expires, tenant, result, idempotency_key, consecutive_failures, worker_pid,
last_failure_error, max_runtime_seconds, last_heartbeat_at, current_run_id,
workflow_template_id, current_step_key, skills, model_override, provider_override,
reasoning_effort, max_retries, goal_mode, goal_max_turns, session_id, block_kind,
block_recurrences`

Pemetaan ke field kanonik: `id→card_id/task_id`, `last_heartbeat_at→heartbeat_at`,
`created_at/started_at/completed_at→created_at/updated_at`, `assignee→assignee`.
`mission_id` & `kill_criteria` TIDAK ADA di schema → `None` (ANOMALI tercatat di bawah).
Timestamp = epoch float → di-ISO-kan di reader.

### `state.db` (default) & `profiles\income-operator\state.db` → tabel `sessions`
55 kolom (hash `sha256:b3863e8c...e837`):
`id, source, user_id, session_key, chat_id, chat_type, thread_id, display_name,
origin_json, expiry_finalized, model, model_config, system_prompt, system_prompt_hash,
parent_session_id, started_at, ended_at, end_reason, message_count, tool_call_count,
input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens,
cwd, git_branch, git_repo_root, git_metadata_generation, billing_provider,
billing_base_url, billing_mode, estimated_cost_usd, actual_cost_usd, cost_status,
cost_source, pricing_version, title, title_source, last_activity_at,
last_activity_description, last_activity_provenance, api_call_count, handoff_state,
handoff_platform, handoff_error, compression_failure_cooldown_until,
compression_failure_error, compression_fallback_streak, compression_ineffective_count,
profile_name, rewind_count, archived, pinned, hidden, last_read_at`

Pemetaan: `id→session_id`, `started_at/last_activity_at→started_at/last_at` (epoch→ISO),
`title→title`, `display_name→snippet`, `profile_name→profile`.
**PROFILE AKTIF = `income-operator`** (gateway PID 17556). `messages` (untuk
session_get) berisi `role/content/timestamp`; FTS5 (`messages_fts`) ada tapi
pencarian FTS5 = P2.

### `cron\jobs.json`
Hanya manifest kosong (`jobs: []`) — BUKAN sumber kebenaran. Job sesungguhnya hanya
terlihat lewat `hermes cron list` → parser teks dipakai.

### `gateway_state.json`
Berisi `gateway_state`, `pid`, `start_time` — tapi stale (state `stopped`, pid lama).
Sumber kebenaran = `hermes gateway status` (live PID 17556).

## 3. Keputusan source/trust per reader

| Reader | Sumber utama | trust |
|---|---|---|
| kanban | CLI `--json` (bentuk di-record di sini) | VERIFIED |
| cron | CLI teks `cron list` (parser di-record) | VERIFIED |
| gateway | CLI teks `gateway status` + config.yaml | VERIFIED |
| sessions | DB profile `state.db` (CLI tak ber-json; Last Active relatif) + schema_guard | VERIFIED |
| capabilities | `state/CAPABILITIES.jsonl` (kosong saat ini) → default D3 Layer 7 | ASSUMED |
| EVENTS.jsonl | file internal bridge (schema 11-field di B2.4.2) | VERIFIED |

`schema_guard` fail-closed: schema beda → `DEGRADED` + `degraded_reason="schema drift"`.

## 4. Anomali / deviation yang tercatat
- **`kanban.db` tidak punya `mission_id`/`task_id`/`updated_at`/`kill_criteria`**
  sebagai kolom kartu. Field kanonik tsb diisi `None`/turunan (tidak menebak).
  Mission linkage ada di EVENTS.jsonl (`mission_id`), dipakai projection.
- Spec menulis `state.db:sessions` di `EXPECTED`; schema_guard memakai nama tabel
  aktual `tasks` & `sessions` (kunci: `kanban.db:tasks`, `state.db:sessions`).
- `hermes session list --json`/`cron list --json`/`gateway status --json` TIDAK
  didukung di v0.20.4 → parser teks / DB-first (keputusan tugas P1 briefing).
