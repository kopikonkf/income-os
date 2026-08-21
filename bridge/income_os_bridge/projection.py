import json, datetime
from . import authority, config, envelope, events, redact, snapshot
from . import hermes_state_reader as reader
_ORDER = {"DEGRADED": 0, "ASSUMED": 1, "VERIFIED": 2}
_LABEL = ["DEGRADED", "ASSUMED", "VERIFIED"]
_EV = config.EVENTS_VERIFIED and "VERIFIED" or "ASSUMED"
def _worst(*trusts):
    return _LABEL[min(_ORDER.get(t, 0) for t in trusts if t)]
def _redact(obj):
    if isinstance(obj, str):
        return redact.redact(obj)
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items()}
    return obj
def _ev():
    return events.read_events()
def _jlines(p, n=None):
    out = []
    try:
        if p.exists():
            for ln in p.read_text(encoding="utf-8-sig").splitlines():
                if not ln.strip():
                    continue
                try:
                    out.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeError):
        pass
    return out[:n] if n else out
def _stale(ev):
    ack = [e for e in ev if e.get("source") == "lane" or "ack" in str(e.get("summary", "")).lower()]
    if not ack:
        return None
    try:
        t = datetime.datetime.fromisoformat(str(ack[-1].get("ts")).replace("Z", "+00:00"))
        return max(0, int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60))
    except Exception:
        return None
def system_health():
    gw, cr, ev = reader.get_gateway_status(), reader.get_cron_jobs(), _ev()
    g = gw.rows[0] if gw.rows else {}
    cron = [{"name": c.get("name"), "last_run_at": c.get("last_run_at"), "last_status": c.get("last_status"), "overdue_min": None} for c in cr.rows]
    alarms = [{"class": e.get("class"), "event_id": e.get("event_id"), "summary": e.get("summary")} for e in ev if e.get("class") in ("WARNING", "CRITICAL")]
    data = {"gateway_running": g.get("running"), "uptime_s": g.get("uptime_s"), "cron": cron,
            "active_alarms": alarms, "cognitive_lane_stale_min": _stale(ev),
            "bridge_seq_last": ev[-1]["seq"] if ev else 0,
            "event_backlog": sum(1 for e in ev if e.get("seq", 0) > events.read_cursor())}
    trust = _worst(gw.trust, cr.trust, _EV)
    return envelope.build("system_health", _redact(data), ["cli:hermes gateway status", "cli:hermes cron list", "file:state/EVENTS.jsonl"],
                          completeness="degraded" if trust == "DEGRADED" else "complete", source_trust=trust)
def system_state():
    limits = {"spend_daily_usd": config.A0_DAILY_USD, "spend_mission_usd": config.A0_MISSION_USD, "wake_per_day": config.WAKE_PER_DAY}
    data = {"autonomy_level": "A0", "status": "ASSUMPTION", "degradation_mode": "none", "status_degradation": "ASSUMPTION",
            "active_limits": {k: {"value": v, "status": "ASSUMPTION"} for k, v in limits.items()},
            "phase": "alpha", "status_phase": "ASSUMPTION"}
    return envelope.build("system_state", _redact(data), ["config:DIE"], source_trust="ASSUMED")
def active_missions(status="active"):
    kb, ev = reader.get_kanban_rows(), _ev()
    m = {}
    for e in ev:
        mid = e.get("mission_id")
        if mid:
            d = m.setdefault(mid, {"mission_id": mid, "goal": mid, "status": "active", "kill_criteria": None,
                                   "invalid": True, "budget": None, "deadline": None, "cards_open": 0, "last_event_seq": 0})
            d["last_event_seq"] = max(d["last_event_seq"], e.get("seq", 0))
    if status != "any":
        m = {k: v for k, v in m.items() if v["status"] == status}
    for d in m.values():
        d["cards_open"] = sum(1 for c in kb.rows if c.get("status") == "open")
    trust = _worst(kb.trust, _EV)
    return envelope.build("active_missions", _redact(list(m.values())), ["db:kanban tasks", "file:state/EVENTS.jsonl"],
                          completeness="degraded" if trust == "DEGRADED" else "complete", source_trust=trust)
def mission_get(mission_id):
    kb = reader.get_kanban_rows()
    mission = next(({"mission_id": e.get("mission_id"), "goal": e.get("mission_id"), "status": "active",
                     "kill_criteria": None, "last_event_seq": e.get("seq")} for e in _ev() if e.get("mission_id") == mission_id), None)
    if mission is None:
        return None  # -> E_NOT_FOUND
    data = {"mission": mission, "cards": [{"card_id": c.get("card_id"), "title": c.get("title"), "status": c.get("status"),
                                             "assignee": c.get("assignee"), "heartbeat_at": c.get("heartbeat_at")} for c in kb.rows],
            "evidence_refs": [d.get("evidence_ref") for d in _jlines(config.STATE / "DECISIONS.jsonl") if d.get("evidence_ref")][:20],
            "cost_lines": _jlines(config.STATE / "ECONOMICS.jsonl"), "decisions": _jlines(config.STATE / "DECISIONS.jsonl", 20)}
    return envelope.build("mission_get", _redact(data), ["db:kanban tasks", "file:DECISIONS.jsonl", "file:ECONOMICS.jsonl"],
                          completeness="degraded" if kb.trust == "DEGRADED" else "complete", source_trust=kb.trust,
                          notes=["evidence_refs = path relatif, bukan isi file"])
