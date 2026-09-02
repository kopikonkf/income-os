from __future__ import annotations
import importlib.util, sqlite3, sys, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERMES=ROOT/'company/die-agents/hermes'; sys.path.insert(0,str(HERMES))
P=HERMES/'production_tick_preflight.py'; spec=importlib.util.spec_from_file_location('preflight',P); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def db(path:Path):
 c=sqlite3.connect(path); c.execute('create table seeds(id text,canonical_name text,object_class text,existence_type text,category_path text,demand_score real,demand_status text,asset_tier text,risk_score real,status text)'); c.execute("insert into seeds values('SEED-000027','trophy','award','real','Business/Award',0.812,'validated_high','U1-raster',null,'approved')"); c.commit(); c.close()

def state(root:Path,task:str,value:str):
 w=root/task; w.mkdir(parents=True); (w/'PROGRESS.md').write_text(f'# p\n\n- Seed: SEED-000027 (trophy)\n- Family: Business/Award\n- State: {value}\n- Started: 2026-09-02T00:00:00Z\n',encoding='utf-8')

def test_active_card_suppresses_seed_selection(tmp_path:Path):
 d=tmp_path/'atlas.db'; db(d); ws=tmp_path/'ws'; state(ws,'OE008TROPHY001','BLUEPRINT_REQUIRED')
 out=mod.preflight(ws,d); assert out['mode']=='WAITING_COGNITION'; assert out['wakeAgent'] is False; assert out['active_card']['task_id']=='OE008TROPHY001'; assert out['active_card']['execution_surface']=='PRODUCTION_COGNITION_LINE_V1'; assert 'seed_selection' not in out

def test_no_active_card_starts_ranked_seed(tmp_path:Path):
 d=tmp_path/'atlas.db'; db(d); ws=tmp_path/'ws'; ws.mkdir()
 out=mod.preflight(ws,d); assert out['mode']=='START_NEW_SEED'; assert out['seed']['id']=='SEED-000027'

def test_blocking_card_prevents_new_seed(tmp_path:Path):
 d=tmp_path/'atlas.db'; db(d); ws=tmp_path/'ws'; state(ws,'OE008TROPHY001','BLOCKED_PROVIDER_LIMIT')
 out=mod.preflight(ws,d); assert out['mode']=='BLOCKED_ACTIVE_CARD'; assert 'seed_selection' not in out


def test_blocked_active_card_cli_is_valid_script_output_not_script_error(tmp_path:Path):
    d=tmp_path/'atlas.db'; db(d); ws=tmp_path/'ws'; state(ws,'OE008TROPHY001','BLUEPRINT_REQUIRED')
    proc=subprocess.run([sys.executable,str(P),'--workspaces',str(ws),'--db',str(d)],text=True,capture_output=True,check=False)
    assert proc.returncode==0
    assert 'WAITING_COGNITION' in proc.stdout and '"wakeAgent": false' in proc.stdout
