# envelope.py — as_of / completeness / source_trust untuk semua respons
import datetime, json
from . import config


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build(surface, data, sources, notes=None, completeness="complete", source_trust="ASSUMED"):
    env = {
        "surface": surface,
        "as_of": now_iso(),
        "completeness": completeness,
        "source_trust": source_trust,
        "operational_control_plane": config.OPERATIONAL_CONTROL_PLANE,
        "canonical_writer": config.CANONICAL_WRITER,
        "sources": sources,
        "notes": notes or [],
        "data": data,
    }
    body = json.dumps(env, ensure_ascii=False)
    if len(body.encode("utf-8")) > config.MAX_RESP_BYTES:
        env["completeness"] = "truncated"
        env["notes"] = list(env["notes"]) + [
            f"respons > {config.MAX_RESP_BYTES} B: dipotong; ambil sisa via paginasi"]
        if isinstance(data, list):
            env["data"] = data[:10]
        else:
            env["data"] = {}
    return env
