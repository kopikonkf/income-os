from pathlib import Path
import json
import subprocess

R = Path(__file__).resolve().parents[3]
CONTRACT = R / 'company/factory-asset/contracts/cluster-provisioning.v1.json'
PROVISIONER = R / 'company/browser/linux/cluster_profile_provisioning.mjs'
AUTH = R / 'company/muxia/scripts/linux/muxia-cluster-auth-handoff.mjs'
RUNNER = R / 'company/factory-asset/bin/run_fa305_cluster_b_provisioning.mjs'
ACTIVE = R / 'company/factory-asset/registries/web-ai-clusters.v1.json'


def test_cluster_b_contract_is_pre_auth_and_not_active_registry_member():
    c = json.loads(CONTRACT.read_text())
    b = c['cluster_b']
    assert c['schema'] == 'die.factory-asset.cluster-provisioning-contract.v1'
    assert b['cluster_id'] == 'cluster-b'
    assert b['profile_id'] == 'web-ai-cluster-b'
    assert b['max_tabs'] == 8
    assert b['browser_owner_model'] == 'SINGLE_LONG_LIVED_CHROMIUM_PROCESS'
    assert b['profile_secret_copy_allowed'] is False
    assert b['source_profile_clone_allowed'] is False
    assert b['source_profile_import_allowed'] is False
    assert b['initial_activation_state'] == 'WAITING_FOUNDER_AUTH'
    assert c['acceptance_boundary']['founder_auth_required_for_full_fa305_pass'] is True
    active = json.loads(ACTIVE.read_text())
    ids = {x['cluster_id'] for x in active['clusters']}
    assert 'cluster-a' in ids
    if 'cluster-b' in ids:
        live = next(x for x in active['clusters'] if x['cluster_id']=='cluster-b')
        assert live['profile_id']=='web-ai-cluster-b'
        assert live['profile_dir']=='/var/lib/muxia/profiles/web-ai-cluster-b/browser'
        assert live['lifecycle_state'] in {'ACTIVE','ACTIVE_ATTACH_ONLY'}


def test_provisioner_has_no_profile_clone_or_cluster_a_secret_read_surface():
    s = PROVISIONER.read_text().lower()
    for token in ('copyfilesync', 'cpsync', 'createReadStream'.lower(), '/var/lib/muxia/profiles/chatgpt-linux-a'):
        assert token.lower() not in s
    assert 'source_profile_supplied: false' in s
    assert 'source_profile_read: false' in s
    assert 'inherited_session_material: false' in s
    assert 'e_rollback_auth_material_may_exist' in s
    assert 'e_cluster_path_symlink' in s
    assert 'e_profile_owner_uid' in s


def test_visible_auth_handoff_contract_has_no_cdp_or_provider_automation():
    s = AUTH.read_text().lower()
    for token in ('--remote-debugging-port', '--remote-debugging-address', 'connectovercdp', 'playwright', 'chatgpt.com', 'qwen.ai', 'gemini.google.com', 'manus.im', 'duck.ai', 'grok.com'):
        assert token not in s
    assert 'display_required' in s
    assert 'broker_must_be_stopped' in s
    assert "'about:blank'" in s
    assert 'provider_login_automated: false' in s


def test_real_temporary_cluster_b_acceptance_reaches_only_founder_auth_boundary():
    r = subprocess.run(['node', str(RUNNER)], capture_output=True, text=True, check=True, timeout=90)
    v = json.loads(r.stdout)
    assert v['implementation_result'] == 'PASS'
    assert v['task_state'] == 'WAITING_FOUNDER_AUTH'
    assert v['full_fa305_acceptance'] is False
    assert v['founder_auth_performed'] is False
    assert v['provider_calls_performed'] == 0
    assert v['cluster_a_profile_accessed'] is False
    assert v['canonical_cluster_b_profile_created'] is False
    assert all(v['assertions'].values())
    proof = v['evidence']['temporary_real_broker_proof']
    assert proof['fresh_profile_initial_entries'] == 0
    assert proof['browser_owner_pid_present'] is True
    assert proof['second_owner_blocked'] is True
    assert proof['second_owner_browser_launch_calls'] == 0
    assert proof['primary_owner_lock_preserved_after_second_rejection'] is True
    assert proof['primary_owner_lock_preserved_after_non_owner_stop'] is True
    assert proof['max_tabs'] == 8
    assert proof['final_pre_auth_state'] == 'WAITING_FOUNDER_AUTH'
    assert proof['rollback']['cluster_root_removed'] is True

