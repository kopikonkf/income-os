import importlib.util,sys,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('led',ROOT/'company/die-agents/hermes/production_seed_ledger.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m)

def ident(mode='ISOLATED_OBJECT',expr='gift box reusable stock component',preset='ISOLATED_CARTOON_WATERCOLOR_L0',rev='1.0.0'):
 return m.expression_identity(seed_id='SEED-000028',noun='Gift Box',semantic_mode=mode,commercial_expression=expr,preset_id=preset,preset_revision=rev)

def test_same_noun_different_semantic_mode_and_preset_are_distinct_identities(tmp_path):
 led=tmp_path/'l.db'
 a=ident();b=ident(mode='ICON',expr='gift box icon for ecommerce navigation',preset='ICON_CLEAN_V1')
 c=ident(expr='gift box reusable stock component',preset='ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0')
 assert len({a['expression_fingerprint'],b['expression_fingerprint'],c['expression_fingerprint']})==3
 assert m.claim_expression(led,a,source_scope='TEST',source_ref='A')['status']=='CLAIMED'
 assert not m.expression_consumed(led,b)
 assert m.claim_expression(led,b,source_scope='TEST',source_ref='B')['status']=='CLAIMED'
 assert m.claim_expression(led,c,source_scope='TEST',source_ref='C')['status']=='CLAIMED'

def test_exact_expression_replay_is_idempotent(tmp_path):
 led=tmp_path/'l.db';a=ident()
 x=m.claim_expression(led,a,source_scope='TEST',source_ref='A');y=m.claim_expression(led,a,source_scope='RETRY',source_ref='A2')
 assert x['status']=='CLAIMED' and y['status']=='ALREADY_CLAIMED' and y['idempotent_replay'] is True
 c=sqlite3.connect(led);assert c.execute('select count(*) from production_expression_consumption').fetchone()[0]==1;assert c.execute('select count(*) from production_expression_consumption_evidence').fetchone()[0]==2;c.close()

def test_near_duplicate_same_seed_mode_preset_is_quarantined(tmp_path):
 led=tmp_path/'l.db';a=ident(expr='editable gift box icon for ecommerce checkout navigation',mode='ICON',preset='ICON_CLEAN_V1')
 b=ident(expr='gift box editable icon for ecommerce checkout navigation',mode='ICON',preset='ICON_CLEAN_V1')
 assert m.claim_expression(led,a,source_scope='TEST',source_ref='A')['status']=='CLAIMED'
 q=m.claim_expression(led,b,source_scope='TEST',source_ref='B')
 assert q['status']=='QUARANTINED_NEAR_DUPLICATE' and q['similarity']>=0.85
 c=sqlite3.connect(led);assert c.execute('select count(*) from production_expression_quarantine').fetchone()[0]==1;assert c.execute('select count(*) from production_expression_consumption').fetchone()[0]==1;c.close()

def test_packaging_derivative_does_not_change_expression_identity():
 a=ident();b=ident()
 # Delivery format is deliberately absent from identity material.
 assert a==b and set(a)=={'expression_fingerprint','seed_id','normalized_noun','semantic_mode','normalized_commercial_expression','preset_id','preset_revision'}

def test_legacy_noun_replay_preserves_history_but_does_not_consume_new_expression(tmp_path):
 led=tmp_path/'l.db';c=m._connect(led)
 c.execute('insert into production_seed_consumption values(?,?,?,?,?,?,?)',('gift box','Gift Box','SEED-000028','OLD','OLDREF','2026-01-01T00:00:00Z','CLAIMED'));c.commit();c.close()
 r=m.bootstrap_expression_legacy_replay(led);assert r['legacy_rows']==1 and r['identity_scope']=='LEGACY_NOUN_ONLY' and r['blocks_new_semantic_expressions'] is False
 a=ident();assert m.expression_consumed(led,a) is False
 c=sqlite3.connect(led);row=c.execute('select identity_scope from production_expression_legacy_replay where normalized_noun=?',('gift box',)).fetchone();c.close();assert row[0]=='LEGACY_NOUN_ONLY'

def test_identity_normalization_is_stable():
 a=m.expression_identity(seed_id='SEED-000028',noun=' Gift   Box ',semantic_mode='isolated_object',commercial_expression='Reusable  GIFT-box component!',preset_id='P',preset_revision='1')
 b=m.expression_identity(seed_id='SEED-000028',noun='gift box',semantic_mode='ISOLATED_OBJECT',commercial_expression='reusable gift box component',preset_id='P',preset_revision='1')
 assert a['expression_fingerprint']==b['expression_fingerprint']
 assert a['normalized_noun']=='gift box' and a['normalized_commercial_expression']=='reusable gift box component'
