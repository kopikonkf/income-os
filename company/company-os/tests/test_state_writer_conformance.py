import importlib.util, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SPEC=importlib.util.spec_from_file_location("writer_conformance", ROOT/"bin"/"die_state_writer_conformance.py")
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

def test_current_repo_has_one_global_physical_writer():
    result=M.validate(ROOT)
    assert result["status"]=="PASS", result
    assert result["canonical_state_writer"]=="die-state-manager"
    assert result["sole_physical_writer_count"]==1
    assert result["unauthorized_global_store_writers"]==[]
    assert {x["store"] for x in result["global_store_write_findings"]} >= {"state/EVENTS.jsonl","state/DECISIONS.jsonl"}

def test_competing_global_store_writer_fails(tmp_path):
    shutil.copytree(ROOT,tmp_path/"repo",dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
    evil=tmp_path/"repo"/"bin"/"bad_writer.py"
    evil.write_text('from pathlib import Path\nSTATE=Path("state")\np=STATE/"EVENTS.jsonl"\nwith open(p,"a",encoding="utf-8") as f:f.write("x")\n',encoding='utf-8')
    result=M.validate(tmp_path/"repo")
    assert result["status"]=="FAIL"
    assert "E_COMPETING_GLOBAL_STORE_WRITER" in result["errors"]

def test_second_registry_writer_fails(tmp_path):
    shutil.copytree(ROOT,tmp_path/"repo",dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
    p=tmp_path/"repo"/"company"/"identity-registry.json"; d=json.loads(p.read_text(encoding='utf-8'))
    d['services'].append({'id':'second-writer','sole_physical_writer':True})
    p.write_text(json.dumps(d),encoding='utf-8')
    result=M.validate(tmp_path/"repo")
    assert result["status"]=="FAIL"
    assert "E_SOLE_WRITER_REGISTRY" in result["errors"]

def test_factory_adapter_is_same_logical_writer():
    result=M.validate(ROOT)
    assert result['factory_domain']['logical_writer']=='die-state-manager'
    assert result['factory_domain']['writer_token']=='DIE_STATE_MANAGER'
