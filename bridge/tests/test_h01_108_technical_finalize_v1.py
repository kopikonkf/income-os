import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company/company-os/die-h01';ENG=H01/'engineering'
sys.path.insert(0,str(ENG))
from svg_prompt_composer_v2 import compile_master_instruction,compile_provider_prompt

def test_technical_finalize_creates_generation_terminal_without_postproduction():
 with tempfile.TemporaryDirectory() as td:
  w=Path(td);f=w/'final';f.mkdir()
  bp=json.loads((H01/'fixtures/h01-102-book-blueprint.v2.json').read_text());mi=compile_master_instruction(bp);pp=compile_provider_prompt(blueprint=bp,master=mi,provider_profile='GEMINI_WEB')
  manifest=json.loads((H01/'fixtures/h01-108/market-informed-100.json').read_text());it=next(x for x in manifest['items'] if x['canonical_name']=='book')
  (w/'blueprint.json').write_text(json.dumps(bp));(w/'master-instruction.json').write_text(json.dumps(mi));(w/'provider-prompt.json').write_text(json.dumps(pp));(w/'batch-item.json').write_text(json.dumps(it))
  raw=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="60" fill="#334455"/></svg>';h=hashlib.sha256(raw).hexdigest();(f/'provider-original.svg').write_bytes(raw)
  (w/'artifact-created.receipt.json').write_text(json.dumps({'status':'ARTIFACT_CREATED','job_id':'H01-108-P001-CAND-0829866-A1','batch_position':it['batch_position'],'noun':'book','provider_id':'gemini','profile_id':'h01-web-p001','udd_id':'h01-web-s01','provider_original_path':str(f/'provider-original.svg'),'provider_original_sha256':h,'semantic_asset_id':bp['semantic_asset_id']}))
  cp=subprocess.run([sys.executable,str(ENG/'h01_108_technical_finalize.py'),'--workspace',str(w)],capture_output=True,text=True)
  assert cp.returncode==0,cp.stderr+cp.stdout
  g=json.loads((w/'generation-complete.receipt.json').read_text());v=json.loads((f/'h01-103-validation.json').read_text())
  assert g['status']=='GENERATION_COMPLETE';assert v['status']=='PASS';assert g['canonical_svg_sha256']==v['canonical_svg_sha256'];assert g['provider_original_sha256']==h
  assert not (w/'postproduction').exists();assert not (w/'rights-precheck.json').exists();assert not (w/'asset-receipt.json').exists()
