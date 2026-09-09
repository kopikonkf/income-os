import importlib.util,json,sys,threading,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];LIB=ROOT/'company/factory-asset/lib/founder_qc_gallery.py';CONSOLE=ROOT/'company/factory-asset/console-prototype'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
def test_gallery_uses_e4_accepted_truth_and_one_workspace_representative(tmp_path):
 repo=tmp_path/'repo';c=repo/'company/factory-asset/fixtures/scale';c.mkdir(parents=True);(c/'FA-124-cartoon-watercolor-cohort.json').write_text(json.dumps({'jobs':[{'job_id':'J1','seed_id':'S1','seed_noun':'apple'}]}))
 fa=tmp_path/'fa';img=fa/'jobs/J1/provider/source-original.png';img.parent.mkdir(parents=True);img.write_bytes(b'PNGDATA');(fa/'FA124-E4-final.json').write_text(json.dumps({'technical_qa':[{'job_id':'J1','seed_id':'S1','seed_noun':'apple','provider_id':'qwen','cluster_id':'cluster-a','status':'SUCCEEDED','technical_qa':{'result':'PASS','path':str(img),'bytes':7,'format':'PNG','width_px':512,'height_px':512,'orientation_result':'PASS'}}]}))
 work=tmp_path/'work';ws=work/'PROD1';(ws/'final').mkdir(parents=True);(ws/'final/asset.jpg').write_bytes(b'JPEGDATA');(ws/'seed-selection.json').write_text(json.dumps({'seed':{'id':'S2','canonical_name':'chair'}}))
 m=load('qc_unit',LIB);d=m.build_gallery(repo,workspaces_root=work,fa124_root=fa);assert d['asset_count']==2 and d['source_counts']=={'FA124_CANARY':1,'PRODUCTION_WORKSPACE':1};assert all('_path' not in x for x in d['items']);a=d['items'][0];body,ctype=m.image_payload(repo,a['asset_id'],'full',workspaces_root=work,fa124_root=fa);assert body==b'PNGDATA' and ctype=='image/png'
def test_live_gallery_indexes_exact_fa124_100_and_hides_paths():
 m=load('qc_live',LIB);d=m.build_gallery(ROOT);assert d['source_counts']['FA124_CANARY']==100;assert d['asset_count']>=100;txt=json.dumps(d);assert '/var/lib/die/' not in txt and d['founder_qc_mutation_enabled'] is False
def test_console_has_qc_gallery_surface():
 html=(CONSOLE/'index.html').read_text();js=(CONSOLE/'app.js').read_text();assert 'data-view="qc"' in html and 'QC Gallery' in html;assert "getLocal('/api/qc-gallery')" in js and '/api/qc-image' not in js;assert 'Founder QC Gallery' in js and 'Read-only review' in js
