import json, re, sys, time
from collections import deque
from . import authority, config, projection, snapshot, access_log
SERVER_NAME = "income-os-bridge"
SERVER_VERSION = "0.5.0"
SERVER_INSTRUCTIONS = (
    "Canonical DIE Decision Fabric P0/P1. Operational control plane: "
    f"{config.OPERATIONAL_CONTROL_PLANE}; canonical writer: "
    f"{config.CANONICAL_WRITER}. Use context_snapshot before Executive "
    "reasoning. This local CLI/stdio server is read-only: it provides bounded "
    "semantic state and evidence, never raw filesystem, credentials, or mutation. "
    "P2 network transport remains optional and separately Founder-gated."
)
TOOLS = {
    "context_snapshot": [("principal_id", "str", True, r"^[a-z0-9][a-z0-9-]{1,63}$", None, None, None, None),
                         ("scope", "str", False, r"^[a-z0-9][a-z0-9_:-]{1,63}$", None, None, None, None),
                         ("since_seq", "int", False, None, None, 0, None, 0),
                         ("limit", "int", False, None, None, 1, 50, config.CONTEXT_EVENT_LIMIT)],
    "system_health": [],
    "system_state": [],
    "active_missions": [("status", "str", False, None, ["any", "active", "paused", "blocked"], None, None, "active")],
    "mission_get": [("mission_id", "str", True, r"^M-[0-9]{3,6}$", None, None, None, None)],
    "workers": [],
    "scheduled_jobs": [],
    "capabilities": [("status", "str", False, None, ["any", "VERIFIED", "ASSUMED", "ABSENT"], None, None, "any")],
    "recent_events": [("since_seq", "int", False, None, None, 0, None, 0),
                       ("limit", "int", False, None, None, 1, 200, config.PAGE_DEFAULT),
                       ("min_class", "str", False, None, list(config.CLASSES), None, None, "INFO")],
    "search_sessions": [("query", "str", True, None, None, 2, 120, None),
                         ("limit", "int", False, None, None, None, 20, 10)],
    "session_get": [("session_id", "str", True, r"^[A-Za-z0-9_-]+$", None, None, 64, None),
                     ("max_turns", "int", False, None, None, None, 20, 20)],
    "briefing_get": [("latest", "bool", False, None, None, None, None, True)],
}
FORBIDDEN = re.compile(
    r"\b(select|union|insert|update|delete|drop|alter|create)\b|\b(exec|eval|os\.system|subprocess)\b|"
    r"(\.\./|\.\.\\)|(^|[\\/])[a-z]:[\\/]|(&|;|\||`|\$\(|\|\||&&)|"
    r"(sk-[A-Za-z0-9]|password|secret|token|bearer|api[_-]?key|\.env)",
    re.IGNORECASE)
class RateLimit:
    def __init__(self):
        self.times = deque()
    def allow(self):
        now = time.time()
        while self.times and now - self.times[0] > config.RATE_WINDOW_S:
            self.times.popleft()
        if len(self.times) >= config.RATE_LIMIT:
            return False
        self.times.append(now)
        return True
_RATE = RateLimit()
_DISPATCH = {
    "context_snapshot": lambda a: projection.context_snapshot(a["principal_id"], a.get("scope"), a.get("since_seq", 0), a.get("limit", config.CONTEXT_EVENT_LIMIT)),
    "system_health": lambda a: projection.system_health(),
    "system_state": lambda a: projection.system_state(),
    "active_missions": lambda a: projection.active_missions(a.get("status", "active")),
    "mission_get": lambda a: projection.mission_get(a["mission_id"]),
    "workers": lambda a: projection.workers(),
    "scheduled_jobs": lambda a: projection.scheduled_jobs(),
    "capabilities": lambda a: projection.capabilities(a.get("status", "any")),
    "recent_events": lambda a: projection.recent_events(a.get("since_seq", 0), a.get("limit", config.PAGE_DEFAULT), a.get("min_class", "INFO")),
    "search_sessions": lambda a: projection.search_sessions(a["query"], a.get("limit", 10)),
    "session_get": lambda a: projection.session_get(a["session_id"], a.get("max_turns", 20)),
    "briefing_get": lambda a: projection.briefing_get(a.get("latest", True)),
}
def _err(code, msg):
    return {"isError": True, "content": [{"type": "text", "text": f"{code}: {msg}"}]}
