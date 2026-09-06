from pathlib import Path
import importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
F=ROOT/'company/factory-asset/fixtures/governed-canary'


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,LIB/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;assert spec and spec.loader;spec.loader.exec_module(m);return m

vr=load('visual_rights_detector_test','visual_rights_detector.py')


def test_ocr_consensus_rejects_texture_fragments_and_accepts_repeated_real_token():
    rows=[
      {'pass_id':'a','text':'f','confidence':99},
      {'pass_id':'b','text':'f','confidence':99},
      {'pass_id':'a','text':'ACME','confidence':96.4},
      {'pass_id':'b','text':'ACME','confidence':95.0},
      {'pass_id':'c','text':'palate','confidence':31.0},
    ]
    out=vr.ocr_consensus(rows,min_confidence=80,min_token_chars=3,min_consensus_passes=2)
    assert [x['normalized'] for x in out['consensus']]==['acme']


def test_threshold_contract_has_large_actual_to_control_margin():
    cfg=vr.load_config()
    actual_logo=vr.classify_logo(full_scores=[0.51619,0.03685,0.04670,0.40025],foreground_scores=[0.58548,0.05436,0.05122,0.30895],cfg=cfg['logo'])
    emblem_logo=vr.classify_logo(full_scores=[0.16238,0.02990,0.56744,0.24028],foreground_scores=[0.12160,0.03850,0.64810,0.19179],cfg=cfg['logo'])
    actual_wm=vr.classify_watermark(full_scores=[0.88132,0.06225,0.04866,0.00776],cfg=cfg['watermark'])
    control_wm=vr.classify_watermark(full_scores=[0.32188,0.47198,0.20555,0.00058],cfg=cfg['watermark'])
    actual_safe=vr.classify_safety(full_scores=[0.99999,0,0,0.00001,0],foreground_scores=[0.99980,0.00003,0.00001,0.00011,0.00005],cfg=cfg['safety'])
    knife=vr.classify_safety(full_scores=[0.00066,0.99050,0.00095,0.00090,0.00699],foreground_scores=[0.00006,0.99822,0.00004,0.00027,0.00141],cfg=cfg['safety'])
    assert actual_logo['disposition']=='CLEAR' and actual_logo['positive_score']<0.11
    assert emblem_logo['disposition']=='STRONG_CANDIDATE' and emblem_logo['positive_score']>0.60
    assert actual_wm['disposition']=='CLEAR' and actual_wm['positive_score']<0.13
    assert control_wm['disposition']=='STRONG_CANDIDATE' and control_wm['positive_score']>0.65
    assert actual_safe['disposition']=='CLEAR' and actual_safe['unsafe_score']<0.001
    assert knife['disposition']=='BLOCK' and knife['unsafe_score']>0.99
    actual_ip=vr.classify_source_ip(full_scores=[0.998421,0.001547,0.000015,0.000009,0.000007],foreground_scores=[0.997396,0.002540,0.000035,0.000018,0.000011],cfg=cfg['source_ip'])
    branded_ip=vr.classify_source_ip(full_scores=[0.064898,0.912004,0.013263,0.009212,0.000623],foreground_scores=[0.111934,0.856874,0.022100,0.008500,0.000592],cfg=cfg['source_ip'])
    character_ip=vr.classify_source_ip(full_scores=[0.000067,0.000078,0.998002,0.001851,0.000001],foreground_scores=[0.000040,0.000032,0.999850,0.000076,0.000002],cfg=cfg['source_ip'])
    assert actual_ip['disposition']=='CLEAR' and actual_ip['risk_score']<0.01
    assert branded_ip['disposition']=='STRONG_RISK' and branded_ip['risk_score']>0.90
    assert character_ip['disposition']=='STRONG_RISK' and character_ip['risk_score']>0.99


def test_frozen_actual_detector_run_is_complete_and_clear():
    d=json.loads((F/'FA-204-visual-rights-detector-run.json').read_text())
    assert d['master_sha256']=='5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06'
    assert d['runtime']['cpu_only'] is True
    assert d['runtime']['clip_checkpoint_sha256']=='afeb0e10f9e5a86da6080e35cf09123aca3b358a0c3e3b6c78a7b63bc04b6762'
    assert d['runtime']['tesseract_version']=='tesseract 5.3.4'
    assert d['runtime']['self_test_result']=='PASS'
    assert d['ocr']['consensus']==[]
    assert all(x['state']=='COMPLETE' for x in d['observation']['detectors'].values())
    assert d['observation']['detectors']['logo']['candidates']==[]
    assert d['observation']['detectors']['watermark']['candidates']==[]
    assert d['observation']['detectors']['safety']['flags']==[]
    assert d['classification']['source_ip']['disposition']=='CLEAR'
    assert d['classification']['source_ip']['risk_score']<0.01


def test_detector_self_test_proves_text_logo_watermark_and_unsafe_detection():
    d=json.loads((F/'FA-204-visual-rights-self-test.json').read_text())
    assert d['result']=='PASS' and d['failures']==[]
    assert any(x['normalized']=='watermark' for x in d['controls']['watermark']['ocr']['consensus'])
    assert d['controls']['watermark']['observation']['detectors']['watermark']['candidates'][0]['confirmed'] is True
    assert any(x['normalized']=='acme' for x in d['controls']['logo_text']['ocr']['consensus'])
    assert d['controls']['logo_emblem']['classification']['logo']['disposition']=='STRONG_CANDIDATE'
    assert d['controls']['unsafe_knife']['classification']['safety']['disposition']=='BLOCK'
    assert d['controls']['branded_trade_dress']['classification']['source_ip']['disposition']=='STRONG_RISK'
    assert d['controls']['branded_trade_dress']['classification']['source_ip']['risk_score']>0.90
    assert d['controls']['fictional_character']['classification']['source_ip']['disposition']=='STRONG_RISK'
    assert d['controls']['fictional_character']['classification']['source_ip']['risk_score']>0.99