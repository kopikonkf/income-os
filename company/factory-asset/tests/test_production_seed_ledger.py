import importlib.util,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; H=ROOT/'company/die-agents/hermes'
if str(H) not in sys.path:sys.path.insert(0,str(H))
from production_seed_ledger import bootstrap_seed_ledger,consumed,normalize_noun
from production_seed_selector import select_seed

def make_db(p):
 c=sqlite3.connect(p);c.executescript('''CREATE TABLE seeds(id TEXT PRIMARY KEY,canonical_name TEXT,object_class TEXT,existence_type TEXT,category_path TEXT,demand_score REAL,demand_status TEXT,asset_tier TEXT,risk_score REAL,status TEXT,source_batch TEXT,master_source_id TEXT,demand_signal TEXT);''');return c

def test_bootstrap_dedupes_overlap_but_preserves_evidence(tmp_path):
 ws=tmp_path/'w';w=ws/'PROD1';w.mkdir(parents=True);(w/'seed-selection.json').write_text(json.dumps({'seed':{'id':'SEED-000001','canonical_name':'water bottle'}}))
 fa=tmp_path/'e4.json';fa.write_text(json.dumps({'technical_qa':[{'job_id':'J1','seed_id':'SEED-000001','seed_noun':'water bottle','status':'SUCCEEDED','technical_qa':{'result':'PASS','sha256':'a'*64}}]}))
 led=tmp_path/'ledger.db';r=bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=fa);assert r['consumed_nouns']==1 and r['evidence_rows']==2;ids,names=consumed(led);assert 'SEED-000001' in ids and 'water bottle' in names

def test_selector_excludes_consumed_noun_even_with_different_seed_id(tmp_path):
 db=tmp_path/'a.db';c=make_db(db);c.executemany('INSERT INTO seeds VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[('SEED-000001','bottle','concrete_visual','real_world','x',.9,'validated_high','U1-raster',0,'approved','x',None,'x'),('SEED-000002','candle','concrete_visual','real_world','x',.8,'validated_high','U1-raster',0,'approved','x',None,'x')]);c.commit();c.close()
 ws=tmp_path/'w';w=ws/'OLD';w.mkdir(parents=True);(w/'seed-selection.json').write_text(json.dumps({'seed':{'id':'CANARY-1','canonical_name':'bottle'}}));led=tmp_path/'ledger.db';bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=tmp_path/'missing')
 r=select_seed(db,ws,ledger_path=led);assert r['seed']['id']=='SEED-000002' and r['seed']['canonical_name']=='candle'

def test_normalize_noun_collapses_punctuation_case():assert normalize_noun(' Water-Bottle!! ')=='water bottle'

