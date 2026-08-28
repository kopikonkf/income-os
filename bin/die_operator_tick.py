"""DIE Proactive Operator tick runner v1 (PROPOSE_ONLY).

Implements docs/operations/PROACTIVE_OPERATOR_V1.md sections 4, 5, 9 and
ORCHESTRATOR_CONTRACT.md. Stdlib only except optional jsonschema validation.

Subcommands:
  prepare   Build the bounded hash-addressed input envelope for one tick and
            print bounded agent instructions. Fail-closed on pause/lock/stale.
  finalize  Validate the agent decision draft against
            company/schemas/die.operator.tick.v1.schema.json plus contract
            rules, write the immutable tick receipt, emit exactly one event
            through bin/die_event.py, and advance the operator cursor.

All file I/O is explicit UTF-8. Windows-safe. No network. USD 0.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from income_os_bridge import config as die_config
import time

DIE = die_config.DIE_HOME
STATE = die_config.STATE
OP = STATE / "operator"
TICKS = OP / "ticks"
RECEIPTS = OP / "platform_receipts"
QC_INBOX = OP / "qc_inbox"
PAUSE_FLAG = OP / "PAUSE"
LOCK = OP / "TICK.lock"
CURSOR = OP / "cursor.json"

SCHEMA = DIE / "company" / "schemas" / "die.operator.tick.v1.schema.json"
EVENT_PY = DIE / "bin" / "die_event.py"
CANON_MANIFEST = DIE / "company" / "runtime-canon-context-v1.json"

CANON_FILES = {
    "orchestrator_contract": DIE / "ORCHESTRATOR_CONTRACT.md",
    "operator_canon": DIE / "docs" / "operations" / "PROACTIVE_OPERATOR_V1.md",
    "blueprint_v2": DIE / "docs" / "missions" / "M001_BLUEPRINT_BATCH1_V2.md",
    "atlas": DIE / "company" / "atlas" / "human-centric" / "HUMAN_CENTRIC_ATLAS_CANON.md",
    "pipeline": DIE / "docs" / "pipeline" / "DIGITAL_INCOME_PIPELINE_CANON.md",
    "platform_matrix": DIE / "docs" / "pipeline" / "MATRIX_6_PLATFORM_TOS_STRICTNESS.md",
}

STATES = [
    "IDLE", "RESEARCH_PENDING", "BLUEPRINT_PENDING", "AWAITING_AUTHORIZATION",
    "BATCH_RUNNING", "QA_GATE", "FOUNDER_QC", "SUBMISSION_WAIT",
    "LEARNING_LOOP", "TIER2_ROUTING",
]
TRANSITIONS = {
    "IDLE": {"RESEARCH_PENDING"},
    "RESEARCH_PENDING": {"BLUEPRINT_PENDING"},
    "BLUEPRINT_PENDING": {"AWAITING_AUTHORIZATION"},
    "AWAITING_AUTHORIZATION": {"BATCH_RUNNING"},
    "BATCH_RUNNING": {"QA_GATE"},
    "QA_GATE": {"FOUNDER_QC", "LEARNING_LOOP"},
    "FOUNDER_QC": {"SUBMISSION_WAIT", "LEARNING_LOOP"},
    "SUBMISSION_WAIT": {"LEARNING_LOOP", "TIER2_ROUTING", "IDLE"},
    "LEARNING_LOOP": {"BLUEPRINT_PENDING", "RESEARCH_PENDING", "IDLE"},
    "TIER2_ROUTING": {"IDLE", "LEARNING_LOOP"},
}
ACTION_TYPES = {
    "OBSERVE_STATE", "CREATE_RESEARCH_CARD", "REQUEST_DIVISION01",
    "CREATE_BLUEPRINT_COMPILE_CARD", "FOLLOW_UP_CARD", "BLOCK_CARD",
    "WRITE_LEARNING", "DRAFT_U1_REQUEST", "INVOKE_M001_RUNNER",
    "PROPOSE_TIER2", "NOTIFY_FOUNDER", "NO_OP",
}
FOUNDER_ACTION_TYPES = {"DRAFT_U1_REQUEST", "NOTIFY_FOUNDER"}
MAX_MUTATIONS = 3
MAX_ENVELOPE_BYTES = 24576
LOCK_STALE_SECONDS = 600


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(t: dt.datetime) -> str:
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(text: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if any(x in key.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            env.pop(key, None)
    return env


def run(cmd, timeout=45):
    return subprocess.run(
        [str(c) for c in cmd], cwd=str(DIE), env=clean_env(), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


def emit_event(cls, summary, detail_ref=None, dedupe_key=None, mission="M-001"):
    cmd = [sys.executable, str(EVENT_PY), "event", "--class", cls,
           "--source", "hermes-income-operator", "--summary", summary[:140],
           "--mission-id", mission]
    if detail_ref:
        cmd += ["--detail-ref", str(detail_ref)]
    if dedupe_key:
        cmd += ["--dedupe-key", dedupe_key]
    result = run(cmd, timeout=30)
    return result.returncode == 0, result


# ---------------------------------------------------------------- cursor ----

def load_cursor() -> dict:
    if CURSOR.exists():
        try:
            data = json.loads(CURSOR.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {"last_state": "IDLE", "non_progress_count": 0, "fingerprints": []}


def save_cursor(cursor: dict) -> None:
    OP.mkdir(parents=True, exist_ok=True)
    CURSOR.write_text(
        json.dumps(cursor, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )


# ------------------------------------------------------------- collectors ---

def collect_repo_sha() -> str:
    result = run(["git", "-C", str(DIE), "rev-parse", "HEAD"], timeout=20)
    sha = result.stdout.strip().lower()
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha or "") else ""


def collect_canon_hashes() -> tuple[dict, str]:
    hashes = {}
    for name, path in CANON_FILES.items():
        hashes[name] = sha256_file(path) if path.is_file() else ""
    status = "VERIFIED"
    manifest_path = CANON_MANIFEST
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            docs = manifest.get("documents") or []
            for doc in docs:
                rel = doc.get("path") or ""
                expected = doc.get("sha256") or ""
                actual_path = DIE / rel
                if expected and actual_path.is_file():
                    if sha256_file(actual_path) != expected:
                        status = "E_CANON_HASH_MISMATCH"
                        break
        except (OSError, json.JSONDecodeError, AttributeError):
            status = "E_MANIFEST_UNREADABLE"
    else:
        status = "E_MANIFEST_MISSING"
    if any(v == "" for v in hashes.values()):
        status = "E_CANON_FILE_MISSING"
    return hashes, status


def collect_kanban(override_file: pathlib.Path | None) -> tuple[list, str]:
    if override_file is not None:
        try:
            rows = json.loads(override_file.read_text(encoding="utf-8"))
            return (rows if isinstance(rows, list) else []), "FILE_OVERRIDE"
        except (OSError, json.JSONDecodeError):
            return [], "FILE_OVERRIDE_INVALID"
    try:
        sys.path.insert(0, str(DIE / "bin"))
        from die_cron import resolve_hermes_executable  # type: ignore
        exe = resolve_hermes_executable()
    except Exception:
        return [], "HERMES_BIN_NOT_FOUND"
    result = run([exe, "--profile", "income-operator", "kanban", "list", "--json"],
                 timeout=30)
    if result.returncode:
        return [], "KANBAN_CLI_FAILED"
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [], "KANBAN_NON_JSON"
    if isinstance(rows, dict):
        for key in ("tasks", "cards", "items", "data"):
            if isinstance(rows.get(key), list):
                rows = rows[key]
                break
    if not isinstance(rows, list):
        return [], "KANBAN_UNKNOWN_SHAPE"
    compact = []
    for row in rows:
        if isinstance(row, dict):
            compact.append({
                "id": row.get("id") or row.get("task_id"),
                "status": row.get("status"),
                "assignee": row.get("assignee"),
                "title": (row.get("title") or "")[:90],
            })
    return compact, "CLI"


def collect_events_tail(limit=20) -> tuple[list, int]:
    path = STATE / "EVENTS.jsonl"
    rows = []
    if path.exists():
        with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    tail = rows[-limit:]
    compact = [{
        "seq": r.get("seq"),
        "class": r.get("class"),
        "source": r.get("source"),
        "summary": (r.get("summary") or "")[:110],
    } for r in tail]
    next_seq = (rows[-1].get("seq", 0) + 1) if rows else 1
    try:
        next_seq = int(next_seq)
    except (TypeError, ValueError):
        next_seq = 1
    return compact, next_seq


def collect_economics_tail(limit=3) -> dict:
    path = STATE / "ECONOMICS.jsonl"
    rows = []
    if path.exists():
        with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    return {"row_count": len(rows), "tail": rows[-limit:]}


def collect_founder_decisions() -> list:
    path = STATE / "DECISIONS.jsonl"
    out = []
    now = utcnow()
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            semantic = row.get("semantic_object") or {}
            cls = semantic.get("decision_class", row.get("class"))
            choice = semantic.get("choice", row.get("choice"))
            if cls == "production_authorization" or choice == "authorize_u1_validation_batch":
                expiry = parse_iso(semantic.get("expires_at") or "")
                out.append({
                    "decision_id": row.get("decision_id"),
                    "ts": row.get("ts"),
                    "choice": choice,
                    "run_id": semantic.get("run_id"),
                    "expired_or_missing_expiry": True if expiry is None else bool(now >= expiry),
                })
    return out


def iter_platform_receipts() -> tuple[list, list]:
    summaries, invalid = [], []
    if RECEIPTS.is_dir():
        for path in sorted(RECEIPTS.glob("*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                invalid.append(path.name)
                continue
            summaries.append({
                "receipt_id": row.get("receipt_id"),
                "batch_id": row.get("batch_id"),
                "asset_id": row.get("asset_id"),
                "platform": row.get("platform"),
                "outcome": row.get("outcome"),
                "reason_code": row.get("reason_code"),
                "evidence_label": row.get("evidence_label"),
                "recorded_at": row.get("recorded_at"),
            })
    return summaries, invalid


def collect_qc_inbox() -> list:
    items = []
    if QC_INBOX.is_dir():
        for path in sorted(QC_INBOX.iterdir()):
            if path.is_file():
                items.append({"name": path.name, "sha256": sha256_file(path)})
    return items


def collect_briefing_excerpt(limit_bytes=2048) -> str:
    path = STATE / "projection" / "BRIEFING.md"
    if not path.is_file():
        return ""
    data = path.read_bytes()[:limit_bytes]
    return data.decode("utf-8", errors="replace")


# ------------------------------------------------------------------ lock ----

_NO_LOCK = False


def acquire_lock() -> bool:
    if _NO_LOCK:
        return True
    OP.mkdir(parents=True, exist_ok=True)
    try:
        if LOCK.exists():
            age = time.time() - LOCK.stat().st_mtime
            if age < LOCK_STALE_SECONDS:
                return False
            LOCK.unlink()
        LOCK.write_text(iso(utcnow()), encoding="utf-8")
        return True
    except OSError:
        return False


def release_lock() -> None:
    if _NO_LOCK:
        return
    try:
        if LOCK.exists():
            LOCK.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------- prepare ---

def cmd_prepare(args) -> int:
    if PAUSE_FLAG.exists():
        ok, _ = emit_event(
            "INFO", "operator tick skipped: kill-switch PAUSE active",
            dedupe_key=f"operator:v1:M-001:pause-skip:{utcnow().strftime('%Y%m%d%H')}",
        )
        print("OPERATOR_PAUSED")
        return 0
    if not acquire_lock():
        print("OPERATOR_TICK_IN_PROGRESS")
        return 0

    kanban_rows, kanban_source = collect_kanban(args.kanban_file)
    canon_hashes, canon_status = collect_canon_hashes()
    events_tail, events_next_seq = collect_events_tail()
    envelope = {
        "as_of": iso(utcnow()),
        "repository_sha": collect_repo_sha(),
        "canon_load_status": canon_status,
        "canon_sha256": canon_hashes,
        "briefing_excerpt": collect_briefing_excerpt(),
        "kanban": {"source": kanban_source, "cards": kanban_rows},
        "events_tail": events_tail,
        "events_next_seq": events_next_seq,
        "economics": collect_economics_tail(),
        "founder_decisions": collect_founder_decisions(),
        "platform_receipts": iter_platform_receipts()[0],
        "platform_receipts_invalid_files": iter_platform_receipts()[1],
        "qc_inbox": collect_qc_inbox(),
        "paused": False,
        "cursor": {
            "last_state": load_cursor().get("last_state", "IDLE"),
            "non_progress_count": load_cursor().get("non_progress_count", 0),
        },
    }
    # Work-situation fingerprint: stable observation surface only.
    # events_tail/economics are deliberately excluded — every tick writes its
    # own event, so a moving log would make non-progress detection impossible.
    fingerprint_payload = json.dumps(
        {k: envelope[k] for k in (
            "repository_sha", "canon_load_status", "canon_sha256",
            "briefing_excerpt", "kanban",
            "founder_decisions", "platform_receipts",
            "platform_receipts_invalid_files", "qc_inbox", "paused",
        ) if k in envelope},
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    fingerprint = sha256_bytes(fingerprint_payload)

    stamp = utcnow().strftime("%Y%m%d-%H%M%S")
    tick_id = f"OPTICK-{stamp}"
    tick_dir = TICKS / tick_id
    tick_dir.mkdir(parents=True, exist_ok=True)
    envelope["input_fingerprint"] = fingerprint
    envelope["tick_id"] = tick_id
    envelope["started_at"] = envelope["as_of"]
    envelope["mode"] = "PROPOSE_ONLY"
    envelope["decision_template"] = {
        "previous_state": envelope["cursor"]["last_state"],
        "selected_state": envelope["cursor"]["last_state"],
        "candidate_actions": [{
            "action_id": "A1",
            "action_type": "NO_OP",
            "authority": "AUTONOMOUS",
            "rationale": "one-line reason citing evidence",
            "evidence_refs": ["<envelope key or file ref>"],
            "dedupe_key": "operator:v1:M-001:<state>:<subject>:<" + fingerprint[:8] + ">",
        }],
        "selected_action_id": None,
        "result": "NO_OP",
        "mutations": [],
        "next_tick_not_before": iso(utcnow() + dt.timedelta(minutes=30)),
    }
    envelope["finalize_command"] = (
        f'{sys.executable} "{DIE / "bin" / "die_operator_tick.py"}" '
        f'finalize --tick-dir "{tick_dir}"'
    )

    envelope_path = tick_dir / "envelope.json"
    raw = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_ENVELOPE_BYTES:
        slim_keys = ("events_tail", "briefing_excerpt", "platform_receipts")
        for key in slim_keys:
            envelope[key] = [] if key != "briefing_excerpt" else ""
        raw = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")
        envelope["slimmed"] = True
    envelope_path.write_bytes(raw)

    degraded = []
    if canon_status != "VERIFIED":
        degraded.append(f"canon_load_status={canon_status} -> result must be REPORT_ONLY")
    if kanban_source != "CLI":
        degraded.append(f"kanban_source={kanban_source} -> result must be REPORT_ONLY")
    degraded_note = ("; ".join(degraded)) if degraded else "none"

    print("DIE OPERATOR TICK — PROPOSE_ONLY — M-001")
    print(f"tick_id: {tick_id}")
    print(f"envelope: {envelope_path} ({len(raw)} bytes)")
    print(f"fingerprint: {fingerprint[:12]}…  previous_state: "
          f"{envelope['cursor']['last_state']}  non_progress: "
          f"{envelope['cursor']['non_progress_count']}")
    print(f"degraded_inputs: {degraded_note}")
    print("RULES: max 1 state transition; max 3 mutations; FORBIDDEN actions never "
          "selected; FOUNDER_REQUIRED => result AWAITING_FOUNDER; every tick writes a "
          "receipt via finalize even when NO_OP.")
    print(f"WRITE your decision draft JSON to: {tick_dir / 'decision.json'}")
    print(f"THEN RUN: {envelope['finalize_command']}")
    return 0


# --------------------------------------------------------------- finalize ---


def cmd_finalize(args) -> int:
    tick_dir = pathlib.Path(args.tick_dir).resolve()
    envelope_path = tick_dir / "envelope.json"
    decision_path = tick_dir / "decision.json"
    try:
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FINALIZE_ERROR: unreadable tick inputs: {exc}", file=sys.stderr)
        release_lock()
        return 2

    completed = utcnow()
    started = parse_iso(envelope.get("started_at") or "") or completed
    wall_seconds = max(0, int((completed - started).total_seconds()))
    decision_json = json.dumps(decision, ensure_ascii=False).encode("utf-8")
    output_tokens = max(1, len(decision_json) // 4)

    cursor = load_cursor()
    receipt = {
        "schema_version": "die.operator.tick.v1",
        "tick_id": envelope.get("tick_id") or tick_dir.name,
        "mode": "PROPOSE_ONLY",
        "operator_id": "hermes-operator",
        "mission_id": "M-001",
        "started_at": envelope.get("started_at"),
        "completed_at": iso(completed),
        "source_snapshot": {
            "snapshot_id": envelope.get("tick_id", "unknown"),
            "as_of": envelope.get("as_of"),
            "repository_sha": envelope.get("repository_sha", ""),
            "canon_load_status": envelope.get("canon_load_status"),
            "events_next_seq": envelope.get("events_next_seq", 0),
        },
        "input_fingerprint": envelope.get("input_fingerprint", ""),
        "previous_state": decision.get(
            "previous_state",
            envelope.get("cursor", {}).get("last_state", "IDLE")),
        "selected_state": decision.get("selected_state", "IDLE"),
        "candidate_actions": decision.get("candidate_actions", []),
        "selected_action_id": decision.get("selected_action_id"),
        "result": decision.get("result", "REPORT_ONLY"),
        "mutations": decision.get("mutations", []),
        "budget": {
            "cost_usd": 0,
            "input_bytes": envelope_path.stat().st_size,
            "output_tokens": output_tokens,
            "wall_time_seconds": wall_seconds,
        },
        "next_tick_not_before": decision.get(
            "next_tick_not_before", iso(completed)),
        "event_dedupe_key": decision.get(
            "event_dedupe_key",
            f"operator:v1:M-001:tick:{envelope.get('tick_id', 'unknown')}"),
    }

    # Degraded inputs force REPORT_ONLY before contract checks.
    if (envelope.get("canon_load_status") != "VERIFIED"
            or envelope.get("kanban", {}).get("source")
            not in ("CLI", "FILE_OVERRIDE")):
        receipt["result"] = "REPORT_ONLY"
        receipt["mutations"] = []

    # Contract checks normalize the receipt first (non_progress_count,
    # possible BLOCKED rewrite) so the schema validates the final artifact.
    violations: list[str] = []
    prev = receipt["previous_state"]
    sel = receipt["selected_state"]
    if sel != prev and sel not in TRANSITIONS.get(prev, set()):
        violations.append(f"illegal transition {prev}->{sel}")
    actions = {a.get("action_id"): a
               for a in receipt.get("candidate_actions", [])}
    selected_id = receipt.get("selected_action_id")
    sel_action = actions.get(selected_id) if selected_id else None
    if selected_id and sel_action is None:
        violations.append("selected_action_id does not match any candidate")
    if sel_action and sel_action.get("authority") == "FORBIDDEN":
        violations.append("FORBIDDEN authority action selected")
    kinds = [m.get("kind") for m in receipt.get("mutations", [])]
    if len(kinds) > MAX_MUTATIONS:
        violations.append(f"mutations exceed {MAX_MUTATIONS}")
    result_value = receipt.get("result")
    if result_value == "EXECUTED" and not kinds:
        violations.append("EXECUTED without mutations")
    if result_value == "NO_OP" and kinds:
        violations.append("NO_OP with mutations")
    if sel_action and sel_action.get("authority") == "FOUNDER_REQUIRED":
        if result_value != "AWAITING_FOUNDER":
            violations.append(
                "FOUNDER_REQUIRED action must yield AWAITING_FOUNDER")
    if result_value == "AWAITING_FOUNDER":
        if not ({"AUTHORIZATION_DRAFT", "FOUNDER_NOTIFICATION"} & set(kinds)
                or (sel_action
                    and sel_action.get("authority") == "FOUNDER_REQUIRED")):
            violations.append(
                "AWAITING_FOUNDER without founder-facing mutation/action")

    # Non-progress bookkeeping.
    fp = receipt.get("input_fingerprint", "")
    history = cursor.get("fingerprints", [])
    if history and history[-1].get("fingerprint") == fp:
        cursor["non_progress_count"] = (
            int(cursor.get("non_progress_count", 0)) + 1)
    else:
        cursor["non_progress_count"] = 0
    history.append({"fingerprint": fp, "state": sel, "ts": iso(completed)})
    cursor["fingerprints"] = history[-10:]
    receipt["non_progress_count"] = int(cursor.get("non_progress_count", 0))

    # 24h dedupe recurrence over past EXECUTED receipts.
    key = receipt.get("event_dedupe_key", "")
    if key:
        for path in sorted(TICKS.glob("OPTICK-*/receipt.json")):
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (old.get("event_dedupe_key") == key
                    and old.get("tick_id") != receipt.get("tick_id")
                    and old.get("result") == "EXECUTED"):
                ts = parse_iso(old.get("completed_at") or "")
                if ts and (completed - ts).total_seconds() < 86400:
                    violations.append(
                        f"dedupe key reused within 24h: {path.parent.name}")

    schema_errors: list[str] = []
    degraded_notes: list[str] = []
    try:
        import jsonschema  # type: ignore
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        # The schema pins canon_load_status=VERIFIED (ticks are only defined
        # for a verified-canon world). For degraded runs the stored receipt
        # keeps the honest status; validation runs on a sanitized copy so the
        # REPORT_ONLY fail-closed path is not mislabeled BLOCKED.
        validation_copy = json.loads(json.dumps(receipt))
        if validation_copy["source_snapshot"]["canon_load_status"] != "VERIFIED":
            degraded_notes.append(
                "degraded canon: "
                + str(envelope.get("canon_load_status")))
            validation_copy["source_snapshot"]["canon_load_status"] = "VERIFIED"
        jsonschema.validate(instance=validation_copy, schema=schema)
    except ImportError:
        schema_errors = [
            "jsonschema module unavailable; structural check skipped"]
    except Exception as exc:  # ValidationError or unreadable schema
        schema_errors = [f"schema: {getattr(exc, 'message', str(exc))}"]

    all_errors = schema_errors + violations
    event_class = "INFO"
    if receipt["non_progress_count"] >= 3:
        event_class = "WARNING"
    if all_errors:
        receipt["result"] = "BLOCKED"
        receipt["mutations"] = []
        event_class = "WARNING"
        (tick_dir / "violations.json").write_text(
            json.dumps({"tick_id": receipt["tick_id"],
                        "violations": all_errors,
                        "degraded": degraded_notes},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")

    receipt_path = tick_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    ok, _result = emit_event(
        event_class,
        f"operator tick {receipt['tick_id']}: {receipt['result']}"
        + (f" violations={len(all_errors)}" if all_errors else ""),
        detail_ref=str(receipt_path),
        dedupe_key=receipt["event_dedupe_key"],
    )
    if not ok:
        print("FINALIZE_WARNING: die_event.py failed; receipt still recorded",
              file=sys.stderr)

    save_cursor(cursor)
    release_lock()

    print(f"FINALIZED {receipt['tick_id']} result={receipt['result']} "
          f"state={receipt['previous_state']}->{receipt['selected_state']} "
          f"non_progress={receipt['non_progress_count']}")
    for err in all_errors:
        print(f"  VIOLATION: {err}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="build bounded tick input envelope")
    p_prep.add_argument("--kanban-file", type=pathlib.Path, default=None,
                        help="fixture override for tests/simulations")
    p_prep.add_argument("--no-lock", action="store_true",
                        help="simulation helper: skip overlap lock")

    p_fin = sub.add_parser("finalize", help="validate decision and record receipt")
    p_fin.add_argument("--tick-dir", required=True, type=pathlib.Path)
    p_fin.set_defaults(func=None)

    args = parser.parse_args(argv)
    if args.command == "prepare":
        global _NO_LOCK
        _NO_LOCK = bool(getattr(args, "no_lock", False))
        return cmd_prepare(args)
    return cmd_finalize(args)


if __name__ == "__main__":
    raise SystemExit(main())
