import importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
R=Path(__file__).resolve().parents[3];S=json.loads((R/'company/factory-asset/schemas/factory-console-api.schema.json').read_text());V=jsonschema.Draft202012Validator(S)
s=importlib.util.spec_from_file_location('cc',R/'company/factory-asset/lib/console_contract.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_job_intent_and_control_are_vendor_neutral():
 intent=m.job_intent(job_id='console-job-001',idempotency_key='a'*64,blueprint_id='FABP-SHOPPING_BAG_PHOTO',semantic_asset_id='FASA-SHOPPING_BAG_PHOTO-001',label='job');V.validate(intent)
 cmd={'schema':'die.factory-asset.console-api.v1','kind':'CONTROL_COMMAND','command_id':'command-001','job_id':'console-job-001','action':'START'};V.validate(cmd)
def test_queue_event_maps_core_state_only():
 e=m.queue_event({'job_id':'console-job-001','state':'RETRY_WAIT','attempts':1,'retries':1,'recovery_count':0,'failure_code':'RATE_LIMITED','artifact_sha256':None,'intent':{'provider_id':'qwen','blueprint_id':'FABP-X','semantic_asset_id':'FASA-X','label':'x'}});V.validate(e);assert e['retries']==1
def test_provider_and_output_events_validate():
 V.validate(m.provider_event(provider_id='qwen',profile_id='qwen_a',eligibility='ELIGIBLE',capacity='AVAILABLE',policy='ALLOWED_EVIDENCED',routing_reason='deterministic winner'))
 V.validate({'schema':'die.factory-asset.console-api.v1','kind':'OUTPUT_EVENT','semantic_asset_id':'FASA-X','master_sha256':'b'*64,'master_format':'PNG','derivative_count':2,'qa_state':'PASS','compatibility_state':'COMPATIBLE'})
@pytest.mark.parametrize('field',['cookie','session_token','rpc_id','endpoint','browser_profile','cdp_url','raw_auth_body'])
def test_vendor_wire_and_browser_fields_rejected(field):
 x=m.job_intent(job_id='console-job-001',idempotency_key='a'*64,blueprint_id='FABP-SHOPPING_BAG_PHOTO',semantic_asset_id='FASA-SHOPPING_BAG_PHOTO-001',label='job');x[field]='forbidden'
 with pytest.raises(jsonschema.ValidationError):V.validate(x)
def test_retry_count_above_core_limit_rejected():
 x={'schema':'die.factory-asset.console-api.v1','kind':'QUEUE_EVENT','job_id':'j','state':'RETRY_WAIT','attempts':4,'retries':3,'recovery_count':0,'failure_code':'RATE_LIMITED','artifact_sha256':None,'blueprint_id':'FABP-X','semantic_asset_id':'FASA-X','label':'x'}
 with pytest.raises(jsonschema.ValidationError):V.validate(x)