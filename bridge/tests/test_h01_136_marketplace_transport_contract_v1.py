from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import importlib.util
import inspect
import json
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company" / "company-os" / "die-h01"
MODULE_PATH = H01 / "engineering" / "marketplace_transport_contract.py"
SCHEMA_PATH = H01 / "contracts" / "h01-marketplace-transport.v1.schema.json"
FIXTURE_PATH = H01 / "fixtures" / "h01-136" / "submission-ready-entry.synthetic.json"
RECEIPT_FIXTURE_PATH = H01 / "fixtures" / "h01-136" / "transport-receipt.synthetic.json"

SPEC = importlib.util.spec_from_file_location("h01_136_marketplace_transport", MODULE_PATH)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


PREPARED_AT = "2026-09-13T16:00:00Z"
ATTEMPT_1 = "2026-09-13T16:00:00Z"
ATTEMPT_2 = "2026-09-13T16:02:00Z"
ATTEMPT_3 = "2026-09-13T16:10:00Z"


@contextmanager
def _raises(expected: type[BaseException], match: str | None = None):
    try:
        yield
    except expected as exc:
        if match is not None:
            assert match in str(exc), f"{match!r} not found in {exc!r}"
    else:
        raise AssertionError(f"expected {expected.__name__}")


def _entry() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _manifest() -> dict:
    entry = _entry()
    return {
        "schema": "die.h01.marketplace-delivery-package.v1",
        "marketplace": entry["marketplace"],
        "semantic_asset_id": entry["semantic_asset_id"],
        "submission_eligible": True,
        "compatibility": {"status": "COMPATIBLE", "result": "PASS"},
        "rights_signal": {"result": "PASS"},
        "founder_qc": "PASS",
        "artifacts": [
            {
                "target": entry["files"][0]["path"],
                "sha256": entry["files"][0]["sha256"],
                "bytes": entry["files"][0]["bytes"],
            }
        ],
        "sidecar_metadata": {
            "path": "files/metadata.json",
            "sha256": entry["files"][1]["sha256"],
            "bytes": entry["files"][1]["bytes"],
        },
        "login_action": "NONE",
        "upload_action": "NONE",
        "submission_action": "NONE",
        "publication_action": "NONE",
        "spend_action": "NONE",
    }


def _contract(tmp_path: Path):
    store = MOD.ReceiptStore(tmp_path / "receipts")
    return MOD.LocalTransportContract(store), store


def _prepare(tmp_path: Path):
    contract, store = _contract(tmp_path)
    receipt = contract.prepare(_entry(), prepared_at=PREPARED_AT)
    return contract, store, receipt


def test_schema_and_synthetic_fixture_are_valid() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    fixture = _entry()
    assert fixture["schema"] == "die.h01.submission-ready-entry.v1"
    assert fixture["action"] == "NONE"


def test_manifest_and_submission_ready_entry_share_content_identity(tmp_path: Path) -> None:
    contract, store = _contract(tmp_path)
    first = contract.prepare(_manifest(), prepared_at=PREPARED_AT)
    replay = contract.prepare(_entry(), prepared_at="2026-09-13T17:00:00Z")
    assert replay == first
    assert MOD.normalize_source(_manifest())["package_digest"] == MOD.normalize_source(_entry())["package_digest"]
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 1
    assert store.load(first["receipt_id"]) == first


def test_exact_replay_is_idempotent_and_changed_payload_is_blocked(tmp_path: Path) -> None:
    contract, store, first = _prepare(tmp_path)
    replay = contract.prepare(_entry(), prepared_at="2026-09-13T16:30:00Z")
    assert replay == first
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 1

    changed = _entry()
    changed["files"][0]["sha256"] = "d" * 64
    with _raises(MOD.DuplicateSubmissionError, match="DUPLICATE_SCOPE_CONFLICT"):
        contract.prepare(changed, prepared_at=PREPARED_AT)
    assert store.load(first["receipt_id"])["state"] == "PREPARED"


