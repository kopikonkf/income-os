from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CORE=ROOT/'company/browser/linux/cognition_roundtrip_core.mjs'

def test_subject_spec_action_is_allowed_by_cognition_transport():
    s=CORE.read_text(encoding='utf-8')
    assert "'PRODUCTION_SUBJECT_SPEC_AUTHOR'" in s
    assert "if(!ALLOWED_ACTIONS.has(v.action_type)) throw new Error('E_ACTION')" in s
