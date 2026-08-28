import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "docs" / "CHATGPT_ROLES_TRANSPORT_MAP.md"
REGISTRY_PATH = ROOT / "company" / "identity-registry.json"
HERMES_AGENTS_PATH = ROOT / "company" / "die-agents" / "hermes" / "AGENTS.md"


def test_map_mentions_all_registry_identities():
    role_map = MAP_PATH.read_text(encoding="utf-8")
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    missing = [entry["id"] for entry in registry["identities"] if entry["id"] not in role_map]
    assert missing == []


def test_proxima_is_never_a_cognitive_lane():
    role_map = MAP_PATH.read_text(encoding="utf-8")
    assert "Proxima :3211 is a production gateway. It is NEVER a cognitive lane." in role_map


def test_reserved_infrastructure_ports_are_fail_closed():
    role_map = MAP_PATH.read_text(encoding="utf-8")
    reserved_line = next(
        line for line in role_map.splitlines() if line.startswith("- Reserved/infrastructure ports:")
    )

    assert all(port in reserved_line for port in ("8787", "8789", "8790"))
    assert "fail-closed" in reserved_line


def test_hermes_stable_facts_are_decided_and_current():
    agents = HERMES_AGENTS_PATH.read_text(encoding="utf-8")

    assert "heartbeat threshold = D-0007" in agents
    assert "verified-revenue definition = D-0009" in agents
    assert "autonomy budget = D-0010" in agents
    assert "M-001 = RATIFIED & COMMITTED (D-0020/21/22)" in agents
    assert "never answer from session memory" in agents
