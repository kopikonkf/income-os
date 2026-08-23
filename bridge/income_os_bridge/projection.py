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


def _active_alarms(ev):
    """Compile open alarms without erasing legacy fail-closed records.

    New writers can close an alarm by referencing its event id or by emitting a
    resolved record with the same dedupe key.  Legacy WARNING/CRITICAL rows have
    no lifecycle metadata, so they remain open until an explicit resolution
    references them.
    """

    open_by_id = {}
    open_by_key = {}
    for event in ev:
        state = event.get("alarm_state")
        event_id = event.get("event_id")
        dedupe_key = event.get("dedupe_key")
        resolves_event_id = event.get("resolves_event_id")
        if state == "resolved":
            if resolves_event_id:
                open_by_id.pop(resolves_event_id, None)
            if dedupe_key:
                previous = open_by_key.pop(dedupe_key, None)
                if previous:
                    open_by_id.pop(previous, None)
            continue
        if event.get("class") not in ("WARNING", "CRITICAL"):
            continue
        if event_id:
            open_by_id[event_id] = event
        if dedupe_key and event_id:
            previous = open_by_key.get(dedupe_key)
            if previous:
                open_by_id.pop(previous, None)
            open_by_key[dedupe_key] = event_id
    return list(open_by_id.values())


def _linked_cards(kb_rows, ev, mission_id):
    """Return cards linked explicitly by CLI metadata or a canonical event."""

    task_ids = {
        str(event.get("task_id"))
        for event in ev
        if event.get("mission_id") == mission_id and event.get("task_id")
    }
    return [
        card for card in kb_rows
        if card.get("mission_id") == mission_id
        or str(card.get("task_id") or card.get("card_id")) in task_ids
    ]


def _mission_rows(kb_rows, ev, decisions):
    """Compile mission lifecycle from canonical decisions plus Kanban materialization."""

    missions = {}

    def ensure(mid):
        return missions.setdefault(mid, {
            "mission_id": mid,
            "division_id": None,
            "goal": mid,
            "status": "active",
            "lifecycle_state": "event_observed",
            "kill_criteria": None,
            "invalid": True,
            "reconcile_required": False,
            "execution_ready": False,
            "budget": None,
            "deadline": None,
            "cards_open": 0,
            "last_event_seq": 0,
            "last_decision_id": None,
        })

    for event in ev:
        mid = event.get("mission_id")
        if not mid:
            continue
        row = ensure(mid)
        if row.get("division_id") is None and event.get("division_id") is not None:
            row["division_id"] = event.get("division_id")
        row["last_event_seq"] = max(row["last_event_seq"], event.get("seq", 0))

    lifecycle_rank = {
        "mission_ratification": 1,
        "propose_mission": 2,
        "mission_acceptance": 3,
    }
    lifecycle = {}
    for decision in decisions:
        semantic = decision.get("semantic_object")
        if not isinstance(semantic, dict):
            continue
        mid = semantic.get("mission_id")
        klass = decision.get("class") or semantic.get("decision_class")
        if not mid or klass not in lifecycle_rank:
            continue
        choice = str(decision.get("choice") or semantic.get("choice") or "").upper()
        if klass == "mission_ratification" and not choice.startswith("RATIFY"):
            continue
        if klass == "mission_acceptance" and not choice.startswith("ACCEPT"):
            continue
        row = ensure(mid)
        if semantic.get("division_id") is not None:
            row["division_id"] = semantic.get("division_id")
        if semantic.get("goal"):
            row["goal"] = semantic.get("goal")
        if semantic.get("kill_criteria") is not None:
            row["kill_criteria"] = semantic.get("kill_criteria")
        if semantic.get("budget") is not None:
            row["budget"] = semantic.get("budget")
        if semantic.get("deadline") is not None:
            row["deadline"] = semantic.get("deadline")
        if lifecycle_rank[klass] >= lifecycle.get(mid, 0):
            lifecycle[mid] = lifecycle_rank[klass]
            row["last_decision_id"] = decision.get("decision_id")

    closed = {"done", "closed", "completed", "cancelled"}
    for mid, row in missions.items():
        cards = _linked_cards(kb_rows, ev, mid)
        card_statuses = {str(card.get("status") or "").lower() for card in cards}
        row["cards_open"] = sum(
            1 for card in cards
            if str(card.get("status") or "").lower() not in closed
        )
        rank = lifecycle.get(mid, 0)
        if rank == 1:
            row["status"] = "ratified"
            row["lifecycle_state"] = "ratified"
        elif rank == 2:
            row["status"] = "pending_acceptance"
            row["lifecycle_state"] = "proposed"
        elif rank == 3 and not cards:
            row["status"] = "active"
            row["lifecycle_state"] = "accepted"
            row["invalid"] = False
            row["reconcile_required"] = True
        elif rank == 3:
            row["lifecycle_state"] = "materialized"
            row["invalid"] = False
            if card_statuses and card_statuses <= closed:
                row["status"] = "completed"
            elif "active" in card_statuses or "running" in card_statuses or "in_progress" in card_statuses or "open" in card_statuses:
                row["status"] = "active"
                row["execution_ready"] = True
            elif "blocked" in card_statuses:
                row["status"] = "blocked"
            elif "paused" in card_statuses:
                row["status"] = "paused"
            else:
                row["status"] = "blocked"
                row["reconcile_required"] = True
    return list(missions.values())