def test_visible_auth_handoff_can_resume_on_new_display_without_reopening_state(tmp_path):
    root = tmp_path / "cluster-b"
    profile = root / "browser"
    state_dir = root / "state"
    lock_dir = root / "locks"
    for d, mode in ((root,0o750),(profile,0o700),(state_dir,0o750),(lock_dir,0o750)):
        d.mkdir(exist_ok=True)
        d.chmod(mode)
    state_file = state_dir / "provisioning.json"
    state_file.write_text(json.dumps({
        "schema":"die.factory-asset.cluster-provisioning-state.v1",
        "cluster_id":"cluster-b",
        "profile_id":"web-ai-cluster-b",
        "state":"AUTH_HANDOFF_VISIBLE_NO_CDP",
        "cluster_root":str(root),
        "profile_dir":str(profile),
        "auth_handoff_started":True,
        "credential_values_read":False,
        "cookies_or_tokens_read":False
    }))
    fake = tmp_path / "fake-browser.sh"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    env = dict(__import__("os").environ)
    env["DISPLAY"] = ":99"
    r = subprocess.run([
        "node", str(AUTH), "--state-file", str(state_file),
        "--browser", str(fake), "--resume-visible", "yes"
    ], capture_output=True, text=True, check=True, timeout=20, env=env)
    out = json.loads(r.stdout)
    final = json.loads(state_file.read_text())
    assert out["status"] == "CLOSED"
    assert out["resumed_visible_handoff"] is True
    assert final["state"] == "AUTH_HANDOFF_CLOSED"
    assert final["browser_fully_closed"] is True
    assert final["provider_login_automated"] is False
    assert final["credential_values_read"] is False
    assert final["cookies_or_tokens_read"] is False


def test_visible_auth_handoff_resume_requires_existing_visible_state(tmp_path):
    root = tmp_path / "cluster-b"
    profile = root / "browser"
    state_dir = root / "state"
    lock_dir = root / "locks"
    for d, mode in ((root,0o750),(profile,0o700),(state_dir,0o750),(lock_dir,0o750)):
        d.mkdir(exist_ok=True)
        d.chmod(mode)
    state_file = state_dir / "provisioning.json"
    state_file.write_text(json.dumps({
        "schema":"die.factory-asset.cluster-provisioning-state.v1",
        "cluster_id":"cluster-b",
        "profile_id":"web-ai-cluster-b",
        "state":"WAITING_FOUNDER_AUTH",
        "cluster_root":str(root),
        "profile_dir":str(profile),
        "auth_handoff_started":False,
        "credential_values_read":False,
        "cookies_or_tokens_read":False
    }))
    fake = tmp_path / "fake-browser.sh"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    env = dict(__import__("os").environ)
    env["DISPLAY"] = ":99"
    r = subprocess.run([
        "node", str(AUTH), "--state-file", str(state_file),
        "--browser", str(fake), "--resume-visible", "yes"
    ], capture_output=True, text=True, timeout=20, env=env)
    assert r.returncode != 0
    assert "E_AUTH_HANDOFF_RESUME_STATE:WAITING_FOUNDER_AUTH" in (r.stderr + r.stdout)
    assert json.loads(state_file.read_text())["state"] == "WAITING_FOUNDER_AUTH"
