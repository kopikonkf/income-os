from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from income_os_bridge.submission_adapter_contract import SubmissionAdapterContract
from income_os_bridge.submission_dry_run import compose_submission_dry_run, sha256_json
from income_os_bridge.submission_reconciliation import build_idempotency_key, decide_submission_attempt

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
AUTHORITY_SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-authority.v1.schema.json"
SESSION_SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-session-boundary.v1.schema.json"


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _inputs() -> tuple[dict, dict, dict]:
    metadata = {
        "schema": "die.asset.metadata.v1",
        "title": "Isolated shopping bag for packing customer orders",
        "description": "Generic isolated ecommerce packing bag asset.",
        "keywords": ["shopping bag", "packing", "customer order", "ecommerce"],
        "ai_disclosure": "Generative AI content",
    }
    package = {
        "schema_version": "die.asset.submission-package.v1",
        "package_id": "SUBPKG-SUB001F01",
        "created_at": "2026-09-07T16:00:00Z",
        "mission_id": "MISSION-SUB001F01",
        "asset_id": "ASSET-SUB001F01",
        "artifact_sha256": "a" * 64,
        "qa_receipt_sha256": "b" * 64,
        "qc_receipt_sha256": "c" * 64,
        "blueprint_sha256": "d" * 64,
        "metadata_sha256": sha256_json(metadata),
        "platform_profile_sha256": "e" * 64,
        "route_id": "ROUTE-SUB001F01",
        "initial_route_state": "PREPARED",
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "credentials_embedded": False,
            "mutable_after_seal": False,
        },
    }
    mapping = {
        "schema": "die.asset.metadata-platform-map.v1",
        "platform": "REGRESSION_REFERENCE",
        "profile_id": "QAPROFILE-SUB001F-V1",
        "status": "PASS",
        "mapped_fields": {
            "title": metadata["title"],
            "description": metadata["description"],
            "keywords": metadata["keywords"],
            "ai_disclosure": metadata["ai_disclosure"],
        },
        "failures": [],
        "unknown_requirements": [],
        "semantic_content_invented_by_engine": False,
    }
    return package, metadata, mapping


def _authority(package: dict) -> dict:
    return {
        "schema_version": "die.asset.submission-authority.v1",
        "authority_receipt_id": "SUBAUTH-SUB001F01",
        "package_sha256": sha256_json(package),
        "route_id": package["route_id"],
        "platform_profile_sha256": package["platform_profile_sha256"],
        "decision": "AUTHORIZE_SUBMISSION",
        "authority_class": "FOUNDER_EXPLICIT",
        "issued_at": "2026-09-07T16:00:00Z",
        "expires_at": None,
        "scope": {
            "platform": "REGRESSION_REFERENCE",
            "package_locked": True,
            "route_locked": True,
            "single_submission_attempt": True,
        },
        "credential_boundary": {
            "credentials_embedded": False,
            "credential_material_logged": False,
            "cookie_token_extraction_allowed": False,
            "protection_bypass_allowed": False,
            "implicit_delegation_allowed": False,
        },
    }


def _session(package: dict) -> dict:
    return {
        "schema_version": "die.asset.submission-session-boundary.v1",
        "route_id": package["route_id"],
        "platform": "REGRESSION_REFERENCE",
        "session_state": "READY",
        "session_mode": "EXTERNAL_PROFILE_SESSION",
        "observed_at": "2026-09-07T16:00:00Z",
        "opaque_profile_ref": "profile-reference-only",
        "credential_boundary": {
            "credential_material_present": False,
            "credential_material_persisted_by_die": False,
            "cookie_token_extraction_allowed": False,
            "protection_bypass_allowed": False,
            "session_may_be_recreated_interactively": True,
        },
    }


def _decision(**overrides):
    package, _, _ = _inputs()
    defaults = {
        "pinned_package_sha256": sha256_json(package),
        "pinned_route_id": package["route_id"],
        "observed_package_sha256": sha256_json(package),
        "observed_route_id": package["route_id"],
        "route_state": "AUTHORIZED",
        "current_attempt": 0,
        "proposed_attempt": 1,
        "external_observation": "NOT_CHECKED",
    }
    defaults.update(overrides)
    return decide_submission_attempt(**defaults)


