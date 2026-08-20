import json
from income_os_bridge import briefing, projection
from income_os_bridge.hermes_state_reader import ReaderResult


def test_briefing_empty_economics_is_not_zero():
    rows = [{"event_id": "E-TEST", "seq": 1, "class": "INFO", "summary": "test"}]
    md = briefing.render(rows, [], [], since_seq=0)
    assert "belum ada baris ECONOMICS.jsonl" in md
    assert "revenue kumulatif VERIFIED: USD 0.00" not in md


def test_system_health_p1_envelope_verified(monkeypatch):
    monkeypatch.setattr(projection.reader, "get_gateway_status",
                        lambda: ReaderResult([{"running": True, "uptime_s": None, "main_provider": None,
                                               "main_model": None, "aux_provider": None, "last_error": None}],
                                             "cli", "VERIFIED", "t", True))
    monkeypatch.setattr(projection.reader, "get_cron_jobs",
                        lambda: ReaderResult([], "cli", "VERIFIED", "t", True))
    monkeypatch.setattr(projection.events, "read_events", lambda: [])
    monkeypatch.setattr(projection.events, "read_cursor", lambda: 0)
    payload = projection.system_health()
    assert payload["surface"] == "system_health"
    assert payload["completeness"] == "complete"
    assert payload["source_trust"] == "VERIFIED"
    assert payload["data"]["gateway_running"] is True
    assert "bridge_seq_last" in payload["data"]
