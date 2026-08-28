import json
from pathlib import Path

import pytest

from income_os_bridge import config


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "company" / "contracts" / "die.path-roots.v1.json"


def test_die102_windows_defaults_preserve_live_layout():
    roots = config.resolve_die_path_roots({}, platform_name="windows")
    assert roots.die_home == r"C:\DIE"
    assert roots.die_state_root == r"C:\DIE"
    assert roots.muxia_root == r"C:\DIE\muxia"
    assert roots.die_config_root == r"C:\ProgramData\DIE"
    assert roots.die_install_root == r"C:\Program Files\DIE"


def test_die102_linux_defaults_separate_source_state_config_install():
    roots = config.resolve_die_path_roots({}, platform_name="linux")
    assert roots.die_home == "/srv/die"
    assert roots.die_state_root == "/var/lib/die"
    assert roots.muxia_root == "/var/lib/muxia"
    assert roots.die_config_root == "/etc/die"
    assert roots.die_install_root == "/opt/die"


def test_die102_explicit_roots_override_defaults_without_cross_coupling():
    roots = config.resolve_die_path_roots(
        {
            "DIE_HOME": "/x/source",
            "DIE_STATE_ROOT": "/x/state",
            "MUXIA_ROOT": "/x/muxia",
            "DIE_CONFIG_ROOT": "/x/config",
            "DIE_INSTALL_ROOT": "/x/install",
        },
        platform_name="linux",
    )
    assert roots.die_home == "/x/source"
    assert roots.die_state_root == "/x/state"
    assert roots.muxia_root == "/x/muxia"
    assert roots.die_config_root == "/x/config"
    assert roots.die_install_root == "/x/install"


@pytest.mark.parametrize(
    "key",
    ["DIE_HOME", "DIE_STATE_ROOT", "MUXIA_ROOT", "DIE_CONFIG_ROOT", "DIE_INSTALL_ROOT"],
)
def test_die102_relative_configured_roots_fail_closed(key):
    with pytest.raises(ValueError, match=f"{key} must be an absolute path"):
        config.resolve_die_path_roots({key: "relative/path"}, platform_name="linux")


def test_die102_contract_matches_linux_defaults_and_derived_boundaries():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    env = payload["environment"]
    assert env["DIE_HOME"]["linux_default"] == "/srv/die"
    assert env["DIE_STATE_ROOT"]["linux_default"] == "/var/lib/die"
    assert env["MUXIA_ROOT"]["linux_default"] == "/var/lib/muxia"
    assert env["DIE_CONFIG_ROOT"]["linux_default"] == "/etc/die"
    assert env["DIE_INSTALL_ROOT"]["linux_default"] == "/opt/die"
    assert payload["derived"]["STATE"] == "<DIE_STATE_ROOT>/state"
    assert payload["derived"]["WORKSPACES"] == "<DIE_STATE_ROOT>/workspaces"


def test_die102_runtime_entrypoints_do_not_pin_c_die_as_operational_root():
    paths = [
        ROOT / "bridge" / "income_os_bridge" / "runtime_mcp_server.py",
        ROOT / "bin" / "die_event.py",
        ROOT / "bin" / "die_cron.py",
        ROOT / "bin" / "die_audit.py",
        ROOT / "bin" / "die_briefing.py",
        ROOT / "bin" / "die_heartbeat.py",
        ROOT / "bin" / "die_summary.py",
        ROOT / "bin" / "m001_loop.py",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert 'pathlib.Path(r"C:\\DIE")' not in text, path
        assert 'sys.path.insert(0, r"C:\\DIE\\bin")' not in text, path


def test_die102_runtime_derived_paths_bind_to_state_root():
    assert config.STATE == config.DIE_STATE_ROOT / "state"
    assert config.WORKSPACES == config.DIE_STATE_ROOT / "workspaces"
    assert config.IDENTITY_REGISTRY == config.DIE_HOME / "company" / "identity-registry.json"
