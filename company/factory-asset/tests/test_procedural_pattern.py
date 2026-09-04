import importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
from PIL import Image
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('ppat',R/'company/factory-asset/lib/procedural_pattern.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load(); FIX=json.loads((R/'company/factory-asset/fixtures/procedural-pattern/fixtures.v1.json').read_text()); NS=json.loads((R/'company/factory-asset/schemas/native-producer.schema.json').read_text())
def test_seeded_pattern_is_byte_deterministic_and_native_editable(tmp_path):
 req=FIX['fixtures'][0]['request'];a=m.produce_pattern(req,output_dir=tmp_path/'a');b=m.produce_pattern(req,output_dir=tmp_path/'b');assert (tmp_path/'a/master.svg').read_bytes()==(tmp_path/'b/master.svg').read_bytes();assert (tmp_path/'a/preview.png').read_bytes()==(tmp_path/'b/preview.png').read_bytes();assert a['native_receipt']['master']['sha256']==b['native_receipt']['master']['sha256'];assert a['pattern']['editable_vector_paths'] is True;assert a['pattern']['embedded_raster'] is False;assert a['pattern']['path_count']==req['parameters']['motif_count']+1;jsonschema.Draft202012Validator(NS).validate(a['native_receipt'])
def test_preview_is_tiled_output_linked_to_master(tmp_path):
 req=FIX['fixtures'][1]['request'];r=m.produce_pattern(req,output_dir=tmp_path/'x');assert r['preview']['source_master_sha256']==r['pattern']['master_sha256'];assert r['preview']['dimensions']==[req['parameters']['tile_width']*req['parameters']['preview_repeat'],req['parameters']['tile_height']*req['parameters']['preview_repeat']];
 with Image.open(r['preview']['path']) as im: im.load(); assert im.format=='PNG'
def test_seed_change_changes_master_hash(tmp_path):
 a=json.loads(json.dumps(FIX['fixtures'][0]['request']));b=json.loads(json.dumps(a));b['parameters']['seed']+=1;b['idempotency_key']='c'*64;ra=m.produce_pattern(a,output_dir=tmp_path/'a');rb=m.produce_pattern(b,output_dir=tmp_path/'b');assert ra['pattern']['master_sha256']!=rb['pattern']['master_sha256']
def test_unknown_parameter_fails_closed(tmp_path):
 req=json.loads(json.dumps(FIX['fixtures'][0]['request']));req['parameters']['embedded_png']='x.png'
 with pytest.raises(m.PatternProducerError) as e:m.produce_pattern(req,output_dir=tmp_path/'x')
 assert e.value.code=='UNKNOWN_PATTERN_PARAMETER'
def test_wrong_producer_class_rejected(tmp_path):
 req=json.loads(json.dumps(FIX['fixtures'][0]['request']));req['producer_class']='MOTION_RENDERER'
 with pytest.raises(m.PatternProducerError) as e:m.produce_pattern(req,output_dir=tmp_path/'x')
 assert e.value.code=='WRONG_PRODUCER_CLASS'
def test_cancelled_request_emits_typed_native_receipt(tmp_path):
 req=FIX['fixtures'][0]['request'];r=m.produce_pattern(req,output_dir=tmp_path/'x',cancelled=True);assert r['native_receipt']['result']=='CANCELLED';assert r['native_receipt']['failure']['code']=='CANCELLED';assert not (tmp_path/'x/master.svg').exists();jsonschema.Draft202012Validator(NS).validate(r['native_receipt'])