def _mission_decisions(decisions, mission_id):
    return [
        decision for decision in decisions
        if isinstance(decision.get("semantic_object"), dict)
        and decision["semantic_object"].get("mission_id") == mission_id
    ]


def system_health():
    gw, cr, ev = reader.get_gateway_status(), reader.get_cron_jobs(), _ev()
    g = gw.rows[0] if gw.rows else {}
    cron = [{"name": c.get("name"), "last_run_at": c.get("last_run_at"), "last_status": c.get("last_status"), "overdue_min": None} for c in cr.rows]
    open_alarms = _active_alarms(ev)
    alarms = [{"class": e.get("class"), "event_id": e.get("event_id"), "summary": e.get("summary"),
               "dedupe_key": e.get("dedupe_key")} for e in open_alarms]
    trust = _worst(gw.trust, cr.trust, _EV)
    blockers = []
    if g.get("running") is not True:
        blockers.append("gateway_not_running")
    if trust == "DEGRADED":
        blockers.append("health_source_degraded")
    blockers.extend(
        f"critical_alarm:{e.get('event_id')}"
        for e in open_alarms if e.get("class") == "CRITICAL"
    )
    data = {"gateway_running": g.get("running"), "uptime_s": g.get("uptime_s"), "cron": cron,
            "active_alarms": alarms, "cognitive_lane_stale_min": _stale(ev),
            "bridge_seq_last": ev[-1]["seq"] if ev else 0,
            "event_backlog": sum(1 for e in ev if e.get("seq", 0) > events.read_cursor()),
            "execution_readiness": {"ready": not blockers, "blockers": blockers}}
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
    decisions = _jlines(config.STATE / "DECISIONS.jsonl")
    rows = _mission_rows(kb.rows, ev, decisions)
    if status != "any":
        rows = [row for row in rows if row["status"] == status]
    trust = _worst(kb.trust, _EV)
    reconcile = any(row["reconcile_required"] for row in rows)
    notes = ["accepted mission requires a mission-linked Kanban card before active execution"] if reconcile else None
    return envelope.build("active_missions", _redact(rows), ["db:kanban tasks", "file:state/EVENTS.jsonl", "file:state/DECISIONS.jsonl"],
                          completeness="degraded" if trust == "DEGRADED" or reconcile else "complete", source_trust=trust,
                          notes=notes)
