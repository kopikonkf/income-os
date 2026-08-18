# test_fx07.py — klasifikasi recent_events + cognitive gate (B2.4.3/B2.4.4)
import json, pathlib

from income_os_bridge import config, events, briefing

FX = pathlib.Path(__file__).parent / "fixtures" / "fx-07"


def _load_raw():
    lines = (FX / "input" / "raw_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines]


def _expected():
    return json.loads((FX / "expected.json").read_text(encoding="utf-8"))


def test_classification():
    rows = _load_raw()
    exp = _expected()
    got = [events.classify(e) for e in rows]
    assert got == exp["classes"], f"mismatch: {got}"


def test_wake_only_on_critical_strategic():
    rows = _load_raw()
    exp = _expected()
    eligible = [e["seq"] for e, cls in zip(rows, exp["classes"]) if cls in config.WAKE_CLASSES]
    assert eligible == exp["wake_eligible_seq"]


def test_cognitive_gate_budget_and_deferred():
    rows = _load_raw()
    exp = _expected()
    for e, cls in zip(rows, exp["classes"]):
        e["class"] = cls
    wake_ids, deferred_ids = events.apply_gate(rows)
    wake_seqs = [e["seq"] for e in rows if e["event_id"] in wake_ids]
    defer_seqs = [e["seq"] for e in rows if e["event_id"] in deferred_ids]
    assert wake_seqs == exp["wake_after_gate_seq"], f"wake: {wake_seqs}"
    assert defer_seqs == exp["deferred_seq"], f"deferred: {defer_seqs}"
    assert len(deferred_ids) == exp["deferred_count"]


def test_deferred_appears_in_briefing_section2():
    rows = _load_raw()
    exp = _expected()
    for e, cls in zip(rows, exp["classes"]):
        e["class"] = cls
    wake_ids, deferred_ids = events.apply_gate(rows)
    md = briefing.render(rows, wake_ids, deferred_ids, since_seq=0)
    assert "## 2." in md
    for e in rows:
        if e["event_id"] in deferred_ids:
            assert e["event_id"] in md, f"deferred {e['event_id']} hilang dari bagian 2"