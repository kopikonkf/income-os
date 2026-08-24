from __future__ import annotations

import hashlib
import io
import json
import pathlib
import struct
import zlib

import pytest
from income_os_bridge import m001_asset_qa, m001_loop


def _write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _blueprint(batch_size: int = 20) -> dict:
    return {
        "schema_version": m001_loop.BLUEPRINT_SCHEMA,
        "mission_id": "M-001",
        "blueprint_id": "M001-BP-UTIL-001",
        "candidate_id": "CAND-UTIL-001",
        "master_id": "MASTER-13",
        "buyer": {
            "job_to_be_done": "illustrate ordinary household utility",
            "use_cases": ["editorial layout", "small-business explainer"],
        },
        "worth_making": {
            "score": 82,
            "confidence": "medium",
            "hard_vetoes_clear": True,
            "receipt_ref": "SNAP-WORTH-001",
        },
        "production": {
            "batch_size": batch_size,
            "canary_size": 5,
            "engines_eligible": ["chatgpt"],
            "engine_contract_refs": ["ENGINE-CONTRACT-001"],
            "master_prompt": "Produce one commercially useful unbranded utility illustration.",
            "semantic_variation_plan": [f"utility-{i:02d}" for i in range(batch_size)],
        },
        "qa": {
            "universal_checks": [
                "rights",
                "safety",
                "watermark",
                "lineage",
                "technical",
                "visual",
            ],
            "technical_requirements": {
                "min_megapixels": 3,
                "allowed_formats": ["PNG", "JPEG"],
            },
            "duplicate_distance_rule": "exact duplicates forbidden; semantic distance reviewed",
        },
    }


def _authority_files(tmp_path: pathlib.Path, **semantic_overrides):
    blueprint_path = tmp_path / "ASSET_BLUEPRINT.json"
    _write_json(blueprint_path, _blueprint())
    blueprint_hash = hashlib.sha256(blueprint_path.read_bytes()).hexdigest()
    semantic = {
        "decision_class": "production_authorization",
        "choice": "authorize_u1_validation_batch",
        "mission_id": "M-001",
        "run_id": "M001-U1-TEST01",
        "production_authorized": True,
        "submission_authorized": False,
        "publication_authorized": False,
        "max_cost_usd": 0,
        "batch_size": 20,
        "canary_size": 5,
        "blueprint_sha256": blueprint_hash,
        "authority_evidence": [
            {
                "kind": kind,
                "ref": f"evidence/{kind}.json",
                "status": "VERIFIED",
                "sha256": "b" * 64,
            }
            for kind in sorted(m001_loop.REQUIRED_AUTHORITY_EVIDENCE)
        ],
        "expires_at": "2099-08-25T00:00:00+00:00",
    }
    semantic.update(semantic_overrides)
    decision = {
        "schema_version": "die.decision.v1",
        "request_id": "REQ-M001-U1-TEST01",
        "ts": "2026-08-24T10:00:00+00:00",
        "decision_id": "D-0099",
        "class": "production_authorization",
        "choice": "authorize_u1_validation_batch",
        "decider": "founder",
        "identity_id": "founder",
        "committed_by": "die-state-manager",
        "semantic_object": semantic,
    }
    decisions_path = tmp_path / "DECISIONS.jsonl"
    decisions_path.write_text(json.dumps(decision) + "\n", encoding="utf-8")
    request_path = tmp_path / "REQUEST.json"
    _write_json(
        request_path,
        {
            "schema_version": m001_loop.REQUEST_SCHEMA,
            "run_id": "M001-U1-TEST01",
            "decision_id": "D-0099",
            "asset_blueprint_path": str(blueprint_path),
        },
    )
    return request_path, decisions_path


def test_authorization_and_plan_are_fail_closed_and_j1_to_j8(tmp_path):
    request, decisions = _authority_files(tmp_path)
    validated = m001_loop.validate_authorization(request, decisions)
    plan = m001_loop.build_plan(validated, tmp_path / "run")

    assert [stage["key"] for stage in plan["stages"]] == [f"J{i}" for i in range(1, 9)]
    assert plan["stages"][0]["depends_on"] == []
    assert plan["stages"][-1]["depends_on"] == ["J7"]
    assert plan["submission_authorized"] is False
    assert plan["dispatch_owner"] == "Hermes Gateway embedded Kanban dispatcher"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"max_cost_usd": 1}, "max_cost_usd=0"),
        ({"submission_authorized": True}, "submission_authorized=false"),
        ({"authority_evidence": []}, "authorization evidence missing"),
        ({"expires_at": "2020-01-01T00:00:00+00:00"}, "authorization is expired"),
    ],
)
def test_authorization_rejects_spend_submission_and_missing_gates(
    tmp_path, override, message
):
    request, decisions = _authority_files(tmp_path, **override)
    with pytest.raises(m001_loop.LoopError, match=message):
        m001_loop.validate_authorization(request, decisions)


