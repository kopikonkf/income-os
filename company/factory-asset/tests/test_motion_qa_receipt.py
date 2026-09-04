import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
RECEIPT=R/'company/factory-asset/receipts/FA-042-motion-codec-container-frame-qa.receipt.json'
def test_fa042_actual_receipt_positive_and_negative_controls_are_sealed():
 r=json.loads(RECEIPT.read_text());assert r['result']=='PASS';assert r['positive']['result']=='PASS';t=r['positive']['technical'];assert (t['codec'],t['pixel_format'],t['width'],t['height'],t['fps'],t['frame_count'],t['duration_seconds'],t['audio_stream_count'])==('h264','yuv420p',1080,1080,30.0,180,6.0,0);v=r['positive']['visual'];assert v['sample_count']==5 and v['blank_sample_count']==0 and v['frozen'] is False and v['distinct_perceptual_samples']>=2
 neg=r['negative_controls'];assert 'PROBE_FAILED' in neg['mislabeled.mp4']['failures'];assert 'FRAME_SAMPLE_DECODE_FAILED' in neg['truncated.mp4']['failures'];assert 'BLANK_RENDER' in neg['blank.mp4']['failures'];assert 'FROZEN_RENDER' in neg['frozen.mp4']['failures']
def test_fa042_marketplace_states_are_profile_evidence_bounded():
 r=json.loads(RECEIPT.read_text());c=r['marketplace_compatibility'];assert c['ADOBE_STOCK']['state']=='COMPATIBLE';assert c['DREAMSTIME']['state']=='UNKNOWN';assert c['VECTEEZY']['state']=='UNKNOWN';assert c['MOTIONELEMENTS']['state']=='UNKNOWN';assert r['acceptance']['unknown_profiles_not_promoted'] is True and r['acceptance']['false_success_count']==0
def test_fa042_has_zero_live_authority():
 r=json.loads(RECEIPT.read_text());assert r['authority']=={'provider_generation':False,'marketplace_upload':False,'publication':False,'credential_access':False,'spend_usd':0}