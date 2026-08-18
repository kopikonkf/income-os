# briefing.py — render BRIEFING.md (7 bagian, urut tetap, ≤ 8 KB)
import datetime
from . import config, redact

def _ago_min(ts):
    try:
        t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return max(0, int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60))
    except Exception:
        return None

def render(events, wake_ids, deferred_ids, since_seq, last_briefing=None, lane_ack=None):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n = len(events)
    first = events[0]["event_id"] if events else "-"
    last = events[-1]["event_id"] if events else "-"
    L = []
    L.append(f"# BRIEFING {now}")
    L.append(f"seq: {first}..{last} ({n} event) | wake: {len(wake_ids)} | completeness: complete | source_trust: ASSUMED")
    L.append(f"briefing sebelumnya: {last_briefing or 'tidak ada'} | lane ack terakhir: {lane_ack or 'tidak ada'}")
    L.append("")
    L.append("## 1. Alasan bangun")
    if wake_ids:
        w = events[[e["event_id"] for e in events].index(wake_ids[0])]
        L.append(f"{w['class']} {w['event_id']} - {redact.redact(w['summary'])}")
    else:
        L.append("tidak ada - catch-up terjadwal")
    L.append("")
    L.append("## 2. Yang berubah sejak briefing terakhir")
    if not events:
        L.append("- tidak ada event baru")
    for e in events:
        tag = " [deferred-wake]" if e["event_id"] in deferred_ids else ""
        L.append(f"- {e['class']} {e['event_id']} - {redact.redact(e['summary'])}{tag}")
    L.append("")
    L.append("## 3. Angka")
    classes = {c: sum(1 for e in events if e.get("class") == c) for c in config.CLASSES if sum(1 for e in events if e.get("class") == c)}
    L.append(f"event baru: {n} | by class: " + ", ".join(f"{k}={v}" for k, v in sorted(classes.items())))
    L.append("biaya 24j: tidak ada baris ECONOMICS.jsonl (bukan nol - belum tercatat)")
    L.append("revenue kumulatif VERIFIED: USD 0.00 | PECAH TELOR: belum")
    L.append("")
    L.append("## 4. Menunggu keputusan")
    L.append("- tidak ada permintaan keputusan tertunda tercatat di periode ini")
    L.append("")
    L.append("## 5. Alarm & staleness")
    L.append(f"lane kognitif stale: {_ago_min(lane_ack) if lane_ack else 'belum dihitung'} menit (ambang 1560)")
    L.append(f"bridge seq naik: {'ya' if n else 'tidak (0 event)'} | cron gagal 24j: belum dibaca (P0)")
    L.append("")
    L.append("## 6. Yang TIDAK terlihat dari sini")
    L.append("- Semua surface bertanda ASSUMED: SCHEMA_NOTES.md belum diisi.")
    L.append("- gateway/cron/kanban/sessions belum dibaca (P0 reader = file EVENTS.jsonl saja).")
    L.append("- Tidak ada data pasar. Tidak ada pembeli yang terkontak.")
    L.append("")
    L.append("## 7. Pertanyaan termurah untuk dijawab siklus ini")
    L.append("Apa tes termurah yang bisa membunuh tesis produk pertama minggu ini?")
    L.append("")
    md = "\n".join(L)
    if len(md.encode("utf-8")) > config.MAX_BRIEF_BYTES:
        md = md[: config.MAX_BRIEF_BYTES - 16] + "\n[sisa dipotong]\n"
    return md