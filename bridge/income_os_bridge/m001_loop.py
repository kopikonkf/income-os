"""Governed M-001 U1 mission compiler for the Hermes Kanban dispatcher.

The compiler is deliberately one-shot.  Hermes Gateway already owns the
durable 24/7 dispatch loop; this module only validates Founder authority and
materializes an idempotent J1-J8 dependency graph.  It never submits assets,
publishes content, spends money, or writes canonical DIE state.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import urllib.request
from collections.abc import Iterable
from typing import Any

MISSION_ID = "M-001"
REQUEST_SCHEMA = "die.m001.loop-request.v1"
BLUEPRINT_SCHEMA = "die.m001.asset-blueprint.v1"
RUN_SCHEMA = "die.m001.closed-loop-run.v1"
AUTHORIZATION_CLASS = "production_authorization"
AUTHORIZATION_CHOICE = "authorize_u1_validation_batch"
RUN_ID_RE = re.compile(r"^M001-U1-[A-Z0-9][A-Z0-9._-]{1,47}$")
REQUIRED_AUTHORITY_EVIDENCE = {
    "canon_assimilation",
    "division01_worth_making",
    "platform_contract_matrix",
    "proxima_artifact_export",
    "production_engine_rights",
}


class LoopError(RuntimeError):
    """Fail-closed M-001 runner error."""


@dataclasses.dataclass(frozen=True)
class Stage:
    key: str
    title: str
    goal: str
    output: str
    max_runtime: str
    max_retries: int
    proxima_allowed: bool = False


STAGES = (
    Stage(
        "J1",
        "Lock executable Asset Blueprint",
        "Validate and lock the Founder-authorized Asset Blueprint without changing its commercial hypothesis.",
        "LOCK_RECEIPT.json",
        "30m",
        3,
    ),
    Stage(
        "J2",
        "Produce five-asset canary",
        "Delegate one bounded Worker job that produces exactly five distinct canary assets through Proxima.",
        "BATCH_MANIFEST.json",
        "2h",
        1,
        True,
    ),
    Stage(
        "J3",
        "Run canary universal QA",
        "Run deterministic technical and lineage QA plus a bounded visual-review "
        "receipt; stop unless pass rate is at least 80 percent with zero "
        "hard-rights failures.",
        "QA_RECEIPT.json",
        "1h",
        3,
    ),
    Stage(
        "J4",
        "Produce remaining validation waves",
        "After the canary gate passes, delegate resumable production waves until "
        "the authorized total batch size is reached.",
        "BATCH_MANIFEST.json",
        "6h",
        1,
        True,
    ),
    Stage(
        "J5",
        "Run full-batch universal QA",
        "Evaluate the complete authorized batch and emit per-asset routing states "
        "without treating hard failures as residual content.",
        "QA_RECEIPT.json",
        "2h",
        3,
    ),
    Stage(
        "J6",
        "Recover eligible technical failures",
        "Recover only explicitly eligible technical defects at authorized zero "
        "spend; quarantine rights or safety failures and record a no-op when "
        "upscale is unnecessary.",
        "RECOVERY_RECEIPT.json",
        "3h",
        1,
        True,
    ),
    Stage(
        "J7",
        "Build metadata and manual-submission package",
        "Create marketplace-specific metadata drafts and a durable package for "
        "Founder-controlled submission without uploading or publishing.",
        "SUBMISSION_PACKAGE.json",
        "2h",
        3,
    ),
    Stage(
        "J8",
        "Verify U1 production handoff",
        "Mechanically verify J1-J7 receipts and declare only "
        "READY_FOR_MANUAL_SUBMISSION; never claim marketplace submission, "
        "approval, license, or ERVA.",
        "LOOP_RECEIPT.json",
        "30m",
        3,
    ),
)


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LoopError(f"expected JSON object: {path}")
    return value


def _write_json_atomic(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temp.replace(path)


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise LoopError(f"{label} must be a non-empty RFC3339 timestamp")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise LoopError(f"{label} is not an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise LoopError(f"{label} must include a timezone")
    return value


def _load_decision(decisions_path: pathlib.Path, decision_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    try:
        lines = decisions_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise LoopError(f"cannot read canonical decisions: {exc}") from exc
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("decision_id") == decision_id:
            matches.append(row)
    if len(matches) != 1:
        raise LoopError(
            f"decision {decision_id!r} must resolve exactly once in canonical state"
        )
    return matches[0]


def _semantic(decision: dict[str, Any]) -> dict[str, Any]:
    value = decision.get("semantic_object")
    if not isinstance(value, dict):
        raise LoopError("authorization decision lacks semantic_object")
    return value


def validate_authorization(
    request_path: pathlib.Path,
    decisions_path: pathlib.Path,
    *,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Validate the loop request against one State-Manager-committed decision."""

    request = _read_json(request_path)
    if request.get("schema_version") != REQUEST_SCHEMA:
        raise LoopError(f"request schema must be {REQUEST_SCHEMA}")
    run_id = request.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise LoopError("run_id must match M001-U1-[A-Z0-9._-]")
    decision_id = request.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id.startswith("D-"):
        raise LoopError("decision_id must reference one canonical D-* record")
    blueprint_value = request.get("asset_blueprint_path")
    if not isinstance(blueprint_value, str) or not blueprint_value:
        raise LoopError("asset_blueprint_path is required")
    blueprint_path = pathlib.Path(blueprint_value).expanduser().resolve()
    if not blueprint_path.is_file():
        raise LoopError("asset_blueprint_path does not resolve to a file")

    decision = _load_decision(decisions_path, decision_id)
    semantic = _semantic(decision)
    if decision.get("schema_version") != "die.decision.v1":
        raise LoopError("production authorization must use die.decision.v1")
    if not isinstance(decision.get("request_id"), str) or not decision["request_id"]:
        raise LoopError("production authorization lacks a State Manager request_id")
    if decision.get("committed_by") != "die-state-manager":
        raise LoopError(
            "production authorization was not committed by DIE State Manager"
        )
    if decision.get("identity_id") != "founder" or decision.get("decider") != "founder":
        raise LoopError("production authorization must be Founder-authored")
    decision_class = semantic.get("decision_class", decision.get("class"))
    choice = semantic.get("choice", decision.get("choice"))
    if decision_class != AUTHORIZATION_CLASS or choice != AUTHORIZATION_CHOICE:
        raise LoopError("decision is not an M-001 U1 production authorization")
    if semantic.get("mission_id") != MISSION_ID:
        raise LoopError("authorization mission_id must be M-001")
    if semantic.get("run_id") != run_id:
        raise LoopError("request run_id does not match the committed decision")
    if semantic.get("production_authorized") is not True:
        raise LoopError("production_authorized must be true")
    if semantic.get("submission_authorized") is not False:
        raise LoopError("initial runner requires submission_authorized=false")
    if semantic.get("publication_authorized") is not False:
        raise LoopError("initial runner requires publication_authorized=false")
    max_cost = semantic.get("max_cost_usd")
    if (
        not isinstance(max_cost, (int, float))
        or isinstance(max_cost, bool)
        or max_cost != 0
    ):
        raise LoopError("M-001 A0 runner requires max_cost_usd=0")
    batch_size = semantic.get("batch_size")
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 20 <= batch_size <= 40
    ):
        raise LoopError("authorized batch_size must be an integer from 20 to 40")
    if semantic.get("canary_size") != 5:
        raise LoopError("initial canary_size must be exactly 5")
    evidence = semantic.get("authority_evidence")
    evidence_kinds: set[str] = set()
    if isinstance(evidence, list):
        for row in evidence:
            if not isinstance(row, dict):
                continue
            kind = row.get("kind")
            ref = row.get("ref")
            digest = row.get("sha256")
            if (
                isinstance(kind, str)
                and isinstance(ref, str)
                and ref
                and row.get("status") == "VERIFIED"
                and isinstance(digest, str)
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
            ):
                evidence_kinds.add(kind)
    if not REQUIRED_AUTHORITY_EVIDENCE.issubset(evidence_kinds):
        missing = sorted(REQUIRED_AUTHORITY_EVIDENCE - evidence_kinds)
        raise LoopError("authorization evidence missing: " + ", ".join(missing))
    _parse_timestamp(decision.get("ts"), "decision.ts")
    expires_at = _parse_timestamp(
        semantic.get("expires_at"), "authorization.expires_at"
    )
    expiry = dt.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    clock = now or dt.datetime.now(dt.timezone.utc)
    if clock.tzinfo is None:
        raise LoopError("authorization validation clock must include a timezone")
    if clock >= expiry:
        raise LoopError("production authorization is expired")

    blueprint_sha256 = _sha256(blueprint_path)
    if semantic.get("blueprint_sha256") != blueprint_sha256:
        raise LoopError("Asset Blueprint hash does not match the committed decision")
    blueprint = validate_blueprint(_read_json(blueprint_path), semantic)
    return {
        "request": request,
        "decision": decision,
        "authorization": semantic,
        "blueprint": blueprint,
        "blueprint_path": str(blueprint_path),
        "blueprint_sha256": blueprint_sha256,
    }