def test_replenisher_skips_consumed_candidate_noun(tmp_path):
 from production_seed_replenisher import replenish_seed_pool
 db=tmp_path/'atlas.db';c=sqlite3.connect(db)
 c.executescript('''CREATE TABLE seeds(id TEXT PRIMARY KEY,canonical_name TEXT,aliases TEXT,object_class TEXT,existence_type TEXT,category_path TEXT,visuality_score REAL,demand_score REAL,risk_score REAL,status TEXT,created_at TEXT,updated_at TEXT,canonical_lang TEXT,asset_tier TEXT,source_batch TEXT,master_source_id TEXT,demand_signal TEXT,demand_status TEXT);CREATE TABLE candidate_seeds(id TEXT PRIMARY KEY,canonical_name TEXT,aliases TEXT,word_count INTEGER,concreteness_score REAL,suitability TEXT,ip_risk TEXT,source_tier TEXT,wave3_status TEXT,promoted_to_seed_id TEXT,status TEXT,updated_at TEXT);''')
 c.execute("INSERT INTO seeds VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('SEED-000001','legacy','[]','concrete_visual','real_world','x',1,.8,0,'approved','x','x','en-US','U1-raster','x',None,'x','validated_high'))
 for cid,name in [('CAND-1','bottle'),('CAND-2','candle')]:c.execute("INSERT INTO candidate_seeds VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(cid,name,'[]',1,.95,'lexname=noun.artifact','none','pass','eligible',None,'pending','x'))
 c.commit();c.close()
 ws=tmp_path/'work';w=ws/'OLD';w.mkdir(parents=True);(w/'seed-selection.json').write_text(json.dumps({'seed':{'id':'CANARY-1','canonical_name':'bottle'}}))
 led=tmp_path/'ledger.db';bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=tmp_path/'missing')
 policy=tmp_path/'policy.json';policy.write_text(json.dumps({'schema':'die.production.seed-replenishment-policy.v1','revision':'t','low_watermark':2,'target_pool_size':3,'max_promotions_per_run':3,'candidate_gate':{'wave3_status':'eligible','source_tier':'pass','ip_risk':'none','min_concreteness_score':.85,'max_word_count':3,'allowed_suitability':['lexname=noun.artifact']},'evidence':{'source_kind':'TEST','source_title':'test','source_date':'x','claims':[],'truth_boundary':{}},'direct_terms':['bottle','candle'],'utility_terms':[],'scoring':{'direct_base':.72,'category_base':.58,'concreteness_bonus_max':.06,'class_bonus':{'lexname=noun.artifact':.03},'validated_high_threshold':.68,'validated_medium_threshold':.55},'expression':{'mode':'T','template':'generic {noun}','semantic_identity':'x'},'authority':{'provider_call':False,'submission':False,'publication':False,'marketplace_upload':False,'spend_usd':0}}))
 r=replenish_seed_pool(db,ws,policy_path=policy,state_root=tmp_path/'state',ledger_path=led)
 names=[x['canonical_name'] for x in r.get('promoted',[])];assert 'bottle' not in names and 'candle' in names


def test_fa124_seed_id_is_evidence_not_object_atlas_identity(tmp_path):
 ws=tmp_path/'w';ws.mkdir();fa=tmp_path/'e4.json';fa.write_text(json.dumps({'technical_qa':[{'job_id':'J','seed_id':'SEED-999999','seed_noun':'rope','status':'SUCCEEDED','technical_qa':{'result':'PASS','sha256':'b'*64}}]}));led=tmp_path/'l.db';bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=fa);ids,names=consumed(led);assert 'SEED-999999' not in ids and 'rope' in names


def test_bootstrap_reads_legacy_progress_when_selection_missing(tmp_path):
 ws=tmp_path/'w';w=ws/'PRODSEED000022';w.mkdir(parents=True);(w/'PROGRESS.md').write_text('# x\n\n- Seed: SEED-000022 (candle)\n- State: WAITING_FOUNDER_QC\n');led=tmp_path/'l.db';r=bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=tmp_path/'missing');ids,names=consumed(led);assert 'SEED-000022' in ids and 'candle' in names and r['evidence_rows']==1


def test_selector_allows_same_legacy_noun_for_distinct_semantic_expression(tmp_path):
 from production_seed_selector import select_seed
 db=tmp_path/'a.db';c=make_db(db);c.executemany('INSERT INTO seeds VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[('SEED-000001','bottle','concrete_visual','real_world','x',.9,'validated_high','U1-raster',0,'approved','x',None,'x'),('SEED-000002','candle','concrete_visual','real_world','x',.8,'validated_high','U1-raster',0,'approved','x',None,'x')]);c.commit();c.close()
 ws=tmp_path/'w';w=ws/'OLD';w.mkdir(parents=True);(w/'seed-selection.json').write_text(json.dumps({'seed':{'id':'SEED-000001','canonical_name':'bottle'}}));led=tmp_path/'ledger.db';bootstrap_seed_ledger(ws,ledger_path=led,fa124_e4=tmp_path/'missing')
 # Baseline compatibility remains blocked by legacy noun history.
 baseline=select_seed(db,ws,ledger_path=led);assert baseline['seed']['id']=='SEED-000002'
 # A materially different semantic mode/preset may reuse the same primitive.
 alt=select_seed(db,ws,ledger_path=led,semantic_mode='ICON',preset_id='ICON_CLEAN_V1',preset_revision='1.0.0',commercial_expression_override='editable bottle icon for product interface')
 assert alt['seed']['id']=='SEED-000001' and alt['semantic_mode']=='ICON' and alt['preset_id']=='ICON_CLEAN_V1'
 assert alt['expression_identity']['semantic_mode']=='ICON'