class FakeHermes:
    def __init__(self):
        self.created = []
        self.unblocked = []
        self.doctor_calls = 0

    def doctor(self):
        self.doctor_calls += 1
        return {
            "dispatch_in_gateway": True,
            "dispatch_interval_seconds": 60,
            "gateway_running": True,
        }

    def create(self, plan, stage, parent_id):
        task_id = f"t_{stage['key'].lower()}"
        self.created.append((stage["key"], parent_id, stage["max_retries"]))
        return {"task": {"id": task_id}}

    def unblock(self, task_ids):
        self.unblocked.append(task_ids)


def test_materializer_is_idempotent_and_releases_only_after_all_jobs_exist(tmp_path):
    request, decisions = _authority_files(tmp_path)
    validated = m001_loop.validate_authorization(request, decisions)
    client = FakeHermes()
    run_root = tmp_path / "run"

    first = m001_loop.materialize(validated, run_root, client)
    second = m001_loop.materialize(validated, run_root, client)

    assert first == second
    assert first["materialization_status"] == "DISPATCHABLE"
    assert len(client.created) == 8
    assert client.created[0] == ("J1", None, 3)
    assert client.created[1] == ("J2", "t_j1", 1)
    assert client.unblocked == [[f"t_j{i}" for i in range(1, 9)]]
    assert client.doctor_calls == 1
    assert all((run_root / f"J{i}" / "JOB.json").is_file() for i in range(1, 9))
    j2 = json.loads((run_root / "J2" / "JOB.json").read_text(encoding="utf-8"))
    assert j2["constraints"]["network"] == "proxima_loopback_only"
    assert "market submission" in j2["constraints"]["forbidden"]


def test_hermes_doctor_proves_dispatcher_and_proxima_without_production_prompt(
    monkeypatch,
):
    client = object.__new__(m001_loop.HermesClient)
    client.binary = "hermes"

    def fake_run(arguments):
        if arguments[:3] == ["config", "get", "kanban"]:
            return "dispatch_in_gateway: true\ndispatch_interval_seconds: 60\n"
        if arguments[:2] == ["gateway", "status"]:
            return "Gateway process running (PID: 1)"
        raise AssertionError(arguments)

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(client, "_run", fake_run)
    monkeypatch.setattr(
        m001_loop.urllib.request,
        "urlopen",
        lambda *args, **kwargs: Response(
            json.dumps({"data": [{"id": "chatgpt", "status": "enabled"}]}).encode()
        ),
    )

    assert client.doctor() == {
        "dispatch_in_gateway": True,
        "dispatch_interval_seconds": 60,
        "gateway_running": True,
        "proxima_chatgpt_enabled": True,
    }


def test_hermes_json_parser_tolerates_provider_banner():
    result = m001_loop._parse_json_output('provider banner\n{"task":{"id":"t_j1"}}\n')
    assert result["task"]["id"] == "t_j1"


def _png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _asset(
    workspace: pathlib.Path, asset_id: str, *, rights="CLEAR", include_visual=True
):
    asset_path = workspace / f"assets/{asset_id}.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(_png(10, 10))
    reviews = {}
    for name in ("rights", "safety", "watermark", "lineage", "technical", "visual"):
        if name == "visual" and not include_visual:
            continue
        evidence = workspace / f"evidence/{asset_id}-{name}.json"
        _write_json(evidence, {"review": name})
        reviews[name] = {
            "state": rights if name == "rights" else "PASS",
            "evidence_ref": str(evidence.relative_to(workspace)).replace("\\", "/"),
        }
    return {
        "asset_id": asset_id,
        "blueprint_id": "BP-1",
        "candidate_id": "C-1",
        "master_id": "MASTER-13",
        "engine": "chatgpt",
        "generated_at": "2026-08-24T10:00:00Z",
        "source_path": str(asset_path.relative_to(workspace)).replace("\\", "/"),
        "source_sha256": hashlib.sha256(asset_path.read_bytes()).hexdigest(),
        "prompt_hash": "a" * 64,
        "reviews": reviews,
    }


def _manifest(workspace: pathlib.Path, assets: list[dict]) -> pathlib.Path:
    path = workspace / "BATCH_MANIFEST.json"
    _write_json(
        path,
        {
            "schema_version": m001_asset_qa.MANIFEST_SCHEMA,
            "batch_id": "BATCH-1",
            "blueprint_id": "BP-1",
            "candidate_id": "C-1",
            "master_id": "MASTER-13",
            "technical_requirements": {
                "min_megapixels": 0.0001,
                "allowed_formats": ["PNG"],
            },
            "assets": assets,
        },
    )
    return path


def test_qa_engine_passes_structurally_valid_reviewed_asset(tmp_path):
    asset = _asset(tmp_path, "A-1")
    receipt = m001_asset_qa.evaluate_manifest(
        _manifest(tmp_path, [asset]), tmp_path, min_assets=1, max_assets=1
    )

    assert receipt["batch_state"] == "PASS"
    assert receipt["pass_rate"] == 1.0
    assert receipt["routes"][0]["route"] == "T1_PASS"


