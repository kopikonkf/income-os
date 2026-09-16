import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'

def graph():
    return json.loads(GRAPH.read_text(encoding='utf-8'))

def test_v1_and_v2_browser_engines_remain_separate():
    g=graph(); by={t['id']:t for t in g['tasks']}
    assert by['FA-337']['status']=='READY'
    assert by['FA-337']['track']=='V1_BROWSER_LIFECYCLE'
    text=by['FA-337']['acceptance']
    assert 'without merging the two production engines' in text
    assert 'Factory Asset V2 lifecycle semantics' in text
    assert 'MUXIA/Hermes' in text

def test_v1_lifecycle_is_job_scoped_and_founder_visible():
    g=graph(); by={t['id']:t for t in g['tasks']}
    assert by['FA-338']['depends_on']==['FA-337']
    assert by['FA-338']['status']=='BLOCKED'
    assert 'COLD -> SPAWN_HEADFUL -> WORK -> DURABLE_TERMINAL -> CLOSE -> COLD' in by['FA-338']['acceptance']
    assert by['FA-339']['depends_on']==['FA-338']
    assert 'DISPLAY :12' in by['FA-339']['acceptance']
    assert 'Read-only VNC remains optional' in by['FA-339']['acceptance']
    assert by['FA-340']['depends_on']==['FA-339']
    assert 'without Permission denied surprises' in by['FA-340']['acceptance']
