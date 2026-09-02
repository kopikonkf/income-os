from __future__ import annotations
import importlib.util,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'company/die-agents/hermes/production-cognition/production_cognition_tick.py'
spec=importlib.util.spec_from_file_location('pcog',P); m=importlib.util.module_from_spec(spec); sys.modules['pcog']=m; spec.loader.exec_module(m)
def snapshot():return {'schema':'die.production.seed-snapshot.v1','repository_sha':'a'*40,'seed':{'id':'SEED-000027','canonical_name':'trophy','object_class':'award','category_path':'Business/Award','demand_score':0.812,'demand_status':'validated_high','asset_tier':'U1-raster'}}
def req(rid='COG-PROD_BP_AUTHOR_TASK0001_R00'):return {'schema':'die.cognition.outbox-request.v1','company_instance_id':'DIE-LINUX','request_id':rid,'task_id':'TASK0001','action_type':'PRODUCTION_BLUEPRINT_AUTHOR','target_principal_id':m.DIV,'thread_generation':1,'prompt':'x','expected_response_schema':'die.production.family-blueprint.v1','repository_sha':'a'*40,'evidence_refs':[],'created_at':'2026-09-02T00:00:00Z','expires_at':'2026-09-02T01:00:00Z'}
def blueprint(rid='COG-PROD_BP_AUTHOR_TASK0001_R00'):
 s=snapshot();return {'schema_version':'die.production.family-blueprint.v1','request_id':rid,'blueprint_id':'BP-PROD-TROPHY_0001','task_id':'TASK0001','mission_id':'M-001','repository_sha':'a'*40,'principal':{'principal_id':m.DIV,'role':'AUTHOR'},'seed':s['seed'],'family':{'family_id':'FAM-PROD-AWARD_001','family_thesis':'Commercially useful generic award trophy imagery for business recognition communications.','buyer_persona':['business marketer'],'use_cases':['employee recognition campaign'],'commercial_use_hypothesis':'A generic unbranded trophy can support business award and recognition communication needs.','evidence_status':'OBJECT_ATLAS_ONLY_HYPOTHESIS'},'production':{'asset_type':'RASTER_IMAGE','batch_size':1,'engine':'MUXIA/chatgpt-linux-a','master_prompt':'Create a realistic generic unbranded trophy award on a clean neutral business presentation surface with useful copy space, professional commercial lighting, no text or logos.','negative_constraints':['no logos','no trademarks','no watermark'],'semantic_variation_plan':[{'variation_id':'VAR-USECASE_001','dimension':'buyer_use_case','instruction':'Frame for an employee recognition communication use case.','commercial_rationale':'Tests generic business recognition utility.'}]},'metadata_direction':{'title_direction':'Generic trophy award for business recognition communication','primary_keywords':['trophy award','business recognition','achievement'],'category_direction':['business','awards']},'qa_requirements':{'required_checks':['artifact integrity','technical QA','visual commercial QC'],'forbidden_elements':['logos','trademarks','watermarks']},'lineage':{'seed_snapshot_sha256':m.csha(s),'source_kind':'OBJECT_ATLAS_SEED','external_market_evidence_claimed':False},'authority':{'effect':'NONE','existing_production_authority_unchanged':True,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}
def review(bp,rid='COG-PROD_BP_REVIEW_TASK0001_R00'):return {'schema_version':'die.production.family-blueprint-review.v1','request_id':rid,'review_id':'BP-REVIEW-PROD-TROPHY_0001','task_id':'TASK0001','repository_sha':'a'*40,'principal':{'principal_id':m.EXEC,'role':'REVIEWER'},'blueprint':{'blueprint_id':bp['blueprint_id'],'sha256':m.csha(bp)},'outcome':'NO_VETO','rationale':'The Blueprint is coherent, unbranded, bounded, and truthfully labels commercial utility as an Object-Atlas-only hypothesis.','required_actions':[],'review_mode':'READ_ONLY_CHALLENGE','semantic_content_authored':False,'authority_effect':'NONE'}
def test_blueprint_schema_and_seed_binding():
 s=snapshot();r=req();b=blueprint();assert m.validation is not None
 # use validator module directly
 vspec=importlib.util.spec_from_file_location('v',ROOT/'company/die-agents/hermes/production-cognition/validate_production_cognition.py');v=importlib.util.module_from_spec(vspec);vspec.loader.exec_module(v);assert v.validate_blueprint(b,request=r,seed_snapshot=s)==[];bad=json.loads(json.dumps(b));bad['seed']['id']='SEED-999999';assert 'E_SEED_DRIFT:id' in v.validate_blueprint(bad,request=r,seed_snapshot=s)
def test_review_is_hash_bound():
 bp=blueprint();r=req('COG-PROD_BP_REVIEW_TASK0001_R00');r['action_type']='PRODUCTION_BLUEPRINT_REVIEW';r['target_principal_id']=m.EXEC;r['expected_response_schema']='die.production.family-blueprint-review.v1';rv=review(bp);vspec=importlib.util.spec_from_file_location('v2',ROOT/'company/die-agents/hermes/production-cognition/validate_production_cognition.py');v=importlib.util.module_from_spec(vspec);vspec.loader.exec_module(v);assert v.validate_review(rv,request=r,blueprint=bp)==[];rv['blueprint']['sha256']='0'*64;assert 'E_BLUEPRINT_BINDING' in v.validate_review(rv,request=r,blueprint=bp)
def test_progress_update_is_deterministic(tmp_path):
 w=tmp_path/'TASK';w.mkdir();(w/'PROGRESS.md').write_text('# x\n- State: BLUEPRINT_REQUIRED\n- Blueprint status: NONE\n- Next action: old\n');m.update_progress(w,state='BLUEPRINT_READY',blueprint_status='FIXED BP',next_action='Dispatch Worker');t=(w/'PROGRESS.md').read_text();assert t.count('- State:')==1;assert 'BLUEPRINT_READY' in t;assert 'Dispatch Worker' in t
def test_active_card_ignores_non_blueprint(tmp_path):
 a=tmp_path/'A';a.mkdir();(a/'PROGRESS.md').write_text('- State: WAITING_FOUNDER_QC\n');assert m.active_blueprint_card(tmp_path) is None
def test_parse_response_accepts_single_json_fence():
 assert m.parse_response('```json\n{"a":1}\n```')=={'a':1}


def test_blocked_response_is_request_and_principal_bound():
 r=req(); good={'schema':'die.cognition.blocked.v1','request_id':r['request_id'],'principal_id':m.DIV,'reason_code':'E_X','reason':'bounded'};assert m.validate_blocked_response(good,r)==[];bad=dict(good);bad['principal_id']=m.EXEC;assert 'E_BLOCKED_PRINCIPAL' in m.validate_blocked_response(bad,r)

def test_synthetic_author_review_no_veto_reaches_blueprint_ready(tmp_path, monkeypatch):
    import subprocess as sp
    repo=tmp_path/'repo';repo.mkdir();sp.run(['git','init','-q',str(repo)],check=True);sp.run(['git','-C',str(repo),'config','user.email','t@example.invalid'],check=True);sp.run(['git','-C',str(repo),'config','user.name','T'],check=True);(repo/'x').write_text('x');sp.run(['git','-C',str(repo),'add','x'],check=True);sp.run(['git','-C',str(repo),'commit','-qm','x'],check=True);sha=sp.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    wsroot=tmp_path/'ws';w=wsroot/'TASK0001';w.mkdir(parents=True);(w/'PROGRESS.md').write_text('# p\n- Seed: SEED-000027 (trophy)\n- Family: Business/Award\n- State: BLUEPRINT_REQUIRED\n- Blueprint status: NONE\n- Started: 2026-09-02T00:00:00Z\n- Next action: author\n')
    dbp=tmp_path/'atlas.db';c=sqlite3.connect(dbp);c.execute('create table seeds(id text,canonical_name text,object_class text,category_path text,demand_score real,demand_status text,asset_tier text,status text)');c.execute("insert into seeds values('SEED-000027','trophy','award','Business/Award',0.812,'validated_high','U1-raster','approved')");c.commit();c.close()
    monkeypatch.setattr(m,'thread_generation',lambda principal:1 if principal==m.DIV else 2)
    def fake_transport(node,transport,reqp,response,timeout=270):
        rq=json.load(open(reqp));cog=w/'cognition';trp=cog/'fake-transport'/f"{rq['request_id']}.json";trp.parent.mkdir(parents=True,exist_ok=True)
        if rq['action_type'] in {'PRODUCTION_BLUEPRINT_AUTHOR','PRODUCTION_BLUEPRINT_REVISE'}:
            snap=json.load(open(cog/'seed-snapshot.json'));b=blueprint(rq['request_id']);b['task_id']='TASK0001';b['repository_sha']=sha;b['seed']=snap['seed'];b['lineage']['seed_snapshot_sha256']=m.csha(snap);payload=b
        else:
            bp=json.load(open(cog/'blueprint.author.json'));payload=review(bp,rq['request_id']);payload['task_id']='TASK0001';payload['repository_sha']=sha
        response.parent.mkdir(parents=True,exist_ok=True);response.write_text(json.dumps(payload)+'\n');tr={'schema':'die.cognition.roundtrip-receipt.v1','request_id':rq['request_id'],'response_sha256':m.csha(payload)};m.atomic_json(trp,tr);return {'receipt_ref':str(trp)}
    monkeypatch.setattr(m,'run_transport',fake_transport)
    class A:pass
    a=A();a.workspaces=str(wsroot);a.db=str(dbp);a.repo=str(repo);a.state_root=str(tmp_path/'state');a.node='node';a.transport='fake';a.hermes_bin='hermes';a.hermes_home='home';a.production_job_id='job';a.no_resume=True
    first=m.tick(a);assert first['status']=='ADVANCED' and first['to']=='NEED_REVIEW'
    second=m.tick(a);assert second['status']=='BLUEPRINT_READY'
    assert json.load(open(w/'cognition/state.json'))['stage']=='READY'
    assert (w/'blueprint.json').is_file() and (w/'blueprint.lock.json').is_file()
    text=(w/'PROGRESS.md').read_text();assert 'State: BLUEPRINT_READY' in text and 'Dispatch bounded Worker' in text
    receipts=list((w/'cognition/receipts').glob('*.receipt.json'));assert len(receipts)==2


def test_repo_sha_command_scopes_safe_directory_to_repo():
 t=P.read_text()
 assert "'git','-c',f'safe.directory={args.repo}','-C',args.repo,'rev-parse','HEAD'" in t


def test_node_runtime_is_discovered_not_hardcoded():
 t=P.read_text()
 assert "shutil.which('node')" in t