def test_sub001f_missing_or_invalid_authority_fails_closed() -> None:
    package, _, _ = _inputs()
    adapter = SubmissionAdapterContract(
        platform="REGRESSION_REFERENCE",
        adapter_version="v1",
        execution_mode="AUTOMATED_ALLOWED",
        policy_profile_sha256=package["platform_profile_sha256"],
        submit_supported=True,
    )
    with pytest.raises(PermissionError, match="Founder"):
        adapter.assert_submit_path(founder_authorized=False, official_api=False)

    validator = _validator(AUTHORITY_SCHEMA)
    valid = _authority(package)
    validator.validate(valid)

    forged = deepcopy(valid)
    forged["authority_class"] = "IMPLICIT_DELEGATION"
    with pytest.raises(ValidationError):
        validator.validate(forged)

    leaked = deepcopy(valid)
    leaked["token"] = "must-not-enter-canon"
    with pytest.raises(ValidationError):
        validator.validate(leaked)

    denied = deepcopy(valid)
    denied["decision"] = "DENY_SUBMISSION"
    validator.validate(denied)
    assert denied["decision"] != "AUTHORIZE_SUBMISSION"

    mismatched = deepcopy(valid)
    mismatched["route_id"] = "ROUTE-OTHER001"
    validator.validate(mismatched)
    assert mismatched["route_id"] != package["route_id"]


def test_sub001f_duplicate_package_route_is_idempotent_noop() -> None:
    package, _, _ = _inputs()
    package_sha = sha256_json(package)
    first = build_idempotency_key(package_sha256=package_sha, route_id=package["route_id"])
    second = build_idempotency_key(package_sha256=package_sha, route_id=package["route_id"])
    assert first == second

    replay = _decision(current_attempt=1, proposed_attempt=1)
    assert replay.decision == "NOOP_DUPLICATE"
    assert replay.attempt_eligible is False
    assert replay.submission_action_authorized is False


def test_sub001f_retry_ambiguity_requires_review_before_repeat() -> None:
    for observation in ("NOT_CHECKED", "AMBIGUOUS", "UNREACHABLE"):
        result = _decision(current_attempt=1, proposed_attempt=2, external_observation=observation)
        assert result.decision == "STOP_REVIEW"
        assert result.reconciliation_required is True
        assert result.review_required is True
        assert result.attempt_eligible is False
        assert result.submission_action_authorized is False


def test_sub001f_credential_and_session_leakage_is_rejected() -> None:
    package, metadata, mapping = _inputs()
    authority_validator = _validator(AUTHORITY_SCHEMA)
    session_validator = _validator(SESSION_SCHEMA)

    bad_authority = _authority(package)
    bad_authority["credential_boundary"]["credentials_embedded"] = True
    with pytest.raises(ValidationError):
        authority_validator.validate(bad_authority)

    bad_session = _session(package)
    bad_session["credential_boundary"]["credential_material_present"] = True
    with pytest.raises(ValidationError):
        session_validator.validate(bad_session)

    mapping_leak = deepcopy(mapping)
    mapping_leak["mapped_fields"]["session_token"] = "opaque-secret-material"
    with pytest.raises(ValueError, match="credential/session field"):
        compose_submission_dry_run(
            submission_package=package,
            metadata=metadata,
            platform_mapping=mapping_leak,
            artifact_filename="shopping-bag.png",
        )

    metadata_leak = deepcopy(metadata)
    metadata_leak["api_key"] = "opaque-secret-material"
    leaked_package = deepcopy(package)
    leaked_package["metadata_sha256"] = sha256_json(metadata_leak)
    with pytest.raises(ValueError, match="credential/session field"):
        compose_submission_dry_run(
            submission_package=leaked_package,
            metadata=metadata_leak,
            platform_mapping=mapping,
            artifact_filename="shopping-bag.png",
        )