def validate_blueprint(
    blueprint: dict[str, Any], authorization: dict[str, Any]
) -> dict[str, Any]:
    if blueprint.get("schema_version") != BLUEPRINT_SCHEMA:
        raise LoopError(f"Asset Blueprint schema must be {BLUEPRINT_SCHEMA}")
    if blueprint.get("mission_id") != MISSION_ID:
        raise LoopError("Asset Blueprint mission_id must be M-001")
    for field in ("blueprint_id", "candidate_id", "master_id"):
        if not isinstance(blueprint.get(field), str) or not blueprint[field]:
            raise LoopError(f"Asset Blueprint {field} is required")
    worth = blueprint.get("worth_making")
    if not isinstance(worth, dict):
        raise LoopError("Asset Blueprint worth_making object is required")
    score = worth.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 75:
        raise LoopError("Worth-Making score must be at least 75")
    if worth.get("hard_vetoes_clear") is not True:
        raise LoopError("all Worth-Making hard vetoes must be clear")
    if not isinstance(worth.get("receipt_ref"), str) or not worth["receipt_ref"]:
        raise LoopError("Worth-Making receipt_ref is required")

    buyer = blueprint.get("buyer")
    if not isinstance(buyer, dict) or not buyer.get("job_to_be_done"):
        raise LoopError("buyer.job_to_be_done is required")
    if not isinstance(buyer.get("use_cases"), list) or not buyer["use_cases"]:
        raise LoopError("at least one buyer use case is required")

    production = blueprint.get("production")
    if not isinstance(production, dict):
        raise LoopError("production object is required")
    if production.get("batch_size") != authorization.get("batch_size"):
        raise LoopError("blueprint batch_size must equal the authorized batch_size")
    if production.get("canary_size") != 5:
        raise LoopError("blueprint canary_size must be 5")
    engines = production.get("engines_eligible")
    if not isinstance(engines, list) or not engines:
        raise LoopError("at least one eligible production engine is required")
    refs = production.get("engine_contract_refs")
    if not isinstance(refs, list) or not refs:
        raise LoopError("production engine commercial-rights references are required")
    if (
        not isinstance(production.get("master_prompt"), str)
        or not production["master_prompt"]
    ):
        raise LoopError("production master_prompt is required")
    variations = production.get("semantic_variation_plan")
    if (
        not isinstance(variations, list)
        or len(variations) < authorization["batch_size"]
    ):
        raise LoopError("semantic_variation_plan must cover every authorized asset")

    qa = blueprint.get("qa")
    if not isinstance(qa, dict):
        raise LoopError("qa object is required")
    required_qa = {"rights", "safety", "watermark", "lineage", "technical", "visual"}
    checks = qa.get("universal_checks")
    if not isinstance(checks, list) or not required_qa.issubset(checks):
        raise LoopError(
            "universal_checks must cover rights, safety, watermark, lineage, technical, and visual"
        )
    if (
        not isinstance(qa.get("duplicate_distance_rule"), str)
        or not qa["duplicate_distance_rule"]
    ):
        raise LoopError("qa.duplicate_distance_rule is required")
    technical = qa.get("technical_requirements")
    if not isinstance(technical, dict):
        raise LoopError("qa.technical_requirements is required")
    min_mp = technical.get("min_megapixels")
    if not isinstance(min_mp, (int, float)) or isinstance(min_mp, bool) or min_mp <= 0:
        raise LoopError("qa minimum megapixels must be positive")
    formats = technical.get("allowed_formats")
    if not isinstance(formats, list) or not {
        str(value).upper() for value in formats
    }.intersection({"PNG", "JPEG", "JPG"}):
        raise LoopError("qa allowed_formats must include PNG or JPEG")
    return blueprint


