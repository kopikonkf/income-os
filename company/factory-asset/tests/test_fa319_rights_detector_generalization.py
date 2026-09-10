import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CFG=ROOT/'company/factory-asset/registries/visual-rights-detector.v1.json'

def test_visual_rights_detector_prompts_are_subject_agnostic():
    d=json.loads(CFG.read_text(encoding='utf-8'))
    assert d['revision']=='1.1'
    text=' '.join(d['logo']['prompts']+[d['safety']['prompts'][0],d['source_ip']['prompts'][0]]).casefold()
    assert 'shopping bag' not in text
    assert 'isolated stock object' in text
    assert d['logo']['positive_indices']==[1,2]
    assert d['logo']['review_positive_score']==0.2
    assert d['logo']['strong_candidate_score']==0.4
    assert d['source_ip']['risk_indices']==[1,2,3,4]

def test_graphic_logo_self_test_uses_subject_agnostic_badge_not_fixed_4096_star():
    src=(ROOT/'company/factory-asset/bin/run_visual_rights_detector.py').read_text(encoding='utf-8')
    assert 'w,h=emblem.size' in src
    assert 'min(w,h)//14' in src
    assert "emblem.save(target/'logo_emblem.png')" in src
    assert '[(1680,1700,2416,2436)' not in src
