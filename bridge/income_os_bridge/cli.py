# cli.py — entrypoint P0: python -m income_os_bridge <surface>
import argparse, json, pathlib, sys
from . import config, events, envelope, redact, briefing

def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def cmd_recent_events(a):
    data = events.recent_events(since_seq=a.since_seq, limit=a.limit, min_class=a.min_class)
    _out(envelope.build("recent_events", data, ["file:state/EVENTS.jsonl"],
                        completeness="truncated" if data["truncated"] else "complete",
                        notes=["P0: reader file-only; schema Hermes belum diverifikasi (SCHEMA_NOTES.md kosong)"]))

def cmd_system_health(a):
    _out(envelope.build("system_health", events.system_health(), ["file:state/EVENTS.jsonl"],
                        notes=["P0: gateway/cron belum dibaca (P1 hermes_state_reader); nilai None = belum tersedia"]))

def cmd_briefing(a):
    out = pathlib.Path(a.out) if a.out else config.PROJ
    out.mkdir(parents=True, exist_ok=True)
    cursor = events.read_cursor()
    new = sorted([e for e in events.read_events() if e.get("seq", 0) > cursor], key=lambda e: e.get("seq", 0))
    for e in new:
        e["class"] = e.get("class") or events.classify(e)
        e["wake"] = e["class"] in config.WAKE_CLASSES
    new = [redact.redact_event(e) for e in new]
    wake_ids, deferred_ids = events.apply_gate(new)
    (out / "EVENTS.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in new) + ("\n" if new else ""), encoding="utf-8")
    bpath = out / "BRIEFING.md"
    last_briefing = None
    if bpath.exists():
        for line in bpath.read_text(encoding="utf-8").splitlines():
            if line.startswith("# BRIEFING "):
                last_briefing = line[len("# BRIEFING "):].strip(); break
    bpath.write_text(briefing.render(new, wake_ids, deferred_ids, cursor, last_briefing=last_briefing), encoding="utf-8", newline="\n")
    events.write_cursor(new[-1]["seq"] if new else cursor)
    flag = out / "WAKE.flag"
    if wake_ids:
        flag.write_text(",".join(wake_ids), encoding="utf-8")
    elif flag.exists():
        flag.unlink()
    _out({"surface": "briefing", "as_of": envelope.now_iso(), "completeness": "complete", "source_trust": "ASSUMED",
          "sources": ["file:state/EVENTS.jsonl"],
          "notes": [f"{len(new)} event baru sejak seq {cursor}; wake={wake_ids}; deferred={deferred_ids}"]})

def main(argv=None):
    ap = argparse.ArgumentParser(prog="income_os_bridge")
    sub = ap.add_subparsers(dest="surface", required=True)
    p1 = sub.add_parser("recent_events")
    p1.add_argument("--since-seq", type=int, default=0)
    p1.add_argument("--limit", type=int, default=config.PAGE_DEFAULT)
    p1.add_argument("--min-class", choices=config.CLASSES, default="INFO")
    p1.set_defaults(fn=cmd_recent_events)
    p2 = sub.add_parser("system_health"); p2.set_defaults(fn=cmd_system_health)
    p3 = sub.add_parser("briefing"); p3.add_argument("--out"); p3.set_defaults(fn=cmd_briefing)
    a = ap.parse_args(argv)
    a.fn(a)
    return 0

if __name__ == "__main__":
    sys.exit(main())