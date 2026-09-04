import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('pr',R/'company/factory-asset/lib/package_readiness.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();BP=json.loads((R/'company/factory-asset/fixtures/shopping-bag-blueprint-v2/photo.json').read_text());REC=json.loads((R/'company/factory-asset/receipts/FA-137-metadata-package-readiness.receipt.json').read_text())
def args():
 return {'blueprint':BP,'derivative_plan':REC['derivative_plan'],'rights_signal':REC['rights_signal'],'derivative_evidence':REC['derivatives'],'provenance':{'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI'},'master_technical_qa':{'result':'PASS','master_sha256':REC['master']['sha256']}}
def test_metadata_deterministic():
 a=m.evaluate_package_readiness(**args());b=m.evaluate_package_readiness(**args());assert a['metadata']==b['metadata'] and a['package_plan']==b['package_plan']
def test_rights_review_never_package_ready():
 x=args();x['rights_signal']=json.loads(json.dumps(x['rights_signal']));x['rights_signal']['result']='REVIEW_REQUIRED';r=m.evaluate_package_readiness(**x);assert r['result']=='PACKAGE_BLOCKED' and 'RIGHTS_REVIEW_REQUIRED' in r['blockers']
def test_missing_ai_disclosure_blocks():
 x=args();x['provenance']['ai_disclosure']=None;r=m.evaluate_package_readiness(**x);assert r['result']=='PACKAGE_BLOCKED' and 'AI_DISCLOSURE_REQUIRED' in r['blockers']
def test_tampered_derivative_hash_blocks_against_qa_hash():
 x=args();x['derivative_evidence']=json.loads(json.dumps(x['derivative_evidence']));x['derivative_evidence'][0]['sha256']='0'*64;r=m.evaluate_package_readiness(**x);assert r['result']=='PACKAGE_BLOCKED' and any(v.startswith('DERIVATIVE_QA_HASH_MISMATCH:') for v in r['blockers'])