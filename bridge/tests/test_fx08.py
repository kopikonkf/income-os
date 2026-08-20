# test_fx08.py — no-raw-access (6 injeksi), redact kredensial (fx-08c), tanpa tulis liar (fx-08d)
import json, pathlib

from income_os_bridge import mcp_server, redact, config, projection

FX = pathlib.Path(__file__).parent / "fixtures"


def _payloads():
    return json.loads((FX / "fx-08" / "input" / "payloads.json").read_text(encoding="utf-8-sig"))


def test_fx08_enam_payload_ditolak():
    payloads = _payloads()
    assert len(payloads) == 6
    for p in payloads:
        v = mcp_server.validate(p["name"], p["args"])
        assert v is not None, f"payload lolos validasi: {p}"
        assert v[0] in ("E_NO_RAW_ACCESS", "E_TOO_LARGE"), f"kode salah: {v}"


def test_fx08_call_tool_rejected_tercatat(monkeypatch, tmp_path):
    log = tmp_path / "ACCESS.jsonl"
    monkeypatch.setattr(config, "ACCESS_LOG", log)
    res = mcp_server.call_tool("search_sessions", {"query": "x'; DROP TABLE sessions;--"})
    assert res.get("isError") is True
    assert res["content"][0]["text"].startswith("E_NO_RAW_ACCESS")
    assert "rejected" in log.read_text(encoding="utf-8")


def test_fx08c_redact_kredensial():
    lines = (FX / "fx-08c" / "input" / "secrets.txt").read_text(encoding="utf-8-sig").splitlines()
    outs = [redact.redact(ln) for ln in lines]
    for ln, out in zip(lines, outs):
        assert "[REDACTED]" in out, f"tidak teredact: {ln}"
        for secret in ("sk-proj-abcdef1234567890", "sk-111222333", "hunter2secret", "tok_12345"):
            assert secret not in out


def test_fx08d_tidak_ada_tulis_di_luar_projection(monkeypatch, tmp_path):
    home = tmp_path / "die"
    st, proj = home / "state", home / "state" / "projection"
    proj.mkdir(parents=True)
    monkeypatch.setattr(config, "STATE", st)
    monkeypatch.setattr(config, "EVENTS", st / "EVENTS.jsonl")
    monkeypatch.setattr(config, "PROJ", proj)
    monkeypatch.setattr(config, "PROJ_EVENTS", proj / "EVENTS.jsonl")
    monkeypatch.setattr(config, "BRIEFING", proj / "BRIEFING.md")
    monkeypatch.setattr(config, "CURSOR", proj / ".cursor")
    monkeypatch.setattr(config, "ACCESS_LOG", proj / "ACCESS.jsonl")
    dummy = {"surface": "x", "as_of": "t", "completeness": "complete", "source_trust": "VERIFIED",
             "sources": [], "notes": [], "data": {}}
    for fn in ("system_health", "system_state", "active_missions", "mission_get", "workers",
               "scheduled_jobs", "capabilities", "recent_events", "search_sessions",
               "session_get", "briefing_get"):
        monkeypatch.setattr(projection, fn, lambda *a, **k: dummy)

    def snap(root):
        return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size)
                for p in root.rglob("*") if p.is_file()}

    before = snap(home)
    calls = {"mission_get": {"mission_id": "M-0001"}, "session_get": {"session_id": "abc123"},
             "search_sessions": {"query": "halo"}}
    for name in sorted(mcp_server.TOOLS):
        mcp_server.call_tool(name, calls.get(name, {}))
    after = snap(home)
    for rel, sig in after.items():
        if before.get(rel) != sig:
            assert str(rel).startswith("state/projection") or str(rel).startswith("state\\projection"), \
                f"tulis di luar projection: {rel}"


def test_fx08d_mission_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(projection, "mission_get", lambda *a, **k: None)
    monkeypatch.setattr(config, "ACCESS_LOG", tmp_path / "ACCESS.jsonl")
    res = mcp_server.call_tool("mission_get", {"mission_id": "M-0999"})
    assert res.get("isError") is True
    assert res["content"][0]["text"].startswith("E_NOT_FOUND")
