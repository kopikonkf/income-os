# DIE State Writer v0 -- SATU-SATUNYA physical writer EVENTS/DECISIONS/ECONOMICS
# Provider-neutral deterministic boundary; actors remain semantic authors.
# Original source: S2-B1-Bootstrap-Hermes-VPS.md (Opus 5) B1.6
import json, sys, os, time, pathlib, datetime, argparse
try:
    import msvcrt
except ImportError:
    msvcrt = None

STATE = pathlib.Path(os.environ.get("DIE_HOME", r"C:\DIE")) / "state"
CLASSES = ("INFO", "NOTICE", "WARNING", "CRITICAL", "STRATEGIC")


def _append(path, obj):
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "r+", encoding="utf-8", newline="\n") as f:
        f.seek(0, 2)
        pos = f.tell()
        if msvcrt is not None:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            f.seek(0, 2)
        f.write(line)
        f.flush()
        if msvcrt is not None:
            f.seek(pos)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def next_seq(path):
    if not path.exists() or path.stat().st_size == 0:
        return 1
    with open(path, "r", encoding="utf-8") as f:
        last = None
        for last in f:
            pass
    try:
        return json.loads(last)["seq"] + 1
    except Exception:
        return int(time.time())


def emit_event(cls, source, summary, mission_id=None, task_id=None, detail_ref=None):
    assert cls in CLASSES, f"kelas tidak dikenal: {cls}"
    p = STATE / "EVENTS.jsonl"
    seq = next_seq(p)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    ev = {
        "seq": seq, "event_id": f"E-{seq:06d}", "ts": ts, "class": cls,
        "source": source, "mission_id": mission_id, "task_id": task_id,
        "summary": summary[:140], "detail_ref": detail_ref,
        "wake": cls in ("CRITICAL", "STRATEGIC"),
    }
    _append(p, ev)
    print(json.dumps(ev, ensure_ascii=False))
    return ev


def emit_decision(choice, reason, decider="founder", klass="config",
                  alternatives_rejected=None, evidence_ref=None):
    p = STATE / "DECISIONS.jsonl"
    n = 0
    if p.exists() and p.stat().st_size > 0:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    m = str(d.get("decision_id", "")).replace("D-", "")
                    if m.isdigit():
                        n = max(n, int(m))
                except Exception:
                    pass
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    d = {
        "ts": ts, "decision_id": f"D-{n + 1:04d}", "class": klass,
        "choice": choice, "decider": decider, "reason": reason,
        "alternatives_rejected": alternatives_rejected or [],
        "evidence_ref": evidence_ref,
    }
    _append(p, d)
    print(json.dumps(d, ensure_ascii=False))
    return d


def main():
    ap = argparse.ArgumentParser(prog="die_event")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("event", help="tulis satu event")
    ev.add_argument("--class", dest="cls", required=True)
    ev.add_argument("--source", required=True)
    ev.add_argument("--summary", required=True)
    ev.add_argument("--mission-id")
    ev.add_argument("--task-id")
    ev.add_argument("--detail-ref")

    dec = sub.add_parser("decision", help="tulis satu keputusan")
    dec.add_argument("--choice", required=True)
    dec.add_argument("--reason", required=True)
    dec.add_argument("--decider", default="founder")
    dec.add_argument("--class", dest="klass", default="config")
    dec.add_argument("--evidence-ref")

    a = ap.parse_args()
    if a.cmd == "event":
        emit_event(a.cls, a.source, a.summary, a.mission_id, a.task_id, a.detail_ref)
    elif a.cmd == "decision":
        emit_decision(a.choice, a.reason, a.decider, a.klass, evidence_ref=a.evidence_ref)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