def test_qa_engine_quarantines_rights_and_blocks_missing_visual_review(tmp_path):
    rights_asset = _asset(tmp_path, "A-RIGHTS", rights="FAIL")
    rights = m001_asset_qa.evaluate_manifest(
        _manifest(tmp_path, [rights_asset]), tmp_path, min_assets=1, max_assets=1
    )
    assert rights["batch_state"] == "FAIL"
    assert rights["hard_rights_failures"] == 1
    assert rights["routes"][0]["route"] == "QUARANTINE_RIGHTS"

    review_asset = _asset(tmp_path, "A-REVIEW", include_visual=False)
    review = m001_asset_qa.evaluate_manifest(
        _manifest(tmp_path, [review_asset]), tmp_path, min_assets=1, max_assets=1
    )
    assert review["batch_state"] == "BLOCKED_REVIEW"
    assert review["routes"][0]["route"] == "REVIEW_REQUIRED"


def test_qa_engine_recreates_corrupt_raster(tmp_path):
    asset = _asset(tmp_path, "A-CORRUPT")
    source = tmp_path / asset["source_path"]
    source.write_bytes(b"not-a-png")
    asset["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = m001_asset_qa.evaluate_manifest(
        _manifest(tmp_path, [asset]), tmp_path, min_assets=1, max_assets=1
    )
    assert receipt["batch_state"] == "FAIL"
    assert receipt["routes"][0]["route"] == "RECREATE_TECHNICAL"


def test_verify_run_stops_at_manual_submission_boundary(tmp_path):
    run_root = tmp_path / "run"
    _write_json(
        run_root / "RUN.json",
        {
            "schema_version": m001_loop.RUN_SCHEMA,
            "run_id": "M001-U1-TEST01",
            "blueprint_id": "BP-1",
            "blueprint_sha256": "c" * 64,
            "batch_size": 20,
            "max_cost_usd": 0,
        },
    )
    _write_json(
        run_root / "J1" / "LOCK_RECEIPT.json",
        {"blueprint_sha256": "c" * 64},
    )
    j2_path = run_root / "J2" / "BATCH_MANIFEST.json"
    _write_json(
        j2_path,
        {
            "schema_version": m001_asset_qa.MANIFEST_SCHEMA,
            "blueprint_id": "BP-1",
            "assets": [{"asset_id": f"A-{index:02d}"} for index in range(5)],
        },
    )
    _write_json(
        run_root / "J3" / "QA_RECEIPT.json",
        {"source_manifest_sha256": hashlib.sha256(j2_path.read_bytes()).hexdigest()},
    )
    j4_path = run_root / "J4" / "BATCH_MANIFEST.json"
    _write_json(
        j4_path,
        {
            "schema_version": m001_asset_qa.MANIFEST_SCHEMA,
            "blueprint_id": "BP-1",
            "assets": [{"asset_id": f"A-{index:02d}"} for index in range(20)],
        },
    )
    pass_ids = [f"A-{index:02d}" for index in range(16)]
    _write_json(
        run_root / "J5" / "QA_RECEIPT.json",
        {
            "source_manifest_sha256": hashlib.sha256(j4_path.read_bytes()).hexdigest(),
            "batch_state": "PASS",
            "total_assets": 20,
            "pass_count": 16,
            "pass_rate": 0.8,
            "hard_rights_failures": 0,
            "routes": [
                {
                    "asset_id": f"A-{index:02d}",
                    "route": "T1_PASS" if index < 16 else "T1_RECOVERABLE",
                }
                for index in range(20)
            ],
        },
    )
    _write_json(
        run_root / "J6" / "RECOVERY_RECEIPT.json",
        {"status": "NOT_REQUIRED", "cost_usd": 0},
    )
    _write_json(
        run_root / "J7" / "SUBMISSION_PACKAGE.json",
        {
            "submission_status": "PREPARED_NOT_SUBMITTED",
            "submission_authorized": False,
            "submission_receipts": [],
            "asset_ids": pass_ids,
        },
    )

    receipt = m001_loop.verify_run(run_root)
    assert receipt["status"] == "READY_FOR_MANUAL_SUBMISSION"
    assert receipt["not_proven"] == [
        "submission",
        "marketplace_approval",
        "license",
        "ERVA",
    ]
    assert (run_root / "J8" / "LOOP_RECEIPT.json").is_file()


def test_runtime_canon_uses_gateway_dispatch_not_a_production_cron():
    root = pathlib.Path(__file__).resolve().parents[2]
    operations = (root / "docs/operations/M001_CLOSED_LOOP_RUNNER_V1.md").read_text(
        encoding="utf-8"
    )
    company_brain = (root / "COMPANY_BRAIN.md").read_text(encoding="utf-8")
    hermes = (root / "IDENTITY/hermes-operator/AGENTS.md").read_text(encoding="utf-8")

    assert "No production cron and no second daemon are added." in operations
    assert "Hermes Gateway Kanban dispatcher" in operations
    assert "J8 stops at `READY_FOR_MANUAL_SUBMISSION`" in hermes
    assert (
        "M-001 production is event-driven, not production-cron-driven" in company_brain
    )
    assert "Proxima is used only by a bounded Worker in J2, J4" in hermes