def build_plan(
    validated: dict[str, Any], workspace_root: pathlib.Path
) -> dict[str, Any]:
    auth = validated["authorization"]
    stages = []
    previous: str | None = None
    for stage in STAGES:
        stage_path = workspace_root / stage.key
        stages.append(
            {
                "key": stage.key,
                "title": stage.title,
                "goal": stage.goal,
                "workspace": str(stage_path),
                "output": stage.output,
                "depends_on": [previous] if previous else [],
                "assignee": "income-operator",
                "max_runtime": stage.max_runtime,
                "max_retries": stage.max_retries,
                "proxima_allowed": stage.proxima_allowed,
                "submission_allowed": False,
            }
        )
        previous = stage.key
    core = {
        "schema_version": RUN_SCHEMA,
        "run_id": validated["request"]["run_id"],
        "mission_id": MISSION_ID,
        "decision_id": validated["decision"]["decision_id"],
        "blueprint_id": validated["blueprint"]["blueprint_id"],
        "blueprint_sha256": validated["blueprint_sha256"],
        "batch_size": auth["batch_size"],
        "canary_size": 5,
        "max_cost_usd": 0,
        "submission_authorized": False,
        "publication_authorized": False,
        "dispatch_owner": "Hermes Gateway embedded Kanban dispatcher",
        "dispatch_mode": "event_driven_60s_poll",
        "workspace_root": str(workspace_root),
        "stages": stages,
    }
    fingerprint_payload = json.dumps(core, sort_keys=True, separators=(",", ":"))
    core["plan_sha256"] = hashlib.sha256(fingerprint_payload.encode()).hexdigest()
    return core