def validate(name, args):
    """None jika lolos; (code, msg) jika ditolak (penegak fx-08)."""
    spec = TOOLS.get(name)
    if spec is None:
        return ("E_NO_RAW_ACCESS", f"tool tidak dikenal: {name}")
    args = args or {}
    if not isinstance(args, dict):
        return ("E_NO_RAW_ACCESS", "args harus object")
    allowed = {f[0] for f in spec}
    for key in args:
        if key not in allowed:
            return ("E_NO_RAW_ACCESS", f"field di luar daftar: {key}")
    for (field, typ, required, pattern, enum, mn, mx, default) in spec:
        if field not in args:
            if required:
                return ("E_NO_RAW_ACCESS", f"field wajib: {field}")
            continue
        v = args[field]
        if typ == "int" and not isinstance(v, int):
            return ("E_NO_RAW_ACCESS", f"{field} harus integer")
        if typ == "str" and not isinstance(v, str):
            return ("E_NO_RAW_ACCESS", f"{field} harus string")
        if isinstance(v, str):
            if pattern and not re.fullmatch(pattern, v):
                return ("E_NO_RAW_ACCESS", f"{field} gagal pola {pattern}")
            if mn is not None and len(v) < mn:
                return ("E_NO_RAW_ACCESS", f"{field} terlalu pendek")
            if mx is not None and len(v) > mx:
                return ("E_TOO_LARGE", f"{field} melebihi batas {mx}")
            if FORBIDDEN.search(v):
                return ("E_NO_RAW_ACCESS", f"{field} memuat konten terlarang")
        if enum and v not in enum:
            return ("E_NO_RAW_ACCESS", f"{field} nilai tidak valid: {v}")
        if isinstance(v, int) and mn is not None and v < mn:
            return ("E_NO_RAW_ACCESS", f"{field} di bawah minimum")
        if isinstance(v, int) and mx is not None and v > mx:
            return ("E_TOO_LARGE", f"{field} melebihi batas {mx}")
    return None
def call_tool(name, args):
    args = args or {}
    v = validate(name, args)
    if v:
        access_log.log(name, args, 0, "rejected", "ASSUMED", rejected=True)
        return _err(*v)
    if not _RATE.allow():
        access_log.log(name, args, 0, "rejected", "ASSUMED", rejected=True)
        return _err("E_RATE_LIMIT", "> 60 panggilan surface / jam")
    try:
        res = _DISPATCH[name](args)
    except (authority.AuthorizationError, snapshot.SnapshotError) as e:
        access_log.log(name, args, 0, "rejected", "ASSUMED", rejected=True)
        return _err(e.code, e.message)
    except Exception as e:
        access_log.log(name, args, 0, "degraded", "DEGRADED", rejected=False)
        return _err("E_DEGRADED", f"reader/pengolahan gagal: {e}")
    if res is None:
        access_log.log(name, args, 0, "complete", "ASSUMED", rejected=True)
        return _err("E_NOT_FOUND", "mission_id/session_id tidak ada")
    body = json.dumps(res, ensure_ascii=False).encode("utf-8")
    access_log.log(name, args, len(body), res.get("completeness", "complete"), res.get("source_trust", "ASSUMED"))
    return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}]}
def _handle(msg):
    if not isinstance(msg, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "invalid request"},
        }
    method = msg.get("method")
    ident = msg.get("id")
    raw_params = msg.get("params")
    if raw_params is not None and not isinstance(raw_params, dict):
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "error": {"code": -32602, "message": "invalid params"},
        }
    params = raw_params or {}
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": SERVER_INSTRUCTIONS,
        }}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "tools": [_tool_definition(n) for n in sorted(TOOLS)],
        }}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        return {"jsonrpc": "2.0", "id": ident, "result": call_tool(name, args)}
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "method tidak dikenal"}}

def _schema(name):
    props, required = {}, []
    for (field, typ, req, pattern, enum, mn, mx, default) in TOOLS[name]:
        p = {"type": {"str": "string", "int": "integer", "bool": "boolean"}.get(typ, "string")}
        if pattern:
            p["pattern"] = pattern
        if enum:
            p["enum"] = enum
        if typ == "int":
            if mn is not None:
                p["minimum"] = mn
            if mx is not None:
                p["maximum"] = mx
        else:
            if mn is not None:
                p["minLength"] = mn
            if mx is not None:
                p["maxLength"] = mx
        props[field] = p
        if req:
            required.append(field)
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}
def _tool_definition(name):
    description = (
        "Use this before Executive reasoning to obtain a bounded, fresh semantic "
        "snapshot with typed evidence."
        if name == "context_snapshot"
        else f"Use this to read the bounded DIE semantic surface {name}."
    )
    return {
        "name": name,
        "description": description,
        "inputSchema": _schema(name),
        "annotations": {
            "title": "Read " + name.replace("_", " ").title(),
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }
def serve():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        resp = _handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0
if __name__ == "__main__":
    raise SystemExit(serve())
