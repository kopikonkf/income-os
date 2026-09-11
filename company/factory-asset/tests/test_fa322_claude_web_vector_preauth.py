import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
adapter=load('fa322a',ROOT/'company/factory-asset/lib/claude_native_svg_adapter.py')
post=load('fa322p',ROOT/'company/factory-asset/lib/claude_web_vector_postprocess.py')

def bp():return json.loads((ROOT/'company/factory-asset/fixtures/shopping-bag-blueprint-v2/icon.json').read_text())
def test_claude_readiness_profile_is_web_ai_not_cli():
 r=json.loads((ROOT/'company/factory-asset/registries/provider-readiness-profiles.v1.json').read_text())['providers']['claude']
 assert r['allowed_origins']==['https://claude.ai']
 assert any('contenteditable' in x for x in r['composer_selectors'])
 assert r['auth_selectors']

def test_web_worker_uses_broker_lease_and_claude_web_url_only():
 s=(ROOT/'company/factory-asset/lib/claude_web_svg_worker.mjs').read_text()
 assert "acquireClusterTab" in s and "connectLeasedClusterTab" in s and "releaseClusterTab" in s
 assert "providerId:'claude'" in s and "https://claude.ai/new" in s
 assert 'claude CLI' not in s and 'claude.exe' not in s
 assert 'credential_values_read:false' in s and 'cookies_or_tokens_read:false' in s

def test_raw_web_svg_goes_through_fa321_postproduction(tmp_path):
 b=bp();prompt='Create one clean editable shopping bag icon as genuine SVG path source only, with no text, scripts, external refs or raster image.'
 req=adapter.build_request(job_id='FA322-PREAUTH-ICON',blueprint=b,frozen_blueprint_sha256=adapter.sha256_value(b),provider_prompt=prompt)
 svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M10 20 L90 20 L80 90 L20 90 Z" fill="#000000" stroke="none" stroke-width="1"/></svg>'
 r=post.postprocess(request=req,raw_response='```svg\n'+svg+'\n```',output_dir=tmp_path)
 assert r['technical_result']=='PASS' and r['next_state']=='DERIVATIVES_READY'
 assert r['native_svg']=={'source_kind':'CLAUDE_WEB_TEXT_SVG','editable':True,'conversion_from_raster':False,'embedded_raster_only':False}
 assert {x['format'] for x in r['derivatives']}=={'EPS','PNG','JPEG'}
 assert r['semantic_asset_count']==1
 for fmt,name in {'SVG':'master.svg','EPS':'master.eps','PNG':'preview.png','JPEG':'preview.jpg'}.items():
  assert (tmp_path/name).is_file() and r['files'][fmt]['bytes']>0
 assert (tmp_path/'postprocess.receipt.json').is_file()
