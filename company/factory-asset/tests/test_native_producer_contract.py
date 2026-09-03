import copy,json
from pathlib import Path
import jsonschema,pytest
ROOT=Path(__file__).resolve().parents[3];S=json.loads((ROOT/'company/factory-asset/schemas/native-producer.schema.json').read_text());V=jsonschema.Draft202012Validator(S)
REQ={"schema":"die.factory-asset.native-producer.v1","kind":"REQUEST","job_id":"native-job-001","idempotency_key":"a"*64,"blueprint_id":"FABP-SHOPPING_BAG_PATTERN","semantic_asset_id":"FASA-SHOPPING_BAG_PATTERN","producer_class":"PROCEDURAL_VECTOR","producer_version":"1.0.0","parameters":{"seed":42,"tile":512},"cancellation":{"token":"cancel-001","poll_or_signal_supported":True}}
PASS={"schema":"die.factory-asset.native-producer.v1","kind":"RECEIPT","job_id":"native-job-001","idempotency_key":"a"*64,"producer_class":"PROCEDURAL_VECTOR","producer_version":"1.0.0","result":"PASS","master":{"format":"SVG","sha256":"b"*64,"bytes":1234,"native_editable":True,"generated_by_native_producer":True,"conversion_from_raster":False,"lineage_sha256_required":True},"deterministic_receipt_sha256":"c"*64}
def test_request_valid():V.validate(REQ)
def test_pass_receipt_valid():V.validate(PASS)
@pytest.mark.parametrize('cls,fmt',[('PROCEDURAL_VECTOR','SVG'),('MOTION_RENDERER','MP4'),('LAYERED_TEMPLATE','PSD'),('THREE_D_RENDERER','GLB')])
def test_all_native_classes_share_contract(cls,fmt):
 x=copy.deepcopy(PASS);x['producer_class']=cls;x['master']['format']=fmt;V.validate(x)
def test_flattened_or_raster_conversion_cannot_claim_native_master():
 x=copy.deepcopy(PASS);x['master']['conversion_from_raster']=True
 with pytest.raises(jsonschema.ValidationError):V.validate(x)
def test_pass_requires_native_master():
 x=copy.deepcopy(PASS);x.pop('master')
 with pytest.raises(jsonschema.ValidationError):V.validate(x)
def test_failure_has_typed_failure_and_no_master():
 x=copy.deepcopy(PASS);x['result']='FAIL';x.pop('master');x['failure']={'code':'RENDER_FAILED','retryable':True};V.validate(x)
def test_cancelled_has_typed_cancellation_failure():
 x=copy.deepcopy(PASS);x['result']='CANCELLED';x.pop('master');x['failure']={'code':'CANCELLED','retryable':False};V.validate(x)