def test_concurrent_prepare_has_one_durable_scope_winner(tmp_path: Path) -> None:
    contract, _ = _contract(tmp_path)
    sources = [_entry() for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(
            pool.map(
                lambda source: contract.prepare(source, prepared_at=PREPARED_AT),
                sources,
            )
        )
    assert len({receipt["receipt_id"] for receipt in receipts}) == 1
    assert len(list((tmp_path / "receipts").glob("H01-136-*.json"))) == 1

    changed_contract, _ = _contract(tmp_path / "changed")
    changed_sources = []
    for digit in "01234567":
        source = _entry()
        source["files"][0]["sha256"] = digit * 64
        changed_sources.append(source)

    def attempt(source: dict) -> str:
        try:
            changed_contract.prepare(source, prepared_at=PREPARED_AT)
            return "CREATED"
        except MOD.DuplicateSubmissionError:
            return "DUPLICATE"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, changed_sources))
    assert outcomes.count("CREATED") == 1
    assert outcomes.count("DUPLICATE") == 7
    assert len(list((tmp_path / "changed" / "receipts").glob("H01-136-*.json"))) == 1


def test_source_fields_fail_closed_before_receipt_creation(tmp_path: Path) -> None:
    contract, _ = _contract(tmp_path)
    invalid = _entry()
    invalid["semantic_asset_id"] = "invalid asset id"
    with _raises(MOD.TransportContractError, match="SOURCE_IDENTITY_INVALID"):
        contract.prepare(invalid, prepared_at=PREPARED_AT)

    invalid = _entry()
    invalid["files"][0]["bytes"] = "128"
    with _raises(MOD.TransportContractError, match="PACKAGE_FILE_INVALID"):
        contract.prepare(invalid, prepared_at=PREPARED_AT)

    assert list((tmp_path / "receipts").glob("H01-136-*.json")) == []
    corrupt = tmp_path / "receipts" / f"H01-136-{'f' * 32}.json"
    corrupt.write_text("not-json", encoding="utf-8")
    with _raises(MOD.ReceiptStoreError, match="RECEIPT_READ_FAILED"):
        contract.prepare(_entry(), prepared_at=PREPARED_AT)


def test_retry_classification_backoff_and_exhaustion_are_bounded(tmp_path: Path) -> None:
    contract, _, receipt = _prepare(tmp_path)
    with _raises(MOD.InvalidTransitionError, match="TIMESTAMP_REGRESSION"):
        contract.record_synthetic_dispatch(
            receipt["receipt_id"],
            outcome="TIMEOUT",
            observed_at="2026-09-13T15:59:59Z",
        )
    receipt = contract.record_synthetic_dispatch(receipt["receipt_id"], outcome="TIMEOUT", observed_at=ATTEMPT_1)
    assert receipt["state"] == "RETRYABLE_FAILED"
    assert receipt["attempt_count"] == 1
    assert receipt["retry"]["classification"] == "TRANSIENT_TIMEOUT"
    assert receipt["retry"]["retry_count"] == 1
    assert receipt["retry"]["next_retry_at"] == ATTEMPT_2

    with _raises(MOD.InvalidTransitionError, match="BACKOFF_NOT_ELAPSED"):
        contract.record_synthetic_dispatch(receipt["receipt_id"], outcome="RATE_LIMITED", observed_at=ATTEMPT_1)

    receipt = contract.record_synthetic_dispatch(receipt["receipt_id"], outcome="RATE_LIMITED", observed_at=ATTEMPT_2)
    assert receipt["state"] == "RETRYABLE_FAILED"
    assert receipt["attempt_count"] == 2
    assert receipt["retry"]["retry_count"] == 2
    assert receipt["retry"]["next_retry_at"] == ATTEMPT_3

    receipt = contract.record_synthetic_dispatch(receipt["receipt_id"], outcome="REMOTE_5XX", observed_at=ATTEMPT_3)
    assert receipt["state"] == "TERMINAL_FAILED"
    assert receipt["attempt_count"] == 3
    assert receipt["retry"]["classification"] == "RETRIES_EXHAUSTED"
    assert receipt["retry"]["retryable"] is False
    assert receipt["failure"]["code"] == "RETRIES_EXHAUSTED"

    other_contract, _, other = _prepare(tmp_path / "clock")
    with _raises(MOD.InvalidTransitionError, match="TIMESTAMP_REGRESSION"):
        other_contract.record_synthetic_dispatch(
            other["receipt_id"],
            outcome="TIMEOUT",
            observed_at="2026-09-13T15:59:59Z",
        )


