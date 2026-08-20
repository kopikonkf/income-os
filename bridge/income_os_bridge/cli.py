# cli.py - entrypoint P0+P1: python -m income_os_bridge <surface>
import argparse, json, pathlib, sys
from . import config, events, envelope, redact, briefing, projection


SURFACES = [
    ("recent_events", [("since_seq", "int", None, 0), ("limit", "int", None, config.PAGE_DEFAULT), ("min_class", "str", list(config.CLASSES), "INFO")]),
    ("system_health", []), ("system_state", []),
    ("active_missions", [("status", "str", ["any", "active", "paused", "blocked"], "active")]),
    ("mission_get", [("mission_id", "str", None, None, True)]),
    ("workers", []), ("scheduled_jobs", []),
    ("capabilities", [("status", "str", ["any", "VERIFIED", "ASSUMED", "ABSENT"], "any")]),
    ("search_sessions", [("query", "str", None, None, True), ("limit", "int", None, 10)]),
    ("session_get", [("session_id", "str", None, None, True), ("max_turns", "int", None, config.MAX_TURNS)]),
    ("briefing_get", [("latest", "bool", None, True)]),
]


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _proxy(name, params):
    def fn(a):
        res = getattr(projection, name)(**{k: getattr(a, k) for k in params})
        if res is None:
            # Return error envelope like MCP server does
            _out(envelope.build(name, None, [], notes=[f"{name}: not found"], completeness="complete", source_trust="ASSUMED"))
        else:
            _out(res)
    return fn


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
    _out({"surface": "briefing", "as_of": envelope.now_iso(), "completeness": "complete", "source_trust": "VERIFIED",
          "sources": ["file:state/EVENTS.jsonl"],
          "notes": [f"{len(new)} event baru sejak seq {cursor}; wake={wake_ids}; deferred={deferred_ids}"]})


def main(argv=None):
    # Fix UnicodeEncodeError on Windows: stdout default is cp1252, but JSON output contains non-ASCII chars
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="income_os_bridge")
    sub = ap.add_subparsers(dest="surface", required=True)
    for name, params in SURFACES:
        p = sub.add_parser(name)
        for (flag, typ, choices, default, *req) in params:
            kw = dict(type=(int if typ == "int" else (bool if typ == "bool" else str)), default=default)
            if choices:
                kw["choices"] = choices
            if req:
                kw["required"] = True
            p.add_argument("--" + flag, **kw)
        p.set_defaults(fn=_proxy(name, [x[0] for x in params]))
    p = sub.add_parser("briefing"); p.add_argument("--out"); p.set_defaults(fn=cmd_briefing)
    a = ap.parse_args(argv)
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
