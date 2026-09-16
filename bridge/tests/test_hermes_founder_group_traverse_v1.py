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

def test_installer_patches_only_cron_directory_mode_not_file_privacy():
    s=INSTALL.read_text(encoding='utf-8')
    assert 'E_HERMES_CRON_SECURE_DIR_PATCH_DRIFT' in s
    assert 'os.environ.get("HERMES_HOME_MODE", "").strip()' in s
    assert 'mode = int(mode_str, 8) if mode_str else 0o700' in s
    assert 'cron files remain owner-private 0600' in s
    assert 'founder_directory_mode=0770' in s
    assert 'cron_files_remain_owner_private=true' in s
