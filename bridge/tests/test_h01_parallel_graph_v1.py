import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company/company-os/die-h01/die-h01-task-graph.v1.json'
def test_parallel_frontier_and_dependencies():
    by={x['id']:x for x in json.loads(GRAPH.read_text())['tasks']}
    assert by['H01-135']['status']=='READY' and by['H01-135']['depends_on']==['H01-134']
    assert by['H01-136']['status']=='READY' and by['H01-136']['depends_on']==['H01-134']
    assert by['H01-130']['status']=='READY' and by['H01-130']['depends_on']==['H01-101','H01-120']
    assert by['H01-140']['status']=='READY' and by['H01-140']['depends_on']==['H01-114','H01-134']
    assert by['H01-109']['depends_on']==['H01-135','H01-136']
    assert by['H01-141']['depends_on']==['H01-140'] and by['H01-141']['status']=='BLOCKED'
    assert by['H01-142']['depends_on']==['H01-140'] and by['H01-142']['status']=='BLOCKED'
