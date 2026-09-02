from __future__ import annotations

import json
from pathlib import Path
import pytest
from income_os_bridge.submission_adapter_contract import SubmissionAdapterContract

ROOT=Path(__file__).resolve().parents[2]
SCHEMA=ROOT/'company/schemas/die.asset.submission-adapter.v1.schema.json'
GRAPH=ROOT/'company/muxia-task-graph-v1.json'
DOC=ROOT/'docs/operations/PLATFORM_SUBMISSION_ADAPTER_CONTRACT_V1.md'


def _contract(mode: str, *, submit: bool=True):
    return SubmissionAdapterContract(platform='REFERENCE',adapter_version='v1',execution_mode=mode,policy_profile_sha256='a'*64,submit_supported=submit)


def test_sub001e_schema_declares_exact_execution_modes_and_operations():
    s=json.loads(SCHEMA.read_text(encoding='utf-8'))
    assert s['properties']['execution_mode']['enum']==['AUTOMATED_ALLOWED','OPERATOR_REQUIRED','OFFICIAL_API_ONLY','BLOCKED_POLICY_UNKNOWN']
    assert set(s['properties']['operations']['required'])=={'prepare','submit','reconcile','receipt'}
    b=s['properties']['authority_boundary']['properties']
    assert b['adapter_grants_submission_authority']=={'const':False}
    assert b['credentials_embedded']=={'const':False}
    assert b['policy_may_be_weakened']=={'const':False}


def test_sub001e_unknown_and_operator_modes_block_adapter_submission():
    for mode,msg in [('BLOCKED_POLICY_UNKNOWN','policy unknown'),('OPERATOR_REQUIRED','operator handoff')]:
        with pytest.raises(PermissionError,match=msg): _contract(mode).assert_submit_path(founder_authorized=True,official_api=True)


def test_sub001e_official_api_only_rejects_nonofficial_path():
    c=_contract('OFFICIAL_API_ONLY')
    with pytest.raises(PermissionError,match='official API'): c.assert_submit_path(founder_authorized=True,official_api=False)
    c.assert_submit_path(founder_authorized=True,official_api=True)


def test_sub001e_automation_allowed_still_requires_founder_authority_and_capability():
    with pytest.raises(PermissionError,match='Founder'): _contract('AUTOMATED_ALLOWED').assert_submit_path(founder_authorized=False,official_api=False)
    with pytest.raises(PermissionError,match='not implemented'): _contract('AUTOMATED_ALLOWED',submit=False).assert_submit_path(founder_authorized=True,official_api=False)


def test_sub001e_capability_semantics_keep_external_action_separate():
    c=_contract('AUTOMATED_ALLOWED')
    assert [c.capability(x)['operation'] for x in ['prepare','submit','reconcile','receipt']]==['prepare','submit','reconcile','receipt']
    assert c.capability('prepare')['external_action'] is False
    assert c.capability('submit')['external_action'] is True
    assert c.capability('submit')['requires_founder_authority'] is True


def test_sub001e_doc_and_graph_preserve_policy_and_authority_boundaries():
    d=DOC.read_text(encoding='utf-8')
    for marker in ['must never weaken','BLOCKED_POLICY_UNKNOWN','OPERATOR_REQUIRED','OFFICIAL_API_ONLY','AUTOMATED_ALLOWED','no marketplace login','no cookie/token extraction']:
        assert marker in d
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['SUB-001D']['status']=='DONE'
    assert tasks['SUB-001E']['status'] in {'READY','DONE'}
    assert tasks['SUB-001F']['status'] in {'BLOCKED','READY'}
