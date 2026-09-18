import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CONTRACT=ROOT/'company/factory-asset/contracts/fa340-founder-filesystem-operability.v1.json'
TOOL=ROOT/'company/factory-asset/bin/fa340_founder_filesystem_operability.py'
RUNTIME_NORMALIZER=ROOT/'company/die-agents/hermes/linux/founder-fs-runtime-normalize.sh'
HERMES_INSTALL=ROOT/'company/die-agents/hermes/linux/install-linux.sh'
HERMES_UNIT=ROOT/'company/die-agents/hermes/linux/die-hermes-gateway.service'
STATE=ROOT/'company/factory-asset/lib/postproduction_state.py'
ORCH=ROOT/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'

def test_contract_preserves_service_ownership_and_private_files():
    c=json.loads(CONTRACT.read_text(encoding='utf-8'))
    assert c['task_id']=='FA-340'
    assert c['founder']=={'user':'kopiko','required_group':'die-runtime','sudo_expected':True}
    assert c['governed_roots']==['/var/lib/die','/srv/die','/opt/die']
    assert c['service_private_file_mode']=='0600'
    assert c['operational_file_mode']=='0640'
    assert any('MUST NOT recursively chown' in x for x in c['invariants'])
    private='\n'.join(c['intentionally_private_examples'])
    for token in ['.env','cron/jobs.json','cache','tirith','Cookies','Login Data']:
        assert token in private

def test_apply_tool_is_allowlisted_and_refuses_active_runtime():
    s=TOOL.read_text(encoding='utf-8')
    assert "choices=['audit','apply']" in s
    assert "E_ACTIVE_CONFLICT" in s
    assert "E_KOPIKO_NOT_DIE_RUNTIME" in s
    assert "/var/lib/die/rollback/FA-340" in s
    assert "os.chown(p,-1,runtime.gr_gid)" in s
    assert "os.chown(p,kopiko" not in s
    assert "os.chown(root" not in s
    assert "chmod -R" not in s and "chown -R" not in s
    assert "def _founder_run" in s
    assert "['runuser','-u','kopiko','--',*argv]" in s
    assert "operational_unreadable" in s
    for token in ['postproduction-state.json','*.metadata.*','cron/output','ticker_heartbeat','factory-asset-canaries','rollback.sh']:
        assert token in s

def test_private_runtime_dirs_are_group_traversable_not_group_writable():
    s=RUNTIME_NORMALIZER.read_text(encoding='utf-8')
    assert '/pending_messages' in s and '/tirith/sessions' in s
    assert 'chmod 2750' in s
    assert 'die-hermes' in s and 'die-runtime' in s
    assert 'chmod -R' not in s
    unit=HERMES_UNIT.read_text(encoding='utf-8')
    assert 'ExecStartPost=/usr/local/bin/die-founder-fs-runtime-normalize' in unit
    assert 'ExecStopPost=/usr/local/bin/die-founder-fs-runtime-normalize' in unit

def test_hermes_installer_persists_output_readability_without_opening_control_files():
    s=HERMES_INSTALL.read_text(encoding='utf-8')
    assert 'install -m 0755 "$DIE_HOME/company/die-agents/hermes/linux/founder-fs-runtime-normalize.sh"' in s
    assert 'os.chmod(output_file, 0o640)' in s
    assert 'os.chmod(path, 0o640)' in s
    assert 'os.chmod(flush_dir, 0o2750)' in s
    assert 'cron_control_files_remain_owner_private=true' in s
    assert 'cron_output_files_founder_readable=0640' in s
    assert 'chmod 0600 "$ENV_FILE"' in s

def test_postproduction_state_and_derivatives_are_founder_readable():
    state=STATE.read_text(encoding='utf-8')
    orch=ORCH.read_text(encoding='utf-8')
    assert 'os.chmod(tmp,0o640)' in state
    assert "make_founder_readable(out)" in orch
    assert "make_founder_readable(target)" in orch
    assert "path.chmod(0o640)" in orch

def test_graph_frontier_is_fa340_until_live_acceptance_seal():
    g=json.loads(GRAPH.read_text(encoding='utf-8')); by={t['id']:t for t in g['tasks']}
    assert by['FA-339']['status']=='DONE'
    assert by['FA-340']['depends_on']==['FA-339']
    assert by['FA-340']['status']=='READY'


def test_postproduction_state_runtime_writes_0640(tmp_path):
    import importlib.util, stat, sys
    spec=importlib.util.spec_from_file_location('fa340_state',STATE); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    p=tmp_path/'postproduction-state.json'
    mod.create_state(p,job_id='J1',semantic_asset_id='S1',blueprint_id='B1',source_master_sha256='a'*64)
    assert stat.S_IMODE(p.stat().st_mode)==0o640
