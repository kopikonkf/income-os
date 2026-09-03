import importlib.util, json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'company/factory-asset/lib/vectorizability.py';s=importlib.util.spec_from_file_location('vector_gate',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
CASES=json.loads((ROOT/'company/factory-asset/fixtures/vectorizability/cases.v1.json').read_text())['cases']
def test_all_vector_gate_fixtures_are_deterministic_and_expected():
 for row in CASES:
  one=m.classify_vectorizability(row['evidence']);two=m.classify_vectorizability(row['evidence'])
  assert one==two;assert one.state==row['expected'];assert one.reason_codes
def test_photorealistic_is_not_vectorizable():
 row=next(x for x in CASES if x['id']=='photo');d=m.classify_vectorizability(row['evidence']);assert 'PHOTOREALISTIC_INPUT' in d.reason_codes
def test_complex_input_fails_with_evidence():
 row=next(x for x in CASES if x['id']=='complex-illustration');d=m.classify_vectorizability(row['evidence']);assert {'COLOR_COMPLEXITY_EXCEEDED','EDGE_COMPLEXITY_EXCEEDED','PATH_COUNT_EXCEEDED'}<=set(d.reason_codes)
def test_trace_requires_explicit_authorization():
 e=next(x for x in CASES if x['id']=='simple-silhouette')['evidence'].copy();e['raster_trace_allowed']=False;d=m.classify_vectorizability(e);assert d.state=='NOT_VECTORIZABLE';assert 'TRACE_NOT_AUTHORIZED' in d.reason_codes
def test_missing_evidence_fails_closed():
 with pytest.raises(m.VectorGateInputError):m.classify_vectorizability({'source_representation':'RASTER_PIXELS'})