def _job_envelope(
    plan: dict[str, Any], stage: dict[str, Any], task_id: str
) -> dict[str, Any]:
    workspace = stage["workspace"]
    constraints = {
        "time_budget_min": _duration_minutes(stage["max_runtime"]),
        "allowed_paths": [workspace],
        "network": "proxima_loopback_only" if stage["proxima_allowed"] else "none",
        "forbidden": [
            "credentials",
            "market submission",
            "publication",
            "spawning workers",
            "writes outside workspace",
            "canonical state writes",
            "strategy changes",
        ],
        "read_only_inputs": [
            str(pathlib.Path(plan["workspace_root"]) / "ASSET_BLUEPRINT.json"),
            *[
                item["workspace"]
                for item in plan["stages"]
                if int(item["key"][1:]) < int(stage["key"][1:])
            ],
        ],
    }
    upstream = next(
        (item for item in plan["stages"] if item["key"] in stage["depends_on"]),
        None,
    )
    return {
        "schema_version": "die.worker-job.v1",
        "task_id": task_id,
        "stage": stage["key"],
        "mission_id": MISSION_ID,
        "goal": stage["goal"],
        "context": {
            "run_id": plan["run_id"],
            "blueprint_id": plan["blueprint_id"],
            "blueprint_sha256": plan["blueprint_sha256"],
            "input_stage": stage["depends_on"][0] if stage["depends_on"] else None,
            "input_workspace": upstream["workspace"] if upstream else None,
            "expected_output": stage["output"],
            "stage_contract": _stage_contract(stage["key"], plan),
        },
        "workspace": workspace,
        "constraints": constraints,
        "acceptance_criteria": _acceptance_criteria(stage, plan),
    }


