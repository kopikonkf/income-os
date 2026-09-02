from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MOD_PATH=ROOT/'company/die-agents/hermes/production_active_card_resolver.py'
spec=importlib.util.spec_from_file_location('active_card',MOD_PATH); mod=importlib.util.module_from_spec(spec); sys.modules['active_card']=mod; spec.loader.exec_module(mod)

def progress(root:Path,task:str,*lines:str)->Path:
    w=root/task; w.mkdir(parents=True); (w/'PROGRESS.md').write_text('# progress\n\n'+'\n'.join(f'- {x}' for x in lines)+'\n',encoding='utf-8'); return w

def test_trophy_resolves_exact_actor_and_action(tmp_path:Path):
    progress(tmp_path,'OE008TROPHY001','Seed: SEED-000027 (trophy)','Family: Business/Award (object_class: award)','State: BLUEPRINT_REQUIRED','Started: 2026-09-02T00:00:00Z')
    out=mod.resolve_active_card(tmp_path)
    assert out['status']=='CONTINUE_ACTIVE_CARD'
    c=out['active_card']; assert c['task_id']=='OE008TROPHY001'; assert c['state']=='BLUEPRINT_REQUIRED'; assert c['seed_id']=='SEED-000027'; assert c['seed_name']=='trophy'; assert c['required_actor']=='die-lnx-division-001'; assert c['next_action_type']=='OP-REQUEST-DIVISION01-BLUEPRINT'
    assert out['authority_effect']=='NONE' and out['existing_authority_unchanged'] is True

def test_parked_human_gate_does_not_become_active(tmp_path:Path):
    progress(tmp_path,'OLD','Seed: SEED-000001 (old)','State: WAITING_FOUNDER_QC','Started: 2026-09-01T00:00:00Z')
    out=mod.resolve_active_card(tmp_path); assert out['status']=='NO_ACTIVE_CARD'; assert out['parked_card_count']==1

def test_legacy_rights_gate_is_inferred_parked(tmp_path:Path):
    w=progress(tmp_path,'LEGACY','OpenCode executable probe: PASS')
    q=w/'qa'; q.mkdir(); (q/'asset.png').write_bytes(b'png')
    (q/'rights-input.json').write_text(json.dumps({'human_visual_review':{'state':'NOT_REVIEWED','reviewer':'PENDING_FOUNDER'}}),encoding='utf-8')
    out=mod.resolve_active_card(tmp_path); assert out['status']=='NO_ACTIVE_CARD'; assert out['parked_cards'][0]['state']=='WAITING_FOUNDER_QC'; assert out['parked_cards'][0]['state_source']=='LEGACY_RIGHTS_GATE_INFERENCE'

def test_nonproduction_progress_without_state_is_ignored(tmp_path:Path):
    progress(tmp_path,'DIE202-SYNTH','OpenCode executable probe: PASS','Provider/model call: NOT PERFORMED')
    out=mod.resolve_active_card(tmp_path); assert out['status']=='NO_ACTIVE_CARD'; assert out['parked_card_count']==0

def test_unknown_explicit_state_fails_closed(tmp_path:Path):
    progress(tmp_path,'BAD','State: MAGIC_UNKNOWN')
    out=mod.resolve_active_card(tmp_path); assert out['status']=='BLOCKED'; assert out['reason']=='AMBIGUOUS_PRODUCTION_STATE'

def test_oldest_actionable_card_wins_deterministically(tmp_path:Path):
    progress(tmp_path,'B','State: QA_RUNNING','Started: 2026-09-02T02:00:00Z')
    progress(tmp_path,'A','State: BLUEPRINT_REQUIRED','Started: 2026-09-02T01:00:00Z')
    out=mod.resolve_active_card(tmp_path); assert out['active_card']['task_id']=='A'

def test_blocking_provider_limit_blocks_new_seed_compensation(tmp_path:Path):
    progress(tmp_path,'LIMIT','State: BLOCKED_PROVIDER_LIMIT','Started: 2026-09-02T01:00:00Z')
    out=mod.resolve_active_card(tmp_path); assert out['status']=='BLOCKED_ACTIVE_CARD'; assert out['active_card']['next_action_type']=='PROD-RETRY-PROVIDER-CHAIN'
