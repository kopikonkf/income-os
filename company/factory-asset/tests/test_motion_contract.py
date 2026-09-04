import importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('mc',R/'company/factory-asset/lib/motion_contract.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();PLAN=json.loads((R/'company/factory-asset/fixtures/motion-composition/fixture-plan.v1.json').read_text());MS=json.loads((R/'company/factory-asset/schemas/motion-composition.schema.json').read_text());NS=json.loads((R/'company/factory-asset/schemas/native-producer.schema.json').read_text())
def comp(i=0):return json.loads(json.dumps(PLAN['fixtures'][i]['composition']))
@pytest.mark.parametrize('i',[0,1])
def test_valid_fixture_pins_motion_contract_and_renderer_boundary(i):
 c=comp(i);jsonschema.Draft202012Validator(MS).validate(c);v=m.validate_motion_composition(c);assert v['result']=='PASS';assert v['frame_count']==c['frame_count'];assert v['dimensions']==[c['canvas']['width'],c['canvas']['height']];assert v['renderer']==c['renderer'];assert v['video']==c['video'];assert v['audio_policy']==c['audio']['policy'];assert v['semantic_mode']=='ANIMATION';assert v['native_representation']=='TIMED_FRAMES';assert v['conversion_from_raster'] is False
 r=m.build_renderer_request(c,job_id=f'FA040-MOTION-{i:03d}',cancellation_token=f'fa040-cancel-{i:03d}');jsonschema.Draft202012Validator(NS).validate(r);assert r['producer_class']=='MOTION_RENDERER';assert r['parameters']['composition_sha256']==v['composition_sha256'];assert r['parameters']['expected_frame_count']==c['frame_count'];assert r['parameters']['conversion_from_raster'] is False
def test_renderer_request_is_deterministic():
 c=comp();a=m.build_renderer_request(c,job_id='FA040-MOTION-DET',cancellation_token='fa040-cancel-det');b=m.build_renderer_request(c,job_id='FA040-MOTION-DET',cancellation_token='fa040-cancel-det');assert a==b;assert a['idempotency_key']==b['idempotency_key']
def test_frame_count_mismatch_fails_closed():
 c=comp();c['frame_count']=179
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='FRAME_COUNT_MISMATCH'
def test_png_conversion_masquerade_is_schema_rejected():
 c=comp();c['conversion_from_raster']=True
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='MOTION_SCHEMA_INVALID'
def test_static_timeline_is_not_animation():
 c=comp();c['layers'][0]['keyframes']=[{'frame':0,'property':'Y','value':500}]
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='NO_TEMPORAL_CHANGE'
def test_unsupported_codec_container_combination_rejected():
 c=comp();c['video']={'container':'MP4','codec':'PRORES_422','pixel_format':'YUV422P10LE'}
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='VIDEO_TARGET_UNSUPPORTED'
def test_keyframe_must_stay_in_layer_range():
 c=comp();c['layers'][0]['keyframes'][0]['frame']=179;c['layers'][0]['end_frame']=100
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='KEYFRAME_OUT_OF_LAYER_RANGE'
def test_duplicate_layer_id_rejected():
 c=comp();c['layers'].append(json.loads(json.dumps(c['layers'][0])))
 with pytest.raises(m.MotionContractError) as e:m.validate_motion_composition(c)
 assert e.value.code=='DUPLICATE_LAYER_ID'