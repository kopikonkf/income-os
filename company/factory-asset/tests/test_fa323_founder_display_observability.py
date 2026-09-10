import importlib.util,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('obs',ROOT/'company/factory-asset/lib/founder_display_observability.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m)

def test_contract_matches_actual_production_displays_and_loopback_control_ports():
    c=m.validate_contract(); by={x['cluster_id']:x for x in c['clusters']}
    assert by['cluster-a']['production_display']==101 and by['cluster-b']['production_display']==102
    assert by['cluster-a']['display_socket']==':101' and by['cluster-b']['display_socket']==':102'
    for row in by.values():
        assert row['cdp']['host']=='127.0.0.1' and row['broker']['host']=='127.0.0.1'
        assert row['cdp']['founder_direct_exposure'] is False and row['broker']['founder_direct_exposure'] is False
        assert row['vnc_plan']['state']=='NOT_DEPLOYED' and row['vnc_plan']['bind_host']=='127.0.0.1'
        assert row['vnc_plan']['mode']=='READ_ONLY' and row['vnc_plan']['transport']=='SSH_LOCAL_FORWARD'

def test_fa323_does_not_deploy_vnc_or_grant_interactive_repair():
    c=m.validate_contract(); sec=c['security']
    assert c['implementation_state']=='DEFINED_NOT_DEPLOYED'
    assert sec['default_access']=='READ_ONLY' and sec['interactive_repair']=='FORBIDDEN_UNTIL_FA-325'
    assert sec['public_listener_allowed'] is False and sec['credential_extraction_allowed'] is False and sec['cookie_token_export_allowed'] is False

def test_sanitizer_allows_operational_status_but_rejects_secret_bearing_input():
    out=m.sanitize_status({'owner_state':'READY','active_tab_lease_count':2,'active_job_id':'JOB-1','noise':'drop'},cluster_id='cluster-a')
    assert out=={'active_job_id':'JOB-1','active_tab_lease_count':2,'cluster_id':'cluster-a','owner_state':'READY'}
    with pytest.raises(m.FounderObservabilityError,match='FORBIDDEN_STATUS_FIELD'):
        m.sanitize_status({'owner_state':'READY','token_values':['secret']},cluster_id='cluster-a')
