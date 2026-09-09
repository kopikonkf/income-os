import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ADR=ROOT/'docs/architecture/FACTORY_CONSOLE_V2_ADR.md'
SPEC=ROOT/'company/factory-asset/docs/console/FACTORY_CONSOLE_V2_UI_SPEC.md'
R13=ROOT/'company/factory-asset/receipts/FA-C013-factory-console-production-acceptance.receipt.json'
R14=ROOT/'company/factory-asset/receipts/FA-C014-console-v2-adr.receipt.json'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'

def test_c013_founder_acceptance_preserves_authority_boundaries():
 d=json.load(open(R13));assert d['status']=='DONE' and d['result']=='PASS';assert d['acceptance_basis']['founder_explicit_acceptance'] is True
 b=d['authority_boundaries'];assert b['marketplace_publication_inside_console'] is False and b['provider_dispatch_implied_by_acceptance'] is False and b['scale_100_per_day_authorized'] is False and b['founder_qc_mutation_enabled'] is False

def test_c014_stack_and_wrapper_boundary_are_explicit():
 d=json.load(open(R14));q=d['decisions'];assert d['result']=='PASS';assert q['primary_surface']=='WEB_FIRST_LOOPBACK_CONTROL_PLANE';assert q['frontend']=='TYPESCRIPT_REACT_VITE';assert q['backend']=='PYTHON_LOOPBACK_VERSIONED_JSON_CONTRACTS';assert q['desktop_wrapper']=='OPTIONAL_TAURI_AFTER_FA-C020';assert q['electron']=='REJECTED';assert q['frontend_secret_access'] is False and q['frontend_direct_cdp_access'] is False

def test_clean_room_dense_operator_language_maps_factory_concepts():
 a=ADR.read_text();s=SPEC.read_text()
 for token in ['OPERATE','RUNTIME','ANALYZE','GOVERN','ClusterCard','ProviderSessionCard','StatusPill','EvidenceDrawer','AuthorityBanner']:
  assert token in a or token in s
 assert 'No brand assets' in a and 'Copy 9router component hierarchy' in a
 for route in ['/queue','/assets','/qc','/clusters','/providers','/usage','/economics','/acceptance','/rights']:
  assert route in s

def test_graph_transitions_c013_c014_and_opens_c015():
 d=json.load(open(GRAPH));by={x['id']:x for x in d['tasks']};assert by['FA-C013']['status']=='DONE';assert by['FA-C014']['status']=='DONE';assert by['FA-C015']['status']=='READY';assert set(by['FA-C015']['depends_on'])=={'FA-C014','FA-303'}
