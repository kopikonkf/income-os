import datetime, json, pathlib, re, sqlite3, subprocess
from dataclasses import dataclass
from typing import Any, Literal
from . import config, schema_guard
Source = Literal["cli", "db", "file", "none"]
Trust = Literal["VERIFIED", "ASSUMED", "DEGRADED"]
VERIFIED = "VERIFIED"; ASSUMED = "ASSUMED"; DEGRADED = "DEGRADED"
@dataclass
class ReaderResult:
    rows: list[dict[str, Any]]
    source: Source
    trust: Trust
    as_of: str
    complete: bool
    degraded_reason: str | None = None
    truncated_at: int | None = None
def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
def _iso(epoch):
    if epoch in (None, "", 0):
        return None
    try:
        return datetime.datetime.fromtimestamp(float(epoch), datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        return None
def _run(which, extra=None):
    argv = list(config.CLI_CMDS[which])
    if which == "sessions" and extra:
        argv += ["--limit", str(extra)]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=config.CLI_TIMEOUT, shell=False)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, f"ERR {e}"
def _db(which, sql, params=(), table_key=None):
    path = config.KANBAN_DB if which == "kanban" else config.STATE_DB_PROFILE
    if which == "sessions" and not pathlib.Path(path).exists():
        path = config.STATE_DB_DEFAULT
    try:
        con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        tab = table_key.split(":")[-1] if table_key else None
        cols = [r["name"] for r in con.execute(f"PRAGMA table_info({tab})")] if tab else []
        ok = schema_guard.check(table_key, cols) if tab else None
        rows = [dict(r) for r in con.execute(sql, params)]
        con.close()
        return rows, schema_guard.classify(ok), (None if ok is not False else "schema drift")
    except Exception as e:
        return [], DEGRADED, f"db error: {e}"
def get_kanban_rows(limit=200):
    rc, out = _run("kanban")
    if rc == 0:
        try:
            raw = json.loads(out)
            if isinstance(raw, list):
                return ReaderResult([_kanban_row(c) for c in raw[:limit]], "cli", VERIFIED, _now(), True)
        except Exception:
            pass
    rows, trust, reason = _db("kanban", "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,), "kanban.db:tasks")
    return ReaderResult([_kanban_row(r, db=True) for r in rows], "db", trust, _now(), trust != DEGRADED,
                        degraded_reason=reason, truncated_at=(len(rows) if trust == DEGRADED else None))
def _kanban_row(r, db=False):
    if db:
        return {"card_id": r.get("id"), "title": r.get("title"), "status": r.get("status"),
                "mission_id": None, "task_id": r.get("id"), "heartbeat_at": _iso(r.get("last_heartbeat_at")),
                "created_at": _iso(r.get("created_at")), "updated_at": _iso(r.get("completed_at") or r.get("started_at")),
                "assignee": r.get("assignee"), "kill_criteria": None}
    return {"card_id": r.get("card_id") or r.get("id"), "title": r.get("title"), "status": r.get("status"),
            "mission_id": r.get("mission_id"), "task_id": r.get("task_id") or r.get("id"),
            "heartbeat_at": r.get("heartbeat_at"), "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"), "assignee": r.get("assignee"), "kill_criteria": r.get("kill_criteria")}
def _sess_rows(limit=20, where="", params=()):
    sql = "SELECT * FROM sessions" + (" WHERE " + where if where else "") + " ORDER BY started_at DESC LIMIT ?"
    return _db("sessions", sql, tuple(params) + (limit,), "state.db:sessions")
def _sess_row(r, snippet=None):
    return {"session_id": r.get("id"), "started_at": _iso(r.get("started_at")), "last_at": _iso(r.get("last_activity_at")),
            "title": r.get("title"), "snippet": snippet or r.get("display_name"), "profile": r.get("profile_name")}
def get_sessions(query=None, limit=20):
    try:
        rows, trust, reason = _sess_rows(limit)
    except Exception as e:
        return ReaderResult([], "db", DEGRADED, _now(), False, degraded_reason=str(e))
    return ReaderResult([_sess_row(r) for r in rows], "db", trust, _now(), trust != DEGRADED,
                        degraded_reason=reason, truncated_at=(len(rows) if trust == DEGRADED else None))
