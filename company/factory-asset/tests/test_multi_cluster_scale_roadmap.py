import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'
TAB=ROOT/'company/browser/linux/tab_budget.mjs'
DOC=ROOT/'docs/architecture/FACTORY_WEB_AI_CLUSTER_SCALE_V1.md'

def test_central_cluster_tab_ceiling_is_eight():
    assert 'MAX_TABS_PER_PRINCIPAL = 8' in TAB.read_text()

def test_multi_cluster_and_console_v2_tasks_are_appended():
    g=json.loads(GRAPH.read_text()); by={t['id']:t for t in g['tasks']}
    assert isinstance(g.get('revision'),str) and g['revision']
    for tid in ['FA-299','FA-300','FA-301','FA-302','FA-303','FA-304','FA-305','FA-306','FA-307','FA-308','FA-309','FA-C014','FA-C015','FA-C016','FA-C017','FA-C018','FA-C019','FA-C020','FA-C021','FA-C022']:
        assert tid in by
    assert by['FA-299']['status']=='DONE'
    assert 'FA-118' in by['FA-300']['depends_on']
    assert by['FA-300']['status'] in {'BLOCKED','READY','RUNNING','VERIFYING','DONE'}
    assert by['FA-308']['status']=='DEFERRED' and 'FA-127' in by['FA-308']['depends_on']
    assert by['FA-C022']['status']=='DEFERRED'

def test_architecture_forbids_multi_process_profile_ownership():
    s=DOC.read_text()
    assert 'ONE CHROMIUM OWNER PROCESS' in s
    assert 'does **not** by itself prove simultaneous five-provider production' in s
    assert 'SESSION_API' in s and 'BROWSER_CDP' in s
    assert 'optional Tauri thin shell' in s
