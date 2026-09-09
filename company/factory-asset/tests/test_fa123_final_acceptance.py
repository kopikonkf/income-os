from __future__ import annotations

import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[3]
BASE = R / 'company/factory-asset'


def _json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_fa123_receipt_and_linux_evidence_are_done_pass_and_hash_bound():
    receipt = _json(BASE / 'receipts/FA-123-downstream-capacity.receipt.json')
    evidence_path = BASE / 'fixtures/scale/FA-123-downstream-capacity-evidence.json'
    evidence = _json(evidence_path)
    assert receipt['task_id'] == 'FA-123'
    assert receipt['status'] == 'DONE' and receipt['result'] == 'PASS'
    assert evidence['task_id'] == 'FA-123' and evidence['result'] == 'PASS'
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == receipt['linux_evidence']['evidence_sha256']
    assert receipt['technical_qa_capacity']['passed'] == 100
    assert receipt['distinctness_capacity']['pairwise_comparisons'] == 4950
    assert receipt['package_capacity']['readiness_passed'] == 100
    assert receipt['package_capacity']['composition_passed'] == 100
    assert receipt['automated_backlog_model']['modeled_automated_backlog_per_day_at_100'] == 0


def test_fa123_preserves_founder_qc_truth_boundary_without_fake_sampling_authority():
    receipt = _json(BASE / 'receipts/FA-123-downstream-capacity.receipt.json')
    qc = receipt['founder_qc_model']
    assert qc['current_policy_sampling_rate'] == 1.0
    assert qc['required_founder_touches_per_day_at_target'] == 100
    assert qc['measured_founder_review_capacity_per_day'] is None
    assert qc['human_capacity_status'] == 'EXTERNAL_UNPROVEN'
    assert qc['sampling_policy_changed'] is False
    assert all(row['authority_status'] == 'CURRENT_POLICY' if row['sampling_rate'] == 1.0 else row['authority_status'] == 'INFORMATIONAL_NOT_AUTHORIZED' for row in qc['informational_sampling_scenarios'])
    truth = receipt['truth_boundaries']
    assert truth['provider_calls_performed'] is False
    assert truth['synthetic_capacity_fixtures_counted_as_production_masters'] is False
    assert truth['submission_authorized'] is False
    assert truth['publication_authorized'] is False


def test_task_graph_marks_fa123_done_and_unlocks_only_fa124_ready_boundary():
    graph = _json(BASE / 'task-graph-v1.json')
    by = {row['id']: row for row in graph['tasks']}
    assert by['FA-123']['status'] == 'DONE'
    assert by['FA-123']['depends_on'] == ['FA-122']
    assert 'PASS:' in by['FA-123']['result']
    assert by['FA-124']['status'] in {'READY','IN_PROGRESS','DONE'}
    assert by['FA-124']['depends_on'] == ['FA-123']
    assert by['FA-124']['authority'] == 'FOUNDER_REQUIRED_FOR_LIVE_LOAD'
    assert by['FA-124']['status']=='DONE' or 'Founder' in by['FA-124']['result']
