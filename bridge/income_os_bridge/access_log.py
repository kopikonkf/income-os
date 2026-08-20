# access_log.py â€” catat setiap panggilan surface ke ACCESS.jsonl (audit lat).
import hashlib, json, pathlib
from . import config, envelope
def _hash(args):
    return hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
def log(tool, args, result_bytes, completeness, source_trust, rejected=False):
    rec = {"ts": envelope.now_iso(), "tool": tool, "args_hash": _hash(args or {}),
           "result_bytes": int(result_bytes or 0), "completeness": completeness,
           "source_trust": source_trust, "rejected": bool(rejected)}
    try:
        config.PROJ.mkdir(parents=True, exist_ok=True)
        with open(config.ACCESS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        pass
    return rec
def rejected_count():
    try:
        if not config.ACCESS_LOG.exists():
            return 0
        return sum(1 for ln in config.ACCESS_LOG.read_text(encoding="utf-8").splitlines()
                   if json.loads(ln).get("rejected"))
    except Exception:
        return 0