def _stage_contract(stage_key: str, plan: dict[str, Any]) -> dict[str, Any]:
    contracts = {
        "J1": {
            "blueprint_lock": "exact_sha256",
            "expected_blueprint_sha256": plan["blueprint_sha256"],
        },
        "J2": {
            "asset_count": 5,
            "worker_job_unit": "one asset",
            "max_parallel_workers": 1,
            "manifest_schema": "die.m001.asset-batch.v1",
            "artifact_rule": "one unique asset_id and durable raster file per generation",
            "proxima_endpoint": "http://127.0.0.1:3211/v1/chat/completions",
            "transient_or_browser_only_output": "BLOCKED",
        },
        "J3": {
            "input_stage": "J2",
            "min_assets": 5,
            "max_assets": 5,
            "min_universal_qa_pass_rate": 0.80,
            "max_hard_rights_failures": 0,
        },
        "J4": {
            "total_asset_count": plan["batch_size"],
            "wave_size": 5,
            "max_parallel_workers": 1,
            "manifest_schema": "die.m001.asset-batch.v1",
            "include_verified_canary_assets": True,
            "duplicate_asset_ids_forbidden": True,
        },
        "J5": {
            "input_stage": "J4",
            "min_assets": plan["batch_size"],
            "max_assets": plan["batch_size"],
            "min_universal_qa_pass_rate": 0.80,
            "max_hard_rights_failures": 0,
        },
        "J6": {
            "eligible_routes": ["T1_RECOVERABLE", "RECREATE_TECHNICAL"],
            "forbidden_routes": ["QUARANTINE_RIGHTS", "QUARANTINE_SAFETY"],
            "max_cost_usd": 0,
            "no_candidates_state": "NOT_REQUIRED",
            "re_run_qa_after_transform": True,
        },
        "J7": {
            "submission_status": "PREPARED_NOT_SUBMITTED",
            "submission_authorized": False,
            "target_routes": [
                "Adobe Stock",
                "Dreamstime",
                "123RF",
                "Vecteezy",
                "MotionElements",
            ],
        },
        "J8": {
            "success_state": "READY_FOR_MANUAL_SUBMISSION",
            "not_proven": ["submission", "marketplace_approval", "license", "ERVA"],
        },
    }
    return contracts[stage_key]


def _acceptance_criteria(
    stage: dict[str, Any], plan: dict[str, Any]
) -> list[dict[str, str]]:
    criteria = [
        {
            "id": "AC-1",
            "statement": f"Durable {stage['output']} exists inside the assigned workspace.",
            "verify_with": f"Resolve {stage['workspace']}\\{stage['output']} and hash it.",
        },
        {
            "id": "AC-2",
            "statement": "RESULT.json maps every acceptance criterion to evidence and all tests pass.",
            "verify_with": "python C:\\DIE\\bin\\die_accept.py <workspace> <changed-paths.json>",
        },
        {
            "id": "AC-3",
            "statement": "No submission, publication, credential access, canonical state write, or spend occurred.",
            "verify_with": "Inspect the stage receipt authority_boundary and cost_usd fields.",
        },
    ]
    if stage["key"] in {"J3", "J5"}:
        criteria.append(
            {
                "id": "AC-4",
                "statement": (
                    "Universal QA is executable and records per-asset routes, "
                    "pass rate, and hard-rights failures."
                ),
                "verify_with": (
                    "python C:\\DIE\\bin\\m001_asset_qa.py evaluate "
                    "--manifest <manifest> --output QA_RECEIPT.json"
                ),
            }
        )
    if stage["key"] == "J8":
        criteria.append(
            {
                "id": "AC-4",
                "statement": (
                    "The run verifies as READY_FOR_MANUAL_SUBMISSION and makes "
                    "no claim of external approval or revenue."
                ),
                "verify_with": f"python C:\\DIE\\bin\\m001_loop.py verify-run --run-root {plan['workspace_root']}",
            }
        )
    return criteria


def _duration_minutes(value: str) -> int:
    if value.endswith("m"):
        return int(value[:-1])
    if value.endswith("h"):
        return int(value[:-1]) * 60
    raise LoopError(f"unsupported duration: {value}")


