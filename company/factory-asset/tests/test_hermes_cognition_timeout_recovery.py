from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
COG = R / 'company/die-agents/hermes/production-cognition/production_cognition_tick.py'
ROUNDTRIP = R / 'company/browser/linux/cognition_roundtrip_core.mjs'

spec = importlib.util.spec_from_file_location('pcog_timeout', COG)
m = importlib.util.module_from_spec(spec)
sys.modules['pcog_timeout'] = m
spec.loader.exec_module(m)


def _state(**kw):
    value = {
        'schema': 'die.production.cognition-state.v1',
        'task_id': 'PRODSEED000113',
        'stage': 'NEED_AUTHOR',
        'author_attempt': 0,
        'review_attempt': 0,
        'revision': 0,
        'history': [],
    }
    value.update(kw)
    return value


def test_author_timeout_advances_bounded_attempt_instead_of_infinite_same_request():
    s = _state()
    r = m.record_transport_timeout(s, stage='NEED_AUTHOR', request_id='COG-PROD_BP_AUTHOR_PRODSEED000113_R00', lane='AUTHOR')
    assert r == {'retryable': True, 'attempt': 1, 'stage': 'NEED_AUTHOR'}
    assert s['author_attempt'] == 1
    assert s['history'][-1]['event'] == 'TRANSPORT_RESPONSE_TIMEOUT'
    assert s['history'][-1]['retryable'] is True


def test_author_timeout_exhaustion_fails_closed_to_founder_boundary():
    s = _state(author_attempt=m.MAX_SEMANTIC_ATTEMPTS - 1)
    r = m.record_transport_timeout(s, stage='NEED_AUTHOR', request_id='COG-PROD_BP_AUTHOR_PRODSEED000113_R02', lane='AUTHOR')
    assert r['retryable'] is False
    assert r['attempt'] == m.MAX_SEMANTIC_ATTEMPTS
    assert s['stage'] == 'WAITING_FOUNDER'


def test_review_timeout_has_bounded_versioned_retry():
    s = _state(stage='NEED_REVIEW')
    r = m.record_transport_timeout(s, stage='NEED_REVIEW', request_id='COG-PROD_BP_REVIEW_PRODSEED000113_R00', lane='REVIEW')
    assert r == {'retryable': True, 'attempt': 1, 'stage': 'NEED_REVIEW'}
    exhausted = _state(stage='NEED_REVIEW', review_attempt=m.MAX_CONTEXT_RETRIES)
    r2 = m.record_transport_timeout(exhausted, stage='NEED_REVIEW', request_id='COG-PROD_BP_REVIEW_PRODSEED000113_R03', lane='REVIEW')
    assert r2['retryable'] is False
    assert exhausted['stage'] == 'WAITING_FOUNDER'


def test_roundtrip_stops_expired_or_timed_out_stale_generating_turn():
    text = ROUNDTRIP.read_text(encoding='utf-8')
    assert 'expiredWhileWaiting=Date.now()>=parseTime(req.expires_at)' in text
    assert "throw new Error('E_RESPONSE_TIMEOUT_STALE_TURN_STOPPED')" in text
    assert "await stop.click({timeout:2500}).catch(()=>{})" in text
    assert text.count('E_RESPONSE_TIMEOUT_STALE_TURN_STOPPED') >= 2


def test_cognition_tick_converts_transport_timeout_to_durable_retry_state():
    text = COG.read_text(encoding='utf-8')
    assert "if not is_response_timeout_error(e):raise" in text
    assert "record_transport_timeout(state,stage=stage,request_id=rid,lane='AUTHOR')" in text
    assert "record_transport_timeout(state,stage=stage,request_id=rid,lane='REVIEW')" in text
    assert "'reason':'E_RESPONSE_TIMEOUT'" in text
