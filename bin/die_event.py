# DIE State Writer v0 -- SATU-SATUNYA physical writer EVENTS/DECISIONS/ECONOMICS
# Provider-neutral deterministic boundary; actors remain semantic authors.
# Original source: S2-B1-Bootstrap-Hermes-VPS.md (Opus 5) B1.6
import argparse
import datetime
import json
import os
import pathlib
import sys
import time

try:
    import msvcrt
except ImportError:
    msvcrt = None

STATE = pathlib.Path(os.environ.get("DIE_HOME", r"C:\DIE")) / "state"
CLASSES = ("INFO", "NOTICE", "WARNING", "CRITICAL", "STRATEGIC")


def _append(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "r+", encoding="utf-8", newline="\n") as handle:
        handle.seek(0, 2)
        pos = handle.tell()
        if msvcrt is not None:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            handle.seek(0, 2)
        handle.write(line)
        handle.flush()
        if msvcrt is not None:
            handle.seek(pos)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _json_lines(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows = []
    with open(path, "r", encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def next_seq(path):
    rows = _json_lines(path)
    if not rows:
        return 1
    try:
        return int(rows[-1]["seq"]) + 1
    except (KeyError, TypeError, ValueError):
        return int(time.time())


def emit_event(
    cls,
    source,
    summary,
    mission_id=None,
    task_id=None,
    detail_ref=None,
    *,
    division_id=None,
    dedupe_key=None,
    alarm_state=None,
    resolves_event_id=None,
):
    assert cls in CLASSES, f"kelas tidak dikenal: {cls}"
    if alarm_state not in (None, "open", "resolved"):
        raise ValueError("alarm_state harus open atau resolved")
    if alarm_state == "open" and cls not in ("WARNING", "CRITICAL"):
        raise ValueError("alarm open harus WARNING atau CRITICAL")
    if alarm_state == "resolved" and not (dedupe_key or resolves_event_id):
        raise ValueError("alarm resolved membutuhkan dedupe_key atau resolves_event_id")
    path = STATE / "EVENTS.jsonl"
    seq = next_seq(path)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    event = {
        "seq": seq,
        "event_id": f"E-{seq:06d}",
        "ts": ts,
        "class": cls,
        "source": source,
        "division_id": division_id,
        "mission_id": mission_id,
        "task_id": task_id,
        "summary": summary[:140],
        "detail_ref": detail_ref,
        "wake": cls in ("CRITICAL", "STRATEGIC"),
    }
    if dedupe_key is not None:
        event["dedupe_key"] = dedupe_key
    if alarm_state is not None:
        event["alarm_state"] = alarm_state
    if resolves_event_id is not None:
        event["resolves_event_id"] = resolves_event_id
    _append(path, event)
    print(json.dumps(event, ensure_ascii=False))
    return event


def emit_decision(
    choice,
    reason,
    decider="founder",
    klass="config",
    alternatives_rejected=None,
    evidence_ref=None,
    *,
    request_id=None,
    identity_id=None,
    scope=None,
    authority=None,
    source_snapshot=None,
    evidence_refs=None,
    semantic_object=None,
    print_record=True,
):
    if semantic_object is not None and request_id is None:
        raise ValueError("semantic_object membutuhkan request_id")
    if klass == "mission_ratification":
        if request_id is None:
            raise ValueError("mission_ratification membutuhkan request_id")
        if not isinstance(semantic_object, dict):
            raise ValueError("mission_ratification membutuhkan semantic_object")
        missing = [
            key for key in ("division_id", "mission_id")
            if not semantic_object.get(key)
        ]
        if missing:
            raise ValueError(
                "mission_ratification semantic_object kehilangan "
                + ", ".join(missing)
            )
    path = STATE / "DECISIONS.jsonl"
    rows = _json_lines(path)
    number = 0
    for row in rows:
        marker = str(row.get("decision_id", "")).replace("D-", "")
        if marker.isdigit():
            number = max(number, int(marker))

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    decision = {
        "ts": ts,
        "decision_id": f"D-{number + 1:04d}",
        "class": klass,
        "choice": choice,
        "decider": decider,
        "reason": reason,
        "alternatives_rejected": alternatives_rejected or [],
        "evidence_ref": evidence_ref,
    }
    if request_id is not None:
        decision.update(
            {
                "schema_version": "die.decision.v1",
                "request_id": request_id,
                "identity_id": identity_id,
                "scope": scope,
                "authority": authority,
                "source_snapshot": source_snapshot,
                "evidence_refs": evidence_refs or [],
                "semantic_object": semantic_object or {},
                "committed_by": "die-state-manager",
            }
        )

    _append(path, decision)
    if print_record:
        print(json.dumps(decision, ensure_ascii=False))
    return decision


def commit_normalized_decision(normalized):
    """Commit one gateway-validated decision with sequential replay protection."""

    path = STATE / "DECISIONS.jsonl"
    request_id = normalized["request_id"]
    for row in _json_lines(path):
        if row.get("request_id") == request_id:
            return {"record": row, "replayed": True}

    obj = normalized["object"]
    evidence_refs = normalized.get("evidence_refs", [])
    evidence_ref = evidence_refs[0]["ref"] if evidence_refs else None
    source = normalized["source_snapshot"]
    decision = emit_decision(
        obj["choice"],
        obj["reason"],
        decider=normalized["principal_id"],
        klass=obj["decision_class"],
        alternatives_rejected=obj.get("alternatives_rejected", []),
        evidence_ref=evidence_ref,
        request_id=request_id,
        identity_id=normalized["identity_id"],
        scope=normalized["scope"],
        authority=normalized["authority"],
        source_snapshot={
            "snapshot_id": source["snapshot_id"],
            "snapshot_version": source["snapshot_version"],
            "events_next_seq": source.get("source_cursor", {}).get(
                "events_next_seq"
            ),
            "expires_at": source["freshness"]["expires_at"],
        },
        evidence_refs=evidence_refs,
        semantic_object=obj,
        print_record=False,
    )
    return {"record": decision, "replayed": False}


def main():
    parser = argparse.ArgumentParser(prog="die_event")
    sub = parser.add_subparsers(dest="cmd", required=True)

    event_parser = sub.add_parser("event", help="tulis satu event")
    event_parser.add_argument("--class", dest="cls", required=True)
    event_parser.add_argument("--source", required=True)
    event_parser.add_argument("--summary", required=True)
    event_parser.add_argument("--mission-id")
    event_parser.add_argument("--division-id")
    event_parser.add_argument("--task-id")
    event_parser.add_argument("--detail-ref")
    event_parser.add_argument("--dedupe-key")
    event_parser.add_argument("--alarm-state", choices=("open", "resolved"))
    event_parser.add_argument("--resolves-event-id")

    decision_parser = sub.add_parser("decision", help="tulis satu keputusan")
    decision_parser.add_argument("--choice", required=True)
    decision_parser.add_argument("--reason", required=True)
    decision_parser.add_argument("--decider", default="founder")
    decision_parser.add_argument("--class", dest="klass", default="config")
    decision_parser.add_argument("--evidence-ref")

    args = parser.parse_args()
    if args.cmd == "event":
        emit_event(
            args.cls,
            args.source,
            args.summary,
            args.mission_id,
            args.task_id,
            args.detail_ref,
            division_id=args.division_id,
            dedupe_key=args.dedupe_key,
            alarm_state=args.alarm_state,
            resolves_event_id=args.resolves_event_id,
        )
    elif args.cmd == "decision":
        emit_decision(
            args.choice,
            args.reason,
            args.decider,
            args.klass,
            evidence_ref=args.evidence_ref,
        )
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
