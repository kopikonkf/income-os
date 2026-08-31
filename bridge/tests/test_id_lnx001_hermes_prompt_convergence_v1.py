from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT = ROOT / "company" / "die-agents" / "hermes" / "linux" / "die-hermes-gateway.service"
INSTALL = ROOT / "company" / "die-agents" / "hermes" / "linux" / "install-linux.sh"
HERMES_AGENTS = ROOT / "company" / "die-agents" / "hermes" / "AGENTS.md"
ROOT_AGENTS = ROOT / "AGENTS.md"
SOUL = ROOT / "company" / "die-agents" / "hermes" / "SOUL.md"


def test_hermes_gateway_pins_context_discovery_to_canonical_component_path() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert "WorkingDirectory=/srv/die" in text
    assert "Environment=TERMINAL_CWD=/srv/die/company/die-agents/hermes" in text
    assert "EnvironmentFile=/etc/die/hermes/hermes.env" in text


def test_installer_hash_pins_root_component_agents_and_soul_without_second_canon() -> None:
    text = INSTALL.read_text(encoding="utf-8")
    assert 'sha256sum "$DIE_HOME/AGENTS.md"' in text
    assert 'sha256sum "$DIE_HOME/company/die-agents/hermes/AGENTS.md"' in text
    assert 'sha256sum "$DIE_HOME/company/die-agents/hermes/SOUL.md"' in text
    assert "root_agents_sha256=$root_agents_sha256" in text
    assert "hermes_agents_sha256=$hermes_agents_sha256" in text
    assert "hermes_soul_sha256=$hermes_soul_sha256" in text
    assert "terminal_cwd=$DIE_HOME/company/die-agents/hermes" in text
    assert ROOT_AGENTS.is_file() and HERMES_AGENTS.is_file() and SOUL.is_file()


def test_component_agents_explicitly_remains_delta_to_repository_root() -> None:
    text = HERMES_AGENTS.read_text(encoding="utf-8")
    assert "materializes the canonical Hermes path" in text
    assert "repository-root `AGENTS.md`" in text
    assert "Sections not restated here retain that document's" in text
