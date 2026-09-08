from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
LIB = R / 'company/factory-asset/lib'
sys.path.insert(0, str(LIB))

from fa123_capacity_model import Fa123CapacityError, run_fa123_capacity_model


def _paths():
    base = R / 'company/factory-asset'
    return {
        'fa122_receipt_path': base / 'receipts/FA-122-20-50-masters-day.receipt.json',
        'fa120_receipt_path': base / 'receipts/FA-120-synthetic-throughput-backpressure.receipt.json',
        'fa137_receipt_path': base / 'receipts/FA-137-metadata-package-readiness.receipt.json',
        'fa205_receipt_path': base / 'receipts/FA-205-founder-qc.receipt.json',
    }


def _small_contract(tmp_path: Path) -> Path:
    src = R / 'company/factory-asset/contracts/fa123-downstream-capacity.v1.json'
    value = json.loads(src.read_text(encoding='utf-8'))
    value['modeled_master_count'] = 8
    value['target_masters_per_day'] = 8
    value['backlog']['automated_arrival_rate_per_day'] = 8
    path = tmp_path / 'contract.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def test_small_capacity_model_exercises_qa_distinctness_package_and_human_boundary(tmp_path):
    result = run_fa123_capacity_model(contract_path=_small_contract(tmp_path), **_paths())
    assert result['result'] == 'PASS'
    assert result['technical_qa']['passed'] == 8
    assert result['distinctness']['pairwise_comparisons'] == 28
    assert result['distinctness']['positive_set_exact_duplicate_count'] == 0
    assert result['distinctness']['positive_set_near_duplicate_pair_count'] == 0
    assert result['distinctness']['exact_duplicate_negative_control_detected'] is True
    assert result['distinctness']['near_duplicate_negative_control_detected'] is True
    assert result['package']['readiness_passed'] == 8
    assert result['package']['composition_passed'] == 8
    assert result['automated_capacity']['modeled_automated_backlog_per_day'] == 0
    assert result['founder_qc']['required_founder_touches_per_day_at_target'] == 8
    assert result['founder_qc']['measured_founder_review_capacity_per_day'] is None
    assert result['founder_qc']['sampling_policy_changed'] is False
    assert result['truth_boundaries']['provider_calls_performed'] is False
    assert result['truth_boundaries']['synthetic_fixtures_counted_as_production_masters'] is False


def test_current_100_day_contract_keeps_founder_qc_at_100_percent():
    contract = json.loads((R / 'company/factory-asset/contracts/fa123-downstream-capacity.v1.json').read_text(encoding='utf-8'))
    assert contract['target_masters_per_day'] == 100
    assert contract['founder_qc']['current_authorized_sampling_rate'] == 1.0
    assert contract['founder_qc']['sampling_scenarios_change_authority'] is False
    assert 0.1 in contract['founder_qc']['informational_sampling_scenarios']


def test_invalid_fa122_input_fails_closed(tmp_path):
    bad = json.loads((R / 'company/factory-asset/receipts/FA-122-20-50-masters-day.receipt.json').read_text(encoding='utf-8'))
    bad['result'] = 'FAIL'
    bad_path = tmp_path / 'fa122.json'
    bad_path.write_text(json.dumps(bad), encoding='utf-8')
    paths = _paths(); paths['fa122_receipt_path'] = bad_path
    try:
        run_fa123_capacity_model(contract_path=_small_contract(tmp_path), **paths)
    except Fa123CapacityError as exc:
        assert exc.code == 'E_FA122_INPUT'
    else:
        raise AssertionError('expected fail-closed FA122 input rejection')
