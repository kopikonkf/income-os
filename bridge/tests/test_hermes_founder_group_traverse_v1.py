from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
UNIT=ROOT/'company/die-agents/hermes/linux/die-hermes-gateway.service'
INSTALL=ROOT/'company/die-agents/hermes/linux/install-linux.sh'

def test_gateway_declares_founder_group_traversable_hermes_home():
    unit=UNIT.read_text(encoding='utf-8')
    assert 'Environment=HERMES_HOME_MODE=0770' in unit
    assert 'UMask=0007' in unit
    assert 'Group=die-runtime' in unit
    assert 'HERMES_SKIP_CHMOD' not in unit

def test_installer_preserves_control_privacy_but_exposes_operational_outputs():
    s=INSTALL.read_text(encoding='utf-8')
    assert 'E_HERMES_CRON_SECURE_DIR_PATCH_DRIFT' in s
    assert 'os.environ.get("HERMES_HOME_MODE", "").strip()' in s
    assert 'mode = int(mode_str, 8) if mode_str else 0o700' in s
    assert 'Cron control/state files remain owner-private 0600' in s
    assert 'E_HERMES_CRON_OUTPUT_MODE_PATCH_DRIFT' in s
    assert 'os.chmod(output_file, 0o640)' in s
    assert 'E_HERMES_TICKER_MODE_PATCH_DRIFT' in s
    assert 'os.chmod(path, 0o640)' in s
    assert 'E_HERMES_PENDING_DIR_MODE_PATCH_DRIFT' in s
    assert 'os.chmod(flush_dir, 0o2750)' in s
    assert 'founder_directory_mode=0770' in s
    assert 'cron_control_files_remain_owner_private=true' in s
    assert 'cron_output_files_founder_readable=0640' in s
    assert 'founder_private_runtime_dirs=2750' in s
