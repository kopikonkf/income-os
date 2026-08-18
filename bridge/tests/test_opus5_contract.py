import json
from income_os_bridge import briefing, cli, events


def test_briefing_empty_economics_is_not_zero():
    rows = [{"event_id": "E-TEST", "seq": 1, "class": "INFO", "summary": "test"}]
    md = briefing.render(rows, [], [], since_seq=0)
    assert "belum ada baris ECONOMICS.jsonl" in md
    assert "revenue kumulatif VERIFIED: USD 0.00" not in md


def test_system_health_p0_envelope_is_degraded(capsys):
    cli.cmd_system_health(type("Args", (), {})())
    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "system_health"
    assert payload["completeness"] == "degraded"
    assert payload["source_trust"] == "ASSUMED"