def _card_body(plan: dict[str, Any], stage: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"M-001 U1 closed-loop stage {stage['key']} for run {plan['run_id']}.",
            (
                "Act only as Hermes orchestrator: read JOB.json, delegate only "
                "bounded Worker Contract jobs sequentially, then verify artifacts "
                "and evidence before completing this card."
            ),
            (
                "Do not produce the artifact in the Hermes context. Do not alter "
                "the Asset Blueprint commercial hypothesis."
            ),
            f"Workspace: {stage['workspace']}",
            f"Expected durable output: {stage['output']}",
            f"Upstream dependency: {', '.join(stage['depends_on']) or 'none'}",
            "Proxima is allowed only through a bounded Worker when JOB.json says proxima_loopback_only.",
            "Submission/publication are forbidden; J8 may declare only READY_FOR_MANUAL_SUBMISSION.",
            "On retry, resume from PROGRESS.md and existing artifacts. Never duplicate an existing asset_id.",
        ]
    )


def _parse_json_output(output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise LoopError("Hermes CLI did not return a JSON object")


class HermesClient:
    """Minimal subprocess adapter around the installed Hermes Kanban CLI."""

    def __init__(self, binary: str | None = None):
        self.binary = binary or os.environ.get("HERMES_BIN") or shutil.which("hermes")
        if not self.binary:
            raise LoopError("Hermes binary not found; set HERMES_BIN")

    def _run(self, arguments: Iterable[str]) -> str:
        command = [self.binary, *list(arguments)]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-2000:]
            raise LoopError(f"Hermes CLI failed ({completed.returncode}): {detail}")
        return completed.stdout

    def doctor(self) -> dict[str, Any]:
        config = self._run(["config", "get", "kanban"])
        gateway = self._run(["gateway", "status", "--deep"])
        if "dispatch_in_gateway: true" not in config:
            raise LoopError("Hermes gateway Kanban dispatch is not enabled")
        if "Gateway process running" not in gateway:
            raise LoopError("Hermes income-operator gateway is not running")
        interval_match = re.search(r"dispatch_interval_seconds:\s*(\d+)", config)
        if not interval_match:
            raise LoopError("Hermes dispatch interval is not observable")
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:3211/v1/models", timeout=10
            ) as response:
                models = json.loads(response.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LoopError(f"Proxima model registry is unavailable: {exc}") from exc
        model_rows = models.get("data") if isinstance(models, dict) else None
        if not isinstance(model_rows, list) or not any(
            isinstance(row, dict)
            and row.get("id") == "chatgpt"
            and row.get("status") == "enabled"
            for row in model_rows
        ):
            raise LoopError("Proxima chatgpt production engine is not enabled")
        return {
            "dispatch_in_gateway": True,
            "dispatch_interval_seconds": int(interval_match.group(1)),
            "gateway_running": True,
            "proxima_chatgpt_enabled": True,
        }

    def create(
        self, plan: dict[str, Any], stage: dict[str, Any], parent_id: str | None
    ) -> dict[str, Any]:
        arguments = [
            "kanban",
            "create",
            f"M-001 {stage['key']}: {stage['title']}",
            "--body",
            _card_body(plan, stage),
            "--assignee",
            stage["assignee"],
            "--workspace",
            f"dir:{stage['workspace']}",
            "--idempotency-key",
            f"{plan['run_id']}:{stage['key']}:v1",
            "--max-runtime",
            stage["max_runtime"],
            "--max-retries",
            str(stage["max_retries"]),
            "--created-by",
            "m001-closed-loop-runner",
            "--initial-status",
            "blocked",
            "--json",
        ]
        if parent_id:
            arguments.extend(["--parent", parent_id])
        return _parse_json_output(self._run(arguments))

    def unblock(self, task_ids: list[str]) -> None:
        self._run(
            [
                "kanban",
                "unblock",
                *task_ids,
                "--reason",
                "M-001 runner materialization complete; dependency gates enforce J1-J8 order",
            ]
        )


def materialize(
    validated: dict[str, Any],
    workspace_root: pathlib.Path,
    client: HermesClient,
) -> dict[str, Any]:
    """Create the blocked DAG, persist job envelopes, then release dispatch."""

    workspace_root = workspace_root.resolve()
    plan = build_plan(validated, workspace_root)
    run_path = workspace_root / "RUN.json"
    if run_path.exists():
        existing = _read_json(run_path)
        if existing.get("plan_sha256") != plan["plan_sha256"]:
            raise LoopError("workspace already belongs to a different M-001 plan")
        if existing.get("materialization_status") == "DISPATCHABLE":
            return existing

    doctor = client.doctor()
    workspace_root.mkdir(parents=True, exist_ok=True)
    blueprint_copy = workspace_root / "ASSET_BLUEPRINT.json"
    source_blueprint = pathlib.Path(validated["blueprint_path"])
    if (
        blueprint_copy.exists()
        and _sha256(blueprint_copy) != validated["blueprint_sha256"]
    ):
        raise LoopError("existing workspace Asset Blueprint hash mismatch")
    if not blueprint_copy.exists():
        shutil.copyfile(source_blueprint, blueprint_copy)

    task_ids: dict[str, str] = {}
    parent_id: str | None = None
    for stage in plan["stages"]:
        stage_path = pathlib.Path(stage["workspace"])
        stage_path.mkdir(parents=True, exist_ok=True)
        card = client.create(plan, stage, parent_id)
        task = card.get("task", card)
        task_id = task.get("id") if isinstance(task, dict) else None
        if not isinstance(task_id, str) or not task_id:
            raise LoopError(f"Hermes did not return a task id for {stage['key']}")
        task_ids[stage["key"]] = task_id
        job = _job_envelope(plan, stage, task_id)
        _write_json_atomic(stage_path / "JOB.json", job)
        progress = stage_path / "PROGRESS.md"
        if not progress.exists():
            progress.write_text(
                f"# {stage['key']} progress\n\nStatus: not-started\n",
                encoding="utf-8",
                newline="\n",
            )
        parent_id = task_id

    record = dict(plan)
    record.update(
        {
            "materialization_status": "BLOCKED_PENDING_RELEASE",
            "task_ids": task_ids,
            "runtime_doctor": doctor,
        }
    )
    _write_json_atomic(run_path, record)
    client.unblock(list(task_ids.values()))
    record["materialization_status"] = "DISPATCHABLE"
    record["released_at"] = dt.datetime.now(dt.timezone.utc).isoformat(
        timespec="seconds"
    )
    _write_json_atomic(run_path, record)
    return record


def verify_run(
    run_root: pathlib.Path, output_path: pathlib.Path | None = None
) -> dict[str, Any]:
    """Mechanically verify the J1-J7 handoff without claiming an external event."""

    run_root = run_root.resolve()
    run = _read_json(run_root / "RUN.json")
    if run.get("schema_version") != RUN_SCHEMA:
        raise LoopError("RUN.json schema mismatch")
    required = {
        "J1": "LOCK_RECEIPT.json",
        "J2": "BATCH_MANIFEST.json",
        "J3": "QA_RECEIPT.json",
        "J4": "BATCH_MANIFEST.json",
        "J5": "QA_RECEIPT.json",
        "J6": "RECOVERY_RECEIPT.json",
        "J7": "SUBMISSION_PACKAGE.json",
    }
    hashes: dict[str, str] = {}
    values: dict[str, dict[str, Any]] = {}
    for stage, filename in required.items():
        path = run_root / stage / filename
        values[stage] = _read_json(path)
        hashes[f"{stage}/{filename}"] = _sha256(path)

    if values["J1"].get("blueprint_sha256") != run.get("blueprint_sha256"):
        raise LoopError("J1 lock receipt does not match the authorized blueprint")
    for stage in ("J2", "J4"):
        manifest = values[stage]
        if manifest.get("schema_version") != "die.m001.asset-batch.v1":
            raise LoopError(f"{stage} batch manifest schema mismatch")
        if manifest.get("blueprint_id") != run.get("blueprint_id"):
            raise LoopError(f"{stage} batch manifest blueprint mismatch")
    j2_assets = values["J2"].get("assets")
    if not isinstance(j2_assets, list) or len(j2_assets) != 5:
        raise LoopError("J2 must contain exactly five canary assets")
    j4_assets = values["J4"].get("assets")
    if not isinstance(j4_assets, list) or len(j4_assets) != run.get("batch_size"):
        raise LoopError("J4 manifest does not contain the authorized asset count")
    j4_ids = [row.get("asset_id") for row in j4_assets if isinstance(row, dict)]
    if len(j4_ids) != len(j4_assets) or any(not value for value in j4_ids):
        raise LoopError("J4 contains an asset without a stable asset_id")
    if len(set(j4_ids)) != len(j4_ids):
        raise LoopError("J4 contains duplicate asset IDs")
    if values["J3"].get("source_manifest_sha256") != hashes["J2/BATCH_MANIFEST.json"]:
        raise LoopError("J3 QA is not bound to the J2 canary manifest")
    if values["J5"].get("source_manifest_sha256") != hashes["J4/BATCH_MANIFEST.json"]:
        raise LoopError("J5 QA is not bound to the J4 full-batch manifest")

    qa = values["J5"]
    if qa.get("batch_state") != "PASS":
        raise LoopError("full-batch universal QA has not passed")
    total = qa.get("total_assets")
    if (
        not isinstance(total, int)
        or not 20 <= total <= 40
        or total != run.get("batch_size")
    ):
        raise LoopError("full-batch QA asset count does not match authorization")
    if qa.get("pass_rate", 0) < 0.80:
        raise LoopError("full-batch universal QA pass rate is below 80 percent")
    if qa.get("hard_rights_failures") != 0:
        raise LoopError("hard-rights failures prevent U1 handoff")
    routes = qa.get("routes")
    if not isinstance(routes, list) or len(routes) != total:
        raise LoopError("full-batch QA lacks one route per asset")
    pass_asset_ids = [
        row.get("asset_id")
        for row in routes
        if isinstance(row, dict) and row.get("route") == "T1_PASS"
    ]
    if len(pass_asset_ids) != qa.get("pass_count") or any(
        not value for value in pass_asset_ids
    ):
        raise LoopError("full-batch QA pass_count does not match routed assets")

    recovery = values["J6"]
    if recovery.get("status") not in {"COMPLETE", "NOT_REQUIRED"}:
        raise LoopError("J6 recovery receipt is not complete")
    cost = recovery.get("cost_usd")
    if (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or cost > run.get("max_cost_usd", 0)
    ):
        raise LoopError("recovery cost exceeds Founder authorization")
    package = values["J7"]
    if package.get("submission_status") != "PREPARED_NOT_SUBMITTED":
        raise LoopError("J7 must remain PREPARED_NOT_SUBMITTED")
    if package.get("submission_authorized") is not False:
        raise LoopError("J7 cannot authorize marketplace submission")
    if package.get("submission_receipts") not in (None, []):
        raise LoopError(
            "submission receipts are forbidden inside the U1 production runner"
        )
    package_asset_ids = package.get("asset_ids")
    if not isinstance(package_asset_ids, list) or set(package_asset_ids) != set(
        pass_asset_ids
    ):
        raise LoopError("J7 package must contain every and only T1_PASS asset")

    receipt = {
        "schema_version": "die.m001.closed-loop-receipt.v1",
        "run_id": run["run_id"],
        "mission_id": MISSION_ID,
        "status": "READY_FOR_MANUAL_SUBMISSION",
        "completed_scope": "ideation_blueprint_production_qa_recovery_metadata_handoff",
        "not_proven": ["submission", "marketplace_approval", "license", "ERVA"],
        "submission_authorized": False,
        "publication_authorized": False,
        "cost_usd": cost,
        "total_assets": total,
        "universal_qa_pass_rate": qa["pass_rate"],
        "input_hashes": hashes,
        "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    destination = output_path or (run_root / "J8" / "LOOP_RECEIPT.json")
    try:
        destination.resolve().relative_to(run_root)
    except ValueError as exc:
        raise LoopError("J8 receipt must stay inside the run workspace") from exc
    _write_json_atomic(destination, receipt)
    return receipt
