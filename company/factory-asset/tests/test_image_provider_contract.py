import copy,json
from pathlib import Path
import jsonschema,pytest
ROOT=Path(__file__).resolve().parents[3];S=json.loads((ROOT/'company/factory-asset/schemas/image-provider.schema.json').read_text());V=jsonschema.Draft202012Validator(S)
CAP={"schema":"die.factory-asset.image-provider.v1","kind":"CAPABILITY","provider_id":"qwen","contract_version":"1.0.0","transport_classes":["SESSION_API","BROWSER_CDP"],"image_generation":True,"output_formats":["PNG"],"supports_transparency":"UNKNOWN","supports_requested_dimensions":"UNKNOWN","capacity_state":"UNKNOWN"}
REQ={"schema":"die.factory-asset.image-provider.v1","kind":"GENERATE_REQUEST","job_id":"factory-job-001","idempotency_key":"a"*64,"blueprint_id":"FABP-SHOPPING_BAG_PHOTO","semantic_asset_id":"FASA-SHOPPING_BAG_PHOTO","prompt":"isolated shopping bag on white background","requested_output":{"format":"PNG","width_px":2048,"height_px":2048,"alpha":"OPTIONAL"},"deadline_seconds":300}
PASS={"schema":"die.factory-asset.image-provider.v1","kind":"GENERATE_RESULT","job_id":"factory-job-001","provider_id":"qwen","transport_class":"SESSION_API","result":"PASS","operator_actions_after_dispatch":0,"artifact":{"sha256":"b"*64,"bytes":1000,"mime":"image/png","width_px":2048,"height_px":2048,"decode_reopen":True,"provider_original_bytes":True,"durable_local_save":True}}
HEALTH={"schema":"die.factory-asset.image-provider.v1","kind":"HEALTH","provider_id":"qwen","state":"READY","observed_at":"2026-09-03T19:00:00Z","operator_action_required":False,"reason_code":None}
def test_all_contract_envelopes_validate():
 for x in (CAP,REQ,PASS,HEALTH):V.validate(x)
@pytest.mark.parametrize('provider,transport',[('qwen','SESSION_API'),('chatgpt','BROWSER_CDP'),('gemini','BROWSER_CDP'),('manus','BROWSER_CDP'),('duckai','BROWSER_CDP')])
def test_current_pool_fits_same_generate_result(provider,transport):
 x=copy.deepcopy(PASS);x['provider_id']=provider;x['transport_class']=transport;V.validate(x)
def test_pass_requires_zero_operator_actions_after_dispatch():
 x=copy.deepcopy(PASS);x['operator_actions_after_dispatch']=1
 with pytest.raises(jsonschema.ValidationError):V.validate(x)
def test_pass_requires_provider_original_durable_validated_bytes():
 x=copy.deepcopy(PASS);x['artifact']['provider_original_bytes']=False
 with pytest.raises(jsonschema.ValidationError):V.validate(x)
def test_failure_is_typed_and_has_no_fake_artifact():
 x=copy.deepcopy(PASS);x['result']='FAIL';x.pop('artifact');x['failure']={'code':'CAPACITY_UNAVAILABLE','retryable':True};V.validate(x)
def test_vendor_wire_fields_are_rejected():
 for field in ('cookie','rpc_id','endpoint','session_token','raw_request_body'):
  x=copy.deepcopy(REQ);x[field]='secret-or-vendor-wire'
  with pytest.raises(jsonschema.ValidationError):V.validate(x)