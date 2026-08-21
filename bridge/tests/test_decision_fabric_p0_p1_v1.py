import json
import pathlib

from income_os_bridge import config, envelope, mcp_server, projection


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_decision_fabric_authority_matches_company_registry():
    registry = json.loads(
        (ROOT / "company" / "identity-registry.json").read_text(encoding="utf-8-sig")
    )
    governance = registry["governance"]
    assert config.HERMES_PROFILE == "income-operator"
    assert config.OPERATIONAL_CONTROL_PLANE == (
        f'{governance["operational_control_plane"]}/{config.HERMES_PROFILE}'
    )
    assert config.CANONICAL_WRITER == governance["canonical_state_writer"]


def test_semantic_envelope_declares_operational_authority():
    result = envelope.build(
        "system_state",
        {"status": "ok"},
        ["config:DIE"],
        source_trust="VERIFIED",
    )
    assert result["operational_control_plane"] == "hermes-operator/income-operator"
    assert result["canonical_writer"] == "die-state-manager"


def test_truncated_envelope_preserves_operational_authority():
    result = envelope.build(
        "recent_events",
        {"events": ["x" * 500 for _ in range(4000)]},
        ["fixture"],
    )
    assert result["completeness"] == "truncated"
    assert result["operational_control_plane"] == "hermes-operator/income-operator"
    assert result["canonical_writer"] == "die-state-manager"
    assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= config.MAX_RESP_BYTES


def test_p0_surface_exposes_authority_through_stdio_dispatch(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ACCESS_LOG", tmp_path / "ACCESS.jsonl")
    result = mcp_server.call_tool("system_state", {})
    payload = json.loads(result["content"][0]["text"])
    assert payload["operational_control_plane"] == "hermes-operator/income-operator"
    assert payload["canonical_writer"] == "die-state-manager"


def test_server_instructions_keep_p2_optional():
    assert "Canonical DIE Decision Fabric P0/P1" in mcp_server.SERVER_INSTRUCTIONS
    assert config.OPERATIONAL_CONTROL_PLANE in mcp_server.SERVER_INSTRUCTIONS
    assert config.CANONICAL_WRITER in mcp_server.SERVER_INSTRUCTIONS
    assert "P2 network transport remains optional" in mcp_server.SERVER_INSTRUCTIONS


def test_income_operator_reader_path_is_profile_bound():
    expected = (
        pathlib.Path(r"C:\Users\aethers\AppData\Local\hermes")
        / "profiles"
        / "income-operator"
        / "state.db"
    )
    assert config.STATE_DB_PROFILE == expected


def test_briefing_surface_declares_operational_authority(monkeypatch, tmp_path):
    briefing = tmp_path / "BRIEFING.md"
    briefing.write_text("# BRIEFING fixture", encoding="utf-8")
    monkeypatch.setattr(config, "BRIEFING", briefing)
    result = projection.briefing_get()
    assert result["operational_control_plane"] == "hermes-operator/income-operator"
    assert result["canonical_writer"] == "die-state-manager"
    assert result["markdown"] == "# BRIEFING fixture"
