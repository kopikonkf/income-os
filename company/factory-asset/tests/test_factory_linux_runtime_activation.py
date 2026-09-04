import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def load_resolver():
 p=R/'company/die-agents/hermes/production_active_card_resolver.py';s=importlib.util.spec_from_file_location('fa140a_resolver',p);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load_resolver()
def progress(w,state):
 (w/'PROGRESS.md').write_text(f'# x\n- Seed: SEED-000025 (headphones)\n- Family: Tech/Audio\n- State: {state}\n- Started: 2026-09-03T15:00:14Z\n',encoding='utf-8')
def test_rights_review_card_is_parked_without_complete_exact_observation(tmp_path):
 w=tmp_path/'PRODSEED000025';w.mkdir();progress(w,'WAITING_FOUNDER_RIGHTS_REVIEW');r=m.resolve_active_card(tmp_path);assert r['status']=='NO_ACTIVE_CARD';assert r['parked_card_count']==1 and r['parked_cards'][0]['state']=='WAITING_FOUNDER_RIGHTS_REVIEW'
def test_rights_review_card_resumes_only_with_exact_active_hash_complete_observation(tmp_path):
 w=tmp_path/'PRODSEED000025';w.mkdir();progress(w,'WAITING_FOUNDER_RIGHTS_REVIEW');(w/'factory-v2').mkdir();(w/'factory-v2/postproduction-state.json').write_text(json.dumps({'active_master_sha256':'a'*64}));obs={'schema':'die.factory-asset.rights-observation.v1','master_sha256':'a'*64,'detectors':{k:{'state':'COMPLETE'} for k in ('text','logo','watermark','safety')}};(w/'rights-observation.json').write_text(json.dumps(obs));r=m.resolve_active_card(tmp_path);assert r['status']=='CONTINUE_ACTIVE_CARD';assert r['active_card']['state']=='RIGHTS_SIGNAL_PASS_OR_REVIEW';assert r['active_card']['state_source']=='RIGHTS_OBSERVATION_RESUME'
def test_mismatched_rights_observation_does_not_resume(tmp_path):
 w=tmp_path/'PRODSEED000025';w.mkdir();progress(w,'WAITING_FOUNDER_RIGHTS_REVIEW');(w/'factory-v2').mkdir();(w/'factory-v2/postproduction-state.json').write_text(json.dumps({'active_master_sha256':'a'*64}));obs={'schema':'die.factory-asset.rights-observation.v1','master_sha256':'b'*64,'detectors':{k:{'state':'COMPLETE'} for k in ('text','logo','watermark','safety')}};(w/'rights-observation.json').write_text(json.dumps(obs));assert m.resolve_active_card(tmp_path)['status']=='NO_ACTIVE_CARD'
def test_runtime_wrapper_uses_dedicated_factory_python():
 src=(R/'company/die-agents/hermes/production-runtime/production_runtime_tick.sh').read_text();assert '/opt/die/factory-asset/venv/bin/python' in src;assert 'E_FACTORY_RUNTIME_PYTHON' in src;assert 'exec "$FACTORY_PYTHON"' in src
def test_cognition_source_has_safe_unsent_supersession_and_delivered_reuse():
 src=(R/'company/die-agents/hermes/production-cognition/production_cognition_tick.py').read_text();assert "p.parent/'superseded'" in src;assert 'if delivered:' in src;assert 'run_or_reuse_transport' in src;assert 'E_REQUEST_IDENTITY_DRIFT' in src;assert 'E_REQUEST_IMMUTABLE_DRIFT' not in src
def test_runtime_requirements_are_pinned_minimum_set():
 rows=(R/'company/factory-asset/requirements-runtime.txt').read_text().splitlines();assert rows==['Pillow==11.3.0','jsonschema==4.25.1','PyPDF2==3.0.1']