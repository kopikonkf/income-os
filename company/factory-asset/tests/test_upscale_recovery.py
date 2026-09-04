import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('ur',R/'company/factory-asset/lib/upscale_recovery.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();BASE={'schema':'die.factory-asset.master-facts.v1','sha256':'a'*64,'format':'PNG','width_px':100,'height_px':80}
def test_sufficient_dimensions_skip():
 d=m.decide_upscale_recovery(master=BASE,route_requirement={'min_width_px':100,'min_height_px':80});assert d['state']=='NOOP_SUFFICIENT'
def test_short_dimensions_require_upscale():
 d=m.decide_upscale_recovery(master=BASE,route_requirement={'min_width_px':200,'min_height_px':160},technical_defects=['TECHNICAL_DIMENSION_BELOW_MINIMUM']);assert d['state']=='UPSCALE_REQUIRED' and d['target_dimensions']==[200,160]
def test_recoverable_quality_defect_with_sufficient_dimensions_routes_recovery():
 d=m.decide_upscale_recovery(master=BASE,route_requirement={'min_width_px':80,'min_height_px':60},technical_defects=['DETAIL_SOFTNESS']);assert d['state']=='RECOVERY_REQUIRED' and d['target_dimensions']==[100,80]
def test_rights_review_and_unknown_defect_never_recovered():
 assert m.decide_upscale_recovery(master=BASE,route_requirement={'min_width_px':200,'min_height_px':160},rights_state='REVIEW_REQUIRED')['state']=='BLOCK_NONRECOVERABLE';assert m.decide_upscale_recovery(master=BASE,route_requirement={'min_width_px':200,'min_height_px':160},technical_defects=['MYSTERY_DEFECT'])['state']=='BLOCK_NONRECOVERABLE'