def get_session_detail(session_id, max_turns=config.MAX_TURNS):
    try:
        rows, trust, reason = _sess_rows(1, "id = ?", (session_id,))
        if not rows:
            return {"session": None, "turns": [], "trust": trust, "reason": "not found"}
        msgs = _db("sessions",
                   "SELECT role, content, timestamp FROM messages WHERE session_id = ? AND active = 1 ORDER BY timestamp LIMIT ?",
                   (session_id, max_turns), "state.db:messages")[0]
        turns = [{"role": m.get("role"), "at": _iso(m.get("timestamp")), "text": m.get("content")} for m in msgs]
        return {"session": _sess_row(rows[0]), "turns": turns, "trust": trust, "reason": reason}
    except Exception as e:
        return {"session": None, "turns": [], "trust": DEGRADED, "reason": str(e)}
def get_cron_jobs():
    rc, out = _run("cron")
    if rc != 0:
        return ReaderResult([], "none", DEGRADED, _now(), False, degraded_reason="cron CLI gagal")
    return ReaderResult(_parse_cron(out), "cli", VERIFIED, _now(), True)
def _parse_cron(text):
    jobs, cur = [], None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^([0-9a-f]{12})\s+\[(\w+)\]$", s)
        if m:
            if cur:
                jobs.append(cur)
            cur = {"_enabled": m.group(2)}
            continue
        if cur and ":" in s:
            k, v = s.split(":", 1)
            cur[k.strip().lower().replace(" ", "_")] = v.strip()
    if cur:
        jobs.append(cur)
    out = []
    for j in jobs:
        last = j.get("last_run", "")
        status = "ok" if "ok" in last.lower() else ("failed" if last else None)
        out.append({"name": j.get("name"), "schedule": j.get("schedule"),
                    "enabled": j.get("_enabled") == "active",
                    "last_run_at": (last.split("  ")[0].strip() if last else None),
                    "last_status": status, "next_run_at": j.get("next_run"),
                    "profile": "income-operator"})
    return out
def get_gateway_status():
    rc, out = _run("gateway")
    if rc != 0:
        return ReaderResult([], "none", DEGRADED, _now(), False, degraded_reason="gateway CLI gagal")
    running = "Gateway process running" in out
    m = re.search(r"PID:\s*(\d+)", out)
    pid = int(m.group(1)) if m else None
    provider, model = _config_model()
    return ReaderResult([{"running": running, "pid": pid, "uptime_s": None,
                          "main_provider": provider, "main_model": model,
                          "aux_provider": None, "last_error": None}], "cli", VERIFIED, _now(), True)
def _config_model():
    provider = model = None
    try:
        sec = None
        for ln in config.CONFIG_YAML.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ln and not ln[0].isspace() and ":" in ln:
                sec = ln.split(":", 1)[0].strip()
                continue
            if sec == "model" and ":" in ln:
                k, v = ln.split(":", 1)
                k = k.strip()
                if k == "provider":
                    provider = v.strip()
                elif k == "default":
                    model = v.strip()
    except Exception:
        pass
    return provider, model
def get_capabilities():
    rows = []
    try:
        if config.CAPABILITIES_FILE.exists():
            for ln in config.CAPABILITIES_FILE.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    rows.append(json.loads(ln))
            if rows:
                return ReaderResult([{"name": r.get("name"), "status": r.get("status", ASSUMED),
                                      "evidence_ref": r.get("evidence_ref"), "checked_at": r.get("checked_at")} for r in rows],
                                    "file", VERIFIED, _now(), True)
    except Exception:
        pass
    now = _now()
    return ReaderResult([{"name": n, "status": ASSUMED, "evidence_ref": "config:D3-layer7-default", "checked_at": now}
                         for n in config.DEFAULT_CAPABILITIES], "file", ASSUMED, _now(), True)
