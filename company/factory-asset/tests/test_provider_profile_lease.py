import importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
R=Path(__file__).resolve().parents[3]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,R/p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load('pp','company/factory-asset/lib/provider_profile.py'); S=json.loads((R/'company/factory-asset/schemas/provider-profile.schema.json').read_text())
P={"schema":"die.factory-asset.provider-profile.v1","profile_id":"qwen_a","principal_id":"founder_a","provider_id":"qwen","transport_class":"SESSION_API","credential_ref":{"opaque_ref":"opaque://windows/qwen-a"},"enabled":True}
def test_profile_schema_and_opaque_ref():jsonschema.Draft202012Validator(S).validate(P)
def test_raw_secret_fields_rejected():
 x=dict(P);x['password']='secret'
 with pytest.raises(jsonschema.ValidationError):jsonschema.Draft202012Validator(S).validate(x)
def test_one_profile_one_lease_idempotent():
 r=m.ProviderLeaseRegistry();a=r.acquire(token='t1',principal_id='founder_a',profile_id='qwen_a',owner='job1');assert a==r.acquire(token='t1',principal_id='founder_a',profile_id='qwen_a',owner='job1')
 with pytest.raises(m.LeaseError) as e:r.acquire(token='t2',principal_id='founder_a',profile_id='qwen_a',owner='job2')
 assert e.value.code=='PROFILE_ALREADY_LEASED'
def test_cross_profile_principal_rejected():
 r=m.ProviderLeaseRegistry();r.acquire(token='t1',principal_id='founder_a',profile_id='qwen_a',owner='job1')
 with pytest.raises(m.LeaseError) as e:r.acquire(token='t2',principal_id='founder_a',profile_id='gemini_a',owner='job2')
 assert e.value.code=='PRINCIPAL_CROSS_PROFILE_OWNERSHIP'
def test_release_token_guard_and_sanitize():
 r=m.ProviderLeaseRegistry();r.acquire(token='t1',principal_id='founder_a',profile_id='qwen_a',owner='job1')
 with pytest.raises(m.LeaseError):r.release(token='bad',profile_id='qwen_a')
 r.release(token='t1',profile_id='qwen_a');assert r.active('qwen_a') is None;assert 'credential_ref' not in m.sanitize_profile(P)