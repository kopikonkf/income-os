# events.py — baca EVENTS.jsonl, klasifikasi, cognitive gate
import json, pathlib
from . import config, redact

_RULES = (
    ("STRATEGIC", ("pendapatan pertama", "terverifikasi", "kill criteria", "terpenuhi", "otonomi berubah", "artifact pertama", "sinyal pasar")),
    ("CRITICAL", ("melampaui batas", "di luar allowed", "di luar scope", "pelanggaran", "429", "401", "mati", "terhenti", "bridge exit", "stale")),
    ("WARNING", ("gagal", "blocked", "heartbeat basi", "schema drift", "ground-truth mismatch", "tidak lengkap")),
    ("NOTICE", ("retry", "sesi kognitif dibuka", "20% di atas")),
)

def classify(ev):
    text = f"{ev.get('summary', '')} {ev.get('source', '')}".lower()
    for cls, keys in _RULES:
        if any(k in text for k in keys):
            return cls
    return "INFO"

def read_events(path=None):
    p = pathlib.Path(path) if path else config.EVENTS
    out = []
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out

def read_cursor():
    if config.CURSOR.exists():
        try:
            return int(config.CURSOR.read_text(encoding="utf-8").strip())
        except ValueError:
            return 0
    return 0

def write_cursor(seq):
    config.CURSOR.parent.mkdir(parents=True, exist_ok=True)
    config.CURSOR.write_text(str(seq), encoding="utf-8")

class WakeState:
    def __init__(self, wakes_today=0, minutes_since_last_wake=config.WAKE_MIN_GAP_MIN, woke_keys_24h=None):
        self.wakes_today = wakes_today
        self.minutes_since_last_wake = minutes_since_last_wake
        self.woke_keys_24h = set(woke_keys_24h or [])
        self.deferred = []

    def should_wake(self, ev):
        if ev.get("class") not in config.WAKE_CLASSES:
            return False
        if self.wakes_today >= config.WAKE_PER_DAY:
            self.deferred.append(ev); return False
        if self.minutes_since_last_wake < config.WAKE_MIN_GAP_MIN:
            self.deferred.append(ev); return False
        dk = ev.get("dedupe_key")
        if dk and dk in self.woke_keys_24h:
            return False
        return True

def apply_gate(rows):
    st = WakeState()
    wake_ids, deferred_ids = [], []
    for e in rows:
        if st.should_wake(e):
            wake_ids.append(e["event_id"])
            st.wakes_today += 1
            if e.get("dedupe_key"):
                st.woke_keys_24h.add(e["dedupe_key"])
        elif e["event_id"] in [d["event_id"] for d in st.deferred]:
            deferred_ids.append(e["event_id"])
    return wake_ids, deferred_ids

def recent_events(since_seq=0, limit=config.PAGE_DEFAULT, min_class="INFO"):
    limit = min(limit, config.PAGE_MAX)
    rows = sorted([r for r in read_events() if r.get("seq", 0) > since_seq], key=lambda r: r.get("seq", 0))
    out = []
    for r in rows:
        cls = r.get("class") or classify(r)
        if config.CLASS_ORDER.get(cls, 0) < config.CLASS_ORDER.get(min_class, 0):
            continue
        out.append({"event_id": r.get("event_id"), "seq": r.get("seq"), "ts": r.get("ts"), "class": cls, "source": r.get("source"), "summary": redact.redact(r.get("summary", "")), "wake": cls in config.WAKE_CLASSES})
    truncated = len(out) > limit
    out = out[:limit]
    next_seq = out[-1]["seq"] if out else since_seq
    return {"events": out, "since_seq": since_seq, "next_seq": next_seq, "truncated": truncated}

def system_health():
    rows = read_events()
    cursor = read_cursor()
    last_seq = rows[-1]["seq"] if rows else 0
    backlog = sum(1 for r in rows if r.get("seq", 0) > cursor)
    return {"gateway_running": None, "uptime_s": None, "cron": [], "active_alarms": [], "cognitive_lane_stale_min": None, "bridge_seq_last": last_seq, "event_backlog": backlog}