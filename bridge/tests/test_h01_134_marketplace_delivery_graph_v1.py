import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company/company-os/die-h01/die-h01-task-graph.v1.json'
def test_h01_134_done_and_nonpublishing():
    by={x['id']:x for x in json.loads(GRAPH.read_text())['tasks']}; t=by['H01-134']
    assert t['status']=='DONE'
    assert t['authority']=='ARCHITECT'
    assert t['depends_on']==['H01-105']
    assert 'login' in t['acceptance'].lower()
    assert 'submission_eligible=false' in t['result']
