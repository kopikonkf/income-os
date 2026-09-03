import json
from datetime import date, timedelta
from pathlib import Path
import jsonschema

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=json.loads((ROOT/'company/factory-asset/registries/marketplace-delivery-evidence.v1.json').read_text(encoding='utf-8'))
REGISTRY=json.loads((ROOT/'company/factory-asset/registries/marketplace-delivery-profiles.v1.json').read_text(encoding='utf-8'))
SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/marketplace-delivery-profile.schema.json').read_text(encoding='utf-8'))

def test_registry_validates_against_schema():
    jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(REGISTRY)

def test_profiles_compile_exact_delivery_and_unknowns_from_fa003():
    source={p['platform_id']:p for p in EVIDENCE['platforms']}
    compiled={p['platform_id']:p for p in REGISTRY['profiles']}
    assert set(compiled)==set(source)
    for platform_id, evidence in source.items():
        assert compiled[platform_id]['delivery']==evidence['delivery']
        assert compiled[platform_id]['unknown_or_conflicting']==evidence.get('unknown_or_conflicting',[])
        assert compiled[platform_id]['evidence_status']==evidence['evidence_status']

def test_unknown_handling_is_fail_closed():
    source={p['platform_id']:p for p in EVIDENCE['platforms']}
    for profile in REGISTRY['profiles']:
        expected='EVIDENCE_PINNED' if source[profile['platform_id']]['compatibility_disposition']=='EVIDENCE_PINNED' else 'COMPATIBILITY_UNKNOWN'
        assert profile['profile_state']==expected
    assert {p['platform_id'] for p in REGISTRY['profiles'] if p['profile_state']=='COMPATIBILITY_UNKNOWN'}=={'DREAMSTIME','123RF','VECTEEZY'}

def test_freshness_is_deterministic_from_observation_date():
    observed=date.fromisoformat(EVIDENCE['observed_at'])
    cutoff=observed-timedelta(days=180)
    assert REGISTRY['compiled_from']['freshness_cutoff']==cutoff.isoformat()
    for profile in REGISTRY['profiles']:
        for src in profile['source_freshness']:
            if src['source_date'] is None:
                assert src['freshness']=='UNDATED'
            elif date.fromisoformat(src['source_date']) < cutoff:
                assert src['freshness']=='STALE_DATED'
            else:
                assert src['freshness']=='CURRENT_DATED'

def test_no_profile_claims_compatibility_pass():
    raw=json.dumps(REGISTRY,sort_keys=True)
    assert 'COMPATIBILITY_PASS' not in raw
    assert 'SUPPORTED' not in raw
