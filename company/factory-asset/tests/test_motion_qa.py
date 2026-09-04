import importlib.util,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('mqa',R/'company/factory-asset/lib/motion_qa.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
EXPECTED={'container':'MP4','codec':'H264','pixel_format':'YUV420P','width':1080,'height':1080,'fps':30,'frame_count':180,'duration_seconds':6.0,'audio_policy':'NONE'}
def probe(**changes):
 p={'magic_mp4':True,'sha256':'a'*64,'bytes':1000,'video_stream_count':1,'audio_stream_count':0,'video':{'codec_name':'h264','pix_fmt':'yuv420p','width':1080,'height':1080,'avg_frame_rate':'30/1','nb_frames':'180','duration':'6.000000'},'format':{'duration':'6.000000'}};p.update(changes);return p
def visual(**changes):
 v={'sample_indices':[0,45,90,135,179],'sample_count':5,'samples':[],'blank_sample_count':0,'all_samples_blank':False,'distinct_perceptual_samples':5,'max_pairwise_mae':20.0,'frozen':False};v.update(changes);return v
def test_valid_motion_contract_passes():assert m.evaluate_motion(probe=probe(),visual=visual(),expected=EXPECTED)['result']=='PASS'
def test_codec_container_frame_duration_and_audio_failures_are_typed():
 p=probe(magic_mp4=False,audio_stream_count=1);p['video']=dict(p['video'],codec_name='vp9',nb_frames='179',duration='5.9');r=m.evaluate_motion(probe=p,visual=visual(),expected=EXPECTED)
 for code in ('CONTAINER_MAGIC_MISMATCH','CODEC_MISMATCH','FRAME_COUNT_MISMATCH','DURATION_MISMATCH','UNEXPECTED_AUDIO_STREAM'):assert code in r['failures']
def test_blank_render_fails_even_when_technical_metadata_matches():
 r=m.evaluate_motion(probe=probe(),visual=visual(all_samples_blank=True,blank_sample_count=5),expected=EXPECTED);assert r['result']=='FAIL' and 'BLANK_RENDER' in r['failures']
def test_frozen_render_fails_even_when_technical_metadata_matches():
 r=m.evaluate_motion(probe=probe(),visual=visual(frozen=True,distinct_perceptual_samples=1,max_pairwise_mae=0),expected=EXPECTED);assert r['result']=='FAIL' and 'FROZEN_RENDER' in r['failures']
def test_profile_compatibility_never_promotes_unknown_profile():
 adobe={'profile_state':'EVIDENCE_PINNED','delivery':{'video':['MOV','MP4/H.264']}};unknown={'profile_state':'COMPATIBILITY_UNKNOWN','delivery':{'video':['MP4']}}
 assert m.marketplace_compatibility(marketplace_profile=adobe,qa_result={'result':'PASS'},expected=EXPECTED)['state']=='COMPATIBLE'
 assert m.marketplace_compatibility(marketplace_profile=unknown,qa_result={'result':'PASS'},expected=EXPECTED)['state']=='UNKNOWN'
def test_failed_motion_qa_is_incompatible_even_for_pinned_profile():
 adobe={'profile_state':'EVIDENCE_PINNED','delivery':{'video':['MP4/H.264']}}
 assert m.marketplace_compatibility(marketplace_profile=adobe,qa_result={'result':'FAIL'},expected=EXPECTED)=={'state':'INCOMPATIBLE','reason':'MOTION_QA_FAILED'}