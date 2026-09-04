import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('obs',R/'company/factory-asset/lib/observability.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_metrics_categories_remain_separate():
 l=m.MetricsLedger();l.record({'kind':'ATTEMPT','job_id':'j1'});l.record({'kind':'MASTER','artifact_sha256':'a'*64});l.record({'kind':'MASTER','artifact_sha256':'a'*64});l.record({'kind':'QA_ASSET','quantity':2});l.record({'kind':'DERIVATIVE','quantity':3});l.record({'kind':'PACKAGE','quantity':1});l.record({'kind':'FAILURE','failure_code':'RATE_LIMITED'});l.record({'kind':'RESOURCE','cpu_seconds':2.5,'memory_mb_seconds':100});l.record({'kind':'ECONOMICS','unit_cost_micros':12});s=l.snapshot();assert (s['attempts'],s['unique_masters'],s['qa_assets'],s['derivatives'],s['packages'],s['failures'])==(1,1,2,3,1,1);assert s['resources']['cpu_seconds']==2.5;assert s['economics']['unit_cost_micros']==12
@pytest.mark.parametrize('field',['password','cookie','session_token','access_token','raw_auth_body','api_key','client_secret','browser_profile','cdp_url'])
def test_secret_fields_rejected_recursively(field):
 with pytest.raises(m.ObservabilityError) as e:m.sanitize_event({'kind':'ATTEMPT','job_id':'j', 'state':{'nested':{field:'x'}}})
 assert e.value.code=='SECRET_FIELD_FORBIDDEN'
def test_unknown_fields_rejected_not_silently_logged():
 with pytest.raises(m.ObservabilityError) as e:m.sanitize_event({'kind':'ATTEMPT','job_id':'j','raw_payload':'x'})
 assert e.value.code=='UNKNOWN_OBSERVABILITY_FIELD'
def test_master_requires_valid_hash():
 l=m.MetricsLedger()
 with pytest.raises(m.ObservabilityError):l.record({'kind':'MASTER','artifact_sha256':'bad'})