def mission_get(mission_id):
    kb = reader.get_kanban_rows()
    ev = _ev()
    decisions = _jlines(config.STATE / "DECISIONS.jsonl")
    mission = next((row for row in _mission_rows(kb.rows, ev, decisions) if row["mission_id"] == mission_id), None)
    if mission is None:
        return None  # -> E_NOT_FOUND
    scoped_decisions = _mission_decisions(decisions, mission_id)
    scoped_cards = _linked_cards(kb.rows, ev, mission_id)
    data = {"mission": mission, "cards": [{"card_id": c.get("card_id"), "title": c.get("title"), "status": c.get("status"),
                                             "assignee": c.get("assignee"), "heartbeat_at": c.get("heartbeat_at")} for c in scoped_cards],
            "evidence_refs": [d.get("evidence_ref") for d in scoped_decisions if d.get("evidence_ref")][:20],
            "cost_lines": _jlines(config.STATE / "ECONOMICS.jsonl"), "decisions": scoped_decisions[-20:]}
    return envelope.build("mission_get", _redact(data), ["db:kanban tasks", "file:DECISIONS.jsonl", "file:ECONOMICS.jsonl"],
                          completeness="degraded" if kb.trust == "DEGRADED" or mission["reconcile_required"] else "complete", source_trust=kb.trust,
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


def _decision_evidence_refs(limit=20, division_id=None):
    rows = []
    decisions = _jlines(config.STATE / "DECISIONS.jsonl")
    for decision in decisions[-limit:]:
        if division_id is not None:
            semantic = decision.get("semantic_object")
            if not isinstance(semantic, dict) or semantic.get("division_id") != division_id:
                continue
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


def _division_surface(surface, division_id):
    """Return a fail-closed copy containing only one registered division."""

    bounded = json.loads(json.dumps(surface, ensure_ascii=False))
    data = bounded.get("data")
    if isinstance(data, list):
        bounded["data"] = [
            row for row in data
            if isinstance(row, dict) and row.get("division_id") == division_id
        ]
    elif isinstance(data, dict) and isinstance(data.get("events"), list):
        data["events"] = [
            row for row in data["events"]
            if isinstance(row, dict) and row.get("division_id") == division_id
        ]
        data["truncated"] = False
    else:
        bounded["data"] = {}
        bounded["completeness"] = "degraded"
    bounded["notes"] = list(bounded.get("notes", [])) + [
        f"scoped to registered division {division_id}; untagged rows excluded"
    ]
    return bounded


def _division_health(surface, division_id):
    """Expose transport freshness without cross-division alarm detail."""

    bounded = json.loads(json.dumps(surface, ensure_ascii=False))
    data = bounded.get("data") if isinstance(bounded.get("data"), dict) else {}
    readiness = data.get("execution_readiness")
    bounded["data"] = {
        key: data.get(key)
        for key in (
            "gateway_running",
            "cognitive_lane_stale_min",
            "bridge_seq_last",
            "event_backlog",
        )
    }
    if isinstance(readiness, dict):
        blockers = readiness.get("blockers")
        bounded["data"]["execution_readiness"] = {
            "ready": readiness.get("ready") is True,
            "blocker_count": len(blockers) if isinstance(blockers, list) else None,
        }
    bounded["notes"] = list(bounded.get("notes", [])) + [
        f"division health projection for {division_id}; alarm detail and cron rows withheld"
    ]
    return bounded


def context_snapshot(principal_id, scope=None, since_seq=0, limit=config.CONTEXT_EVENT_LIMIT):
    granted = authority.authorize(
        principal_id,
        "context.snapshot.read",
        scope,
    )
    bounded_limit = min(max(limit, 1), 50)
    evidence_refs = _decision_evidence_refs()
    if granted.get("kind") == "division_decision_engine":
        division_id = granted.get("division_id")
        if not division_id:
            raise authority.AuthorizationError(
                "E_REGISTRY_INVALID",
                "division principal has no registered division_id",
            )
        surfaces = {
            "system_state": system_state(),
            "system_health": _division_health(system_health(), division_id),
            "active_missions": _division_surface(
                active_missions("any"),
                division_id,
            ),
            "recent_events": _division_surface(
                recent_events(since_seq, bounded_limit, "INFO"),
                division_id,
            ),
        }
        evidence_refs = _decision_evidence_refs(division_id=division_id)
    else:
        surfaces = {
            "system_state": system_state(),
            "system_health": system_health(),
            "active_missions": active_missions("any"),
            "recent_events": recent_events(since_seq, bounded_limit, "INFO"),
        }
    return snapshot.build(
        granted,
        surfaces,
        evidence_refs,
    )