def test_non_retryable_outcome_is_terminal(tmp_path: Path) -> None:
    contract, _, receipt = _prepare(tmp_path)
    receipt = contract.record_synthetic_dispatch(
        receipt["receipt_id"], outcome="POLICY_REJECTED", observed_at=ATTEMPT_1, detail="synthetic policy fixture"
    )
    assert receipt["state"] == "TERMINAL_FAILED"
    assert receipt["retry"]["classification"] == "NO_RETRY"
    assert receipt["failure"] == {"code": "PROVIDER_POLICY_REJECTED", "detail": "synthetic policy fixture"}


def test_moderation_receipt_preserves_opaque_references_and_feedback(tmp_path: Path) -> None:
    contract, _, receipt = _prepare(tmp_path)
    receipt = contract.record_synthetic_dispatch(
        receipt["receipt_id"],
        outcome="REMOTE_ACCEPTED",
        observed_at=ATTEMPT_1,
        remote_reference="opaque-remote-ref-001",
        remote_status="received",
    )
    assert receipt["state"] == "REMOTE_ACCEPTED"
    receipt = contract.record_synthetic_moderation(
        receipt["receipt_id"],
        status="REJECTED",
        observed_at="2026-09-13T16:05:00Z",
        moderation_reference="opaque-moderation-ref-001",
        feedback=[{"code": "METADATA_INVALID", "detail": "synthetic fixture"}],
    )
    assert receipt["state"] == "REJECTED"
    assert receipt["moderation"]["status"] == "REJECTED"
    assert receipt["moderation"]["moderation_reference"] == "opaque-moderation-ref-001"
    assert receipt["moderation"]["feedback"][0]["code"] == "METADATA_INVALID"
    assert receipt["moderation"]["feedback"][0]["learning_target"] == "METADATA"
    assert [row["to"] for row in receipt["state_history"]] == [
        "PREPARED",
        "DISPATCHING",
        "REMOTE_ACCEPTED",
        "MODERATION_PENDING",
        "REJECTED",
    ]
    with _raises(MOD.InvalidTransitionError, match="TERMINAL_RECEIPT_IMMUTABLE"):
        contract.record_synthetic_moderation(receipt["receipt_id"], status="ACCEPTED", observed_at="2026-09-13T16:06:00Z")


def test_receipt_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    contract, store, receipt = _prepare(tmp_path)
    receipt = contract.record_synthetic_dispatch(
        receipt["receipt_id"],
        outcome="REMOTE_ACCEPTED",
        observed_at=ATTEMPT_1,
        remote_reference="opaque-remote-ref-001",
        remote_status="received",
    )
    receipt = contract.record_synthetic_moderation(
        receipt["receipt_id"],
        status="ACCEPTED",
        observed_at="2026-09-13T16:05:00Z",
        moderation_reference="opaque-moderation-ref-001",
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(receipt))
    assert errors == []
    serialized = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path = tmp_path / "receipts" / f"{receipt['receipt_id']}.json"
    assert path.read_bytes() == serialized
    assert store.load(receipt["receipt_id"]) == receipt
    expected = json.loads(RECEIPT_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert receipt == expected


def test_source_secrets_and_external_action_locks_fail_closed(tmp_path: Path) -> None:
    contract, _ = _contract(tmp_path)
    leaked = _entry()
    leaked["api_key"] = "not-a-real-key"
    with _raises(MOD.TransportContractError, match="SECRET_FIELD_FORBIDDEN"):
        contract.prepare(leaked, prepared_at=PREPARED_AT)

    actionful = _entry()
    actionful["action"] = "SUBMIT"
    with _raises(MOD.TransportContractError, match="EXTERNAL_ACTION_NOT_ALLOWED"):
        contract.prepare(actionful, prepared_at=PREPARED_AT)

    receipt = contract.prepare(_entry(), prepared_at=PREPARED_AT)
    assert receipt["authority"] == {
        "gate": "FOUNDER_APPROVAL_REQUIRED_BEFORE_EXTERNAL_ACTION",
        "founder_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
        "external_action_performed": False,
        "credential_accessed": False,
    }
    assert set(receipt["actions"].values()) == {"NONE"}


def test_module_has_no_external_transport_import_or_callable_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert imports.isdisjoint({"requests", "socket", "subprocess", "urllib", "http"})
    public_names = set(dir(MOD.LocalTransportContract))
    assert not public_names.intersection({"login", "upload", "submit", "publish", "spend"})


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        if inspect.signature(test).parameters:
            with tempfile.TemporaryDirectory() as directory:
                test(Path(directory))
        else:
            test()
    print(f"H01-136 focused tests: {len(tests)}/{len(tests)} PASS")
