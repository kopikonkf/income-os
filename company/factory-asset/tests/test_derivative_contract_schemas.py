import copy, json
from pathlib import Path
import jsonschema, pytest
ROOT=Path(__file__).resolve().parents[3]
RS=json.loads((ROOT/'company/factory-asset/schemas/derivative-recipe.schema.json').read_text())
OS=json.loads((ROOT/'company/factory-asset/schemas/derivative-receipt.schema.json').read_text())
RECIPE={"schema":"die.factory-asset.derivative-recipe.v1","recipe_id":"raster-jpeg-stock-v1","recipe_version":"1.0.0","input":{"master_sha256":"a"*64,"semantic_asset_id":"FASA-SHOPPING_BAG_PHOTO","format":"PNG"},"output":{"format":"JPEG","purpose":"MARKETPLACE_DELIVERY","width_px":4096,"height_px":4096,"color_space":"SRGB","alpha_policy":"FLATTEN_WHITE","quality":92,"semantic_identity_effect":"NONE"},"marketplace_profile":{"platform_id":"ADOBE_STOCK","profile_revision":"1.0"},"idempotency":{"key_material":["master_sha256","recipe_id","recipe_version","marketplace_profile.platform_id","marketplace_profile.profile_revision","output"],"output_collision_action":"VERIFY_HASH_AND_REUSE_OR_FAIL"},"qa":{"magic_mime_match":True,"decode_reopen":True,"sha256":True,"dimensions_if_raster":True},"compatibility":{"unknown_action":"BLOCK_PACKAGE","require_profile_match":True}}
RECEIPT={"schema":"die.factory-asset.derivative-receipt.v1","recipe_id":"raster-jpeg-stock-v1","recipe_version":"1.0.0","idempotency_key":"b"*64,"input":{"master_sha256":"a"*64,"semantic_asset_id":"FASA-SHOPPING_BAG_PHOTO"},"marketplace_profile":{"platform_id":"ADOBE_STOCK","profile_revision":"1.0"},"output":{"format":"JPEG","sha256":"c"*64,"bytes":1234,"width_px":4096,"height_px":4096,"semantic_identity_effect":"NONE"},"qa":{"magic_mime_match":True,"decode_reopen":True,"sha256_verified":True,"failure_code":None},"compatibility":{"state":"COMPATIBLE","reason":None},"result":"PASS"}
def test_recipe_positive(): jsonschema.Draft202012Validator(RS).validate(RECIPE)
def test_receipt_positive(): jsonschema.Draft202012Validator(OS).validate(RECEIPT)
def test_derivative_never_mints_semantic_identity():
 x=copy.deepcopy(RECIPE);x['output']['semantic_identity_effect']='NEW_ASSET'
 with pytest.raises(jsonschema.ValidationError):jsonschema.Draft202012Validator(RS).validate(x)
def test_pass_receipt_requires_all_qa_green():
 x=copy.deepcopy(RECEIPT);x['qa']['decode_reopen']=False
 with pytest.raises(jsonschema.ValidationError):jsonschema.Draft202012Validator(OS).validate(x)
def test_pass_receipt_cannot_claim_unknown_compatibility():
 x=copy.deepcopy(RECEIPT);x['compatibility']['state']='COMPATIBILITY_UNKNOWN'
 with pytest.raises(jsonschema.ValidationError):jsonschema.Draft202012Validator(OS).validate(x)