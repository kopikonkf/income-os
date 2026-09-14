import hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company/company-os/die-h01/engineering/h01_108_seal_generation.py'
S=importlib.util.spec_from_file_location('h01seal',MOD);M=importlib.util.module_from_spec(S);assert S and S.loader;sys.modules[S.name]=M;S.loader.exec_module(M)

def item(pos,name):return {'batch_position':pos,'canonical_name':name,'queue_item_id':f'H01-SVGQ-CAND-{pos:07d}','source_candidate_id':f'CAND-{pos:07d}'}
def make_workspace(root,it,provider='gemini'):
 w=root/f"{it['batch_position']:03d}-{it['canonical_name']}-{provider}-a1";(w/'final').mkdir(parents=True)
 raw=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>';h=hashlib.sha256(raw).hexdigest();(w/'final/provider-original.svg').write_bytes(raw)
 (w/'final/h01-103-validation.json').write_text(json.dumps({'status':'PASS','input_sha256':h,'canonical_svg_sha256':'c'+str(it['batch_position']),'native_editable':True,'conversion_from_raster':False}))
 (w/'artifact-created.receipt.json').write_text(json.dumps({'status':'ARTIFACT_CREATED','provider_original_sha256':h,'provider_id':provider,'profile_id':'h01-web-p001','udd_id':'h01-web-s01','job_id':'J'+str(it['batch_position']),'created_at':'2026-09-14T00:00:00Z'}))
 (w/'blueprint.json').write_text(json.dumps({'semantic_asset_id':f"H01SVG-{it['source_candidate_id']}"}));return w

def test_seal_writes_generation_only_complete_pass_and_is_idempotent(monkeypatch):
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);runs=root/'runs';runs.mkdir();items=[item(1,'book'),item(2,'chair')];manifest=root/'manifest.json';manifest.write_text(json.dumps({'items':items}));progress=root/'progress.json';progress.write_text(json.dumps({'status':'AWAITING_RIGHTS_ACCEPTANCE','accepted_count':0}))
  ws=[make_workspace(runs,x) for x in items]
  monkeypatch.setattr(sys,'argv',['seal','--manifest',str(manifest),'--runs-root',str(runs),'--progress-file',str(progress)]);assert M.main()==0
  p=json.loads(progress.read_text());assert p['status']=='COMPLETE_PASS';assert p['generated_count']==2;assert p['remaining_count']==0;assert 'rights_acceptance_boundary' not in p;assert 'accepted_count' not in p
  for w in ws:
   g=json.loads((w/'generation-complete.receipt.json').read_text());assert g['status']=='GENERATION_COMPLETE';assert g['h01_103_status']=='PASS';assert g['postproduction_state']=='INDEPENDENT_DOWNSTREAM'
  monkeypatch.setattr(sys,'argv',['seal','--manifest',str(manifest),'--runs-root',str(runs),'--progress-file',str(progress)]);assert M.main()==0
  assert (root/'autonomous-progress.pre-generation-seal.json').exists()

def test_seal_ignores_rights_outcome_for_generation(monkeypatch):
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);runs=root/'runs';runs.mkdir();it=item(1,'book');manifest=root/'manifest.json';manifest.write_text(json.dumps({'items':[it]}));w=make_workspace(runs,it);(w/'asset-receipt.json').write_text(json.dumps({'rights':'BLOCK','postproduction_classification':'BLOCKED_RIGHTS'}))
  monkeypatch.setattr(sys,'argv',['seal','--manifest',str(manifest),'--runs-root',str(runs),'--progress-file',str(root/'progress.json')]);assert M.main()==0;assert json.loads((w/'generation-complete.receipt.json').read_text())['status']=='GENERATION_COMPLETE'
