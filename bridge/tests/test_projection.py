# test_projection.py — fx-06: akurasi system_health + pemisahan lapisan reader/projection
import json, pathlib

from income_os_bridge import projection, envelope, config
from income_os_bridge.hermes_state_reader import ReaderResult

FX = pathlib.Path(__file__).parent / "fixtures" / "fx-06"


def _rr(d):
    return ReaderResult(d.get("rows", []), d.get("source", "cli"), d.get("trust", "VERIFIED"),
                        d.get("as_of", "2026-08-19T05:00:00Z"), d.get("complete", True))


def test_fx06_system_health_accuracy(monkeypatch):
    d = json.loads((FX / "input" / "reader.json").read_text(encoding="utf-8-sig"))
    monkeypatch.setattr(projection.reader, "get_gateway_status", lambda: _rr(d["gateway"]))
    monkeypatch.setattr(projection.reader, "get_cron_jobs", lambda: _rr(d["cron"]))
    monkeypatch.setattr(projection.events, "read_events", lambda: [])
    monkeypatch.setattr(projection.events, "read_cursor", lambda: 0)
    env = projection.system_health()
    exp = json.loads((FX / "expected.json").read_text(encoding="utf-8-sig"))
    assert env["data"]["gateway_running"] == exp["gateway_running"]
    assert [c["name"] for c in env["data"]["cron"]] == exp["cron_names"]
    assert env["data"]["cron"][0]["last_status"] == exp["cron_status_first"]
    assert env["source_trust"] == exp["source_trust"]
    assert env["completeness"] == exp["completeness"]
    assert env["data"]["cron"][1]["last_status"] is None


def test_fx06_reader_gagal_terlihat_buta(monkeypatch):
    monkeypatch.setattr(projection.reader, "get_gateway_status",
                        lambda: ReaderResult([], "none", "DEGRADED", "t", False, degraded_reason="x"))
    monkeypatch.setattr(projection.reader, "get_cron_jobs",
                        lambda: ReaderResult([], "none", "DEGRADED", "t", False, degraded_reason="x"))
    monkeypatch.setattr(projection.events, "read_events", lambda: [])
    monkeypatch.setattr(projection.events, "read_cursor", lambda: 0)
    env = projection.system_health()
    assert env["source_trust"] == "DEGRADED"
    assert env["completeness"] == "degraded"
    assert env["data"]["cron"] == []


def test_projection_no_sql_no_subprocess():
    src = (pathlib.Path(__file__).resolve().parents[1] / "income_os_bridge" / "projection.py").read_text(encoding="utf-8")
    for bad in ("sqlite3", "subprocess", "import os", "eval(", "exec(", "os.system"):
        assert bad not in src, f"projection menyentuh: {bad}"


def test_envelope_batas_32kb():
    big = ["x" * 500 for _ in range(4000)]
    env = envelope.build("recent_events", {"events": big}, ["test"], notes=None)
    assert env["completeness"] == "truncated"
    assert len(json.dumps(env, ensure_ascii=False).encode("utf-8")) <= config.MAX_RESP_BYTES
