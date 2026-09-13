import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company/company-os/die-h01/die-h01-task-graph.v1.json'

def test_h01_114_is_read_only_gallery_followup_after_h01_108():
    g=json.loads(GRAPH.read_text()); by={x['id']:x for x in g['tasks']}; t=by['H01-114']
    assert t['status']=='BLOCKED'
    assert t['authority']=='ARCHITECT'
    assert t['depends_on']==['H01-108']
    assert 'postproduction/preview.webp' in t['acceptance']
    assert 'existing read-only Founder QC Gallery' in t['acceptance']
    assert 'No complex SVG/vector viewer' in t['acceptance']