def test_sub001f_unknown_policy_and_operator_paths_block_submit() -> None:
    package, _, _ = _inputs()
    for mode, message in (
        ("BLOCKED_POLICY_UNKNOWN", "policy unknown"),
        ("OPERATOR_REQUIRED", "operator handoff"),
    ):
        adapter = SubmissionAdapterContract(
            platform="REGRESSION_REFERENCE",
            adapter_version="v1",
            execution_mode=mode,
            policy_profile_sha256=package["platform_profile_sha256"],
            submit_supported=True,
        )
        with pytest.raises(PermissionError, match=message):
            adapter.assert_submit_path(founder_authorized=True, official_api=True)
        capability = adapter.capability("submit")
        assert capability["supported_by_adapter"] is False
        assert capability["external_action"] is True
        assert capability["requires_founder_authority"] is True


def test_sub001f_dry_run_stays_side_effect_free_and_non_authorizing() -> None:
    package, metadata, mapping = _inputs()
    result = compose_submission_dry_run(
        submission_package=package,
        metadata=metadata,
        platform_mapping=mapping,
        artifact_filename="shopping-bag.png",
    )
    assert [action["action"] for action in result["planned_actions"]] == [
        "ATTACH_ARTIFACT",
        "APPLY_MAPPED_METADATA",
        "STOP_BEFORE_SUBMISSION",
    ]
    assert all(action["external"] is False for action in result["planned_actions"])
    assert result["authority_boundary"] == {
        "submission_authorized": False,
        "publication_authorized": False,
        "credential_access_required": False,
        "external_action_performed": False,
        "dry_run_only": True,
    }
    serialized = json.dumps(result, sort_keys=True).lower()
    assert "session_token" not in serialized
    assert "api_key" not in serialized


def test_sub001f_reconciliation_conflict_and_ambiguity_fail_closed() -> None:
    package, _, _ = _inputs()
    scope_conflict = _decision(observed_route_id="ROUTE-OTHER001")
    assert scope_conflict.decision == "BLOCK_SCOPE_MISMATCH"
    assert scope_conflict.attempt_eligible is False
    assert scope_conflict.submission_action_authorized is False

    package_conflict = _decision(observed_package_sha256="f" * 64)
    assert package_conflict.decision == "BLOCK_SCOPE_MISMATCH"
    assert package_conflict.submission_action_authorized is False

    ambiguous = _decision(current_attempt=1, proposed_attempt=2, external_observation="AMBIGUOUS")
    assert ambiguous.decision == "STOP_REVIEW"
    assert ambiguous.review_required is True
    assert ambiguous.submission_action_authorized is False

    existing = _decision(current_attempt=1, proposed_attempt=2, external_observation="FOUND_SUBMITTED")
    assert existing.decision == "RECONCILE_NO_SUBMIT"
    assert existing.reconciliation_required is True
    assert existing.attempt_eligible is False
    assert existing.submission_action_authorized is False


def test_sub001f_fail_closed_matrix_never_self_grants_submission_authority() -> None:
    decisions = [
        _decision(route_state="PREPARED"),
        _decision(current_attempt=1, proposed_attempt=1),
        _decision(current_attempt=1, proposed_attempt=3),
        _decision(current_attempt=1, proposed_attempt=2, external_observation="AMBIGUOUS"),
        _decision(current_attempt=1, proposed_attempt=2, external_observation="FOUND_REVIEW_PENDING"),
        _decision(current_attempt=1, proposed_attempt=2, external_observation="NOT_FOUND"),
    ]
    assert {item.decision for item in decisions} >= {
        "BLOCK_ROUTE_STATE",
        "NOOP_DUPLICATE",
        "BLOCK_NON_SEQUENTIAL_ATTEMPT",
        "STOP_REVIEW",
        "RECONCILE_NO_SUBMIT",
        "ALLOW_ATTEMPT",
    }
    assert all(item.submission_action_authorized is False for item in decisions)


def test_sub001f_graph_transition_is_dependency_bounded() -> None:
    tasks = {row["id"]: row for row in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["SUB-001E"]["status"] == "DONE"
    assert tasks["SUB-001F"]["status"] in {"READY", "DONE"}
    if tasks["SUB-001F"]["status"] == "READY":
        assert tasks["SUB-001"]["status"] == "BLOCKED"
    else:
        assert tasks["SUB-001"]["status"] == "READY"
    for marketplace in ("SUB-ADOBEA", "SUB-DREAMSTIMEA", "SUB-123RFA", "SUB-VECTEEZYA", "SUB-MOTIONELEMENTSA"):
        assert tasks[marketplace]["status"] == "BLOCKED"