def workers():
    kb = reader.get_kanban_rows()
    byw = {}
    for c in kb.rows:
        w = c.get("assignee") or "unassigned"
        d = byw.setdefault(w, {"worker": w, "status": "idle", "jobs_total": 0, "jobs_done": 0, "jobs_blocked": 0, "median_min": None, "last_seen_at": c.get("heartbeat_at")})
        d["jobs_total"] += 1
        st = c.get("status")
        if st == "done":
            d["jobs_done"] += 1
        elif st == "blocked":
            d["jobs_blocked"] += 1
        if c.get("heartbeat_at"):
            d["last_seen_at"] = c.get("heartbeat_at")
    return envelope.build("workers", _redact(list(byw.values())), ["db:kanban tasks"],
                          completeness="degraded" if kb.trust == "DEGRADED" else "complete", source_trust=kb.trust)
def scheduled_jobs():
    cr = reader.get_cron_jobs()
    data = [{"name": c.get("name"), "schedule": c.get("schedule"), "enabled": c.get("enabled"), "next_run_at": c.get("next_run_at"),
             "last_run_at": c.get("last_run_at"), "last_status": c.get("last_status")} for c in cr.rows]
    return envelope.build("scheduled_jobs", _redact(data), ["cli:hermes cron list"],
                          completeness="degraded" if cr.trust == "DEGRADED" else "complete", source_trust=cr.trust,
                          notes=["prompt cron tidak diekspos (detail internal)"])
def capabilities(status="any"):
    cap = reader.get_capabilities()
    rows = [c for c in cap.rows if status == "any" or c.get("status") == status]
    return envelope.build("capabilities", _redact(rows), ["file:state/CAPABILITIES.jsonl"],
                          completeness="degraded" if cap.trust == "DEGRADED" else "complete", source_trust=cap.trust)
def recent_events(since_seq=0, limit=config.PAGE_DEFAULT, min_class="INFO"):
    data = events.recent_events(since_seq, limit, min_class)
    return envelope.build("recent_events", _redact(data), ["file:state/EVENTS.jsonl"],
                          completeness="truncated" if data["truncated"] else "complete", source_trust=_EV)
def search_sessions(query, limit=10):
    q = query.lower()
    sess = reader.get_sessions(limit=50)
    rows = [s for s in sess.rows if q in (s.get("title") or "").lower() or q in (s.get("snippet") or "").lower()][:limit]
    data = {"rows": [{"session_id": h.get("session_id"), "started_at": h.get("started_at"), "title": h.get("title"),
                      "snippet": (h.get("snippet") or "")[:config.SNIPPET_MAX]} for h in rows], "query": query, "hit_count": len(rows)}
    return envelope.build("search_sessions", _redact(data), ["db:state sessions"], source_trust=sess.trust,
                          notes=["P1: pencarian substring; FTS5 = P2"])
def session_get(session_id, max_turns=config.MAX_TURNS):
    det = reader.get_session_detail(session_id, max_turns)
    if det.get("session") is None:
        return None  # -> E_NOT_FOUND
    data = {"session_id": session_id, "started_at": det["session"].get("started_at"),
            "turns": [{"role": t.get("role"), "at": t.get("at"), "text": t.get("text")} for t in det["turns"]]}
    trust = det.get("trust", "ASSUMED")
    return envelope.build("session_get", _redact(data), ["db:state messages"],
                          completeness="truncated" if trust == "DEGRADED" else "complete", source_trust=trust,
                          notes=[f"maks {max_turns} turn; isi file/kredensial tidak dialirkan"])
def briefing_get(latest=True):
    p = config.BRIEFING
    return {"as_of": envelope.now_iso(),
            "operational_control_plane": config.OPERATIONAL_CONTROL_PLANE,
            "canonical_writer": config.CANONICAL_WRITER,
            "markdown": redact.redact(p.read_text(encoding="utf-8")) if latest and p.exists() else ""}


def _decision_evidence_refs(limit=20):
    rows = []
    decisions = _jlines(config.STATE / "DECISIONS.jsonl")
    for decision in decisions[-limit:]:
        ref = decision.get("evidence_ref")
        decision_id = decision.get("decision_id")
        observed_at = decision.get("ts")
        if not ref or not decision_id or not observed_at:
            continue
        rows.append({
            "evidence_id": f"EVREF-{decision_id}",
            "kind": "decision_support",
            "ref": redact.redact_reference(str(ref)),
            "claim": f"Supporting reference declared by {decision_id}",
            "trust": "ASSUMED",
            "observed_at": str(observed_at),
        })
    return rows


def context_snapshot(principal_id, scope=None, since_seq=0, limit=config.CONTEXT_EVENT_LIMIT):
    granted = authority.authorize(
        principal_id,
        "context.snapshot.read",
        scope,
    )
    bounded_limit = min(max(limit, 1), 50)
    surfaces = {
        "system_state": system_state(),
        "system_health": system_health(),
        "active_missions": active_missions("any"),
        "recent_events": recent_events(since_seq, bounded_limit, "INFO"),
    }
    return snapshot.build(
        granted,
        surfaces,
        _decision_evidence_refs(),
    )
