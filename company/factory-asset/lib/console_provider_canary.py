from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from factory_queue import FactoryJobQueue
from provider_original import intake_provider_original

REQUEST_SCHEMA = "die.factory-asset.console-provider-canary-request.v1"
RESULT_SCHEMA = "die.factory-asset.console-provider-canary-result.v1"
CONSOLE_STATE_SCHEMA = "die.factory-asset.console-provider-canary-state.v1"
LINEAGE_SCHEMA = "die.factory-asset.console-provider-canary-lineage.v1"
EXECUTOR_SCHEMA = "die.factory-asset.console-provider-executor.v1"


class ConsoleProviderCanaryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def validate_request(request: dict[str, Any]) -> None:
    required = {
        "schema",
        "task_id",
        "job_id",
        "idempotency_key",
        "asset_type",
        "blueprint_id",
        "semantic_asset_id",
        "prompt",
        "routing_constraint",
        "authority",
    }
    if set(request) != required:
        raise ConsoleProviderCanaryError("E_REQUEST_FIELDS", "request fields must match the canonical envelope")
    if request.get("schema") != REQUEST_SCHEMA or request.get("task_id") != "FA-C010":
        raise ConsoleProviderCanaryError("E_REQUEST_SCHEMA", "FA-C010 request schema/task mismatch")
    if request.get("asset_type") != "PHOTO":
        raise ConsoleProviderCanaryError("E_ASSET_TYPE", "bounded canary accepts PHOTO only")
    if not all(isinstance(request.get(k), str) and request[k].strip() for k in ("job_id", "idempotency_key", "blueprint_id", "semantic_asset_id", "prompt")):
        raise ConsoleProviderCanaryError("E_REQUEST_IDENTITY", "job/idempotency/blueprint/semantic/prompt values are required")
    if len(request["idempotency_key"]) != 64 or any(c not in "0123456789abcdef" for c in request["idempotency_key"]):
        raise ConsoleProviderCanaryError("E_IDEMPOTENCY_KEY", "idempotency key must be lower-case sha256")
    if not (10 <= len(request["prompt"]) <= 4000):
        raise ConsoleProviderCanaryError("E_PROMPT_BOUNDS", "prompt length outside bounded canary range")

    route = request.get("routing_constraint")
    if not isinstance(route, dict) or set(route) != {"allowed_provider_ids", "cluster_id", "transport", "direct_gui_provider_browser_ownership"}:
        raise ConsoleProviderCanaryError("E_ROUTING_CONSTRAINT", "canonical routing constraint required")
    if route.get("cluster_id") not in {"cluster-a", "cluster-b"} or route.get("transport") != "BROWSER_CDP":
        raise ConsoleProviderCanaryError("E_ROUTE_SCOPE", "FA-C010 requires a canonical cluster-a/cluster-b BROWSER_CDP route")
    if route.get("allowed_provider_ids") != ["qwen"]:
        raise ConsoleProviderCanaryError("E_PROVIDER_SCOPE", "bounded acceptance allows only the already-accepted qwen route")
    if route.get("direct_gui_provider_browser_ownership") is not False:
        raise ConsoleProviderCanaryError("E_GUI_OWNERSHIP", "Console may not own provider/browser GUI state")

    authority = request.get("authority")
    expected = {
        "founder_authorized_live_provider_call": True,
        "spend_usd": 0,
        "marketplace_submission_authorized": False,
        "publication_authorized": False,
        "account_creation_or_action_authorized": False,
        "captcha_checkpoint_bypass_authorized": False,
        "credential_cookie_token_session_value_read_authorized": False,
    }
    if authority != expected:
        raise ConsoleProviderCanaryError("E_AUTHORITY", "authority envelope does not match bounded Founder authorization")


def _console_state(queue: FactoryJobQueue, request: dict[str, Any], *, phase: str, route: dict[str, Any] | None = None) -> dict[str, Any]:
    job = queue.get(request["job_id"]).as_dict()
    return {
        "schema": CONSOLE_STATE_SCHEMA,
        "task_id": "FA-C010",
        "source_surface": "FACTORY_CONSOLE",
        "phase": phase,
        "job": job,
        "factory_core_route": route,
        "direct_gui_provider_browser_ownership": False,
        "provider_calls_performed_by_console": False,
        "credential_values_read": False,
        "cookies_or_tokens_read": False,
    }


def _validate_executor_result(executor: dict[str, Any], request: dict[str, Any]) -> tuple[Path, str]:
    if executor.get("schema") != EXECUTOR_SCHEMA or executor.get("result") != "PASS" or executor.get("status") != "SUCCEEDED":
        raise ConsoleProviderCanaryError("E_EXECUTOR_RESULT", "governed provider executor did not return PASS/SUCCEEDED")
    if executor.get("job_id") != request["job_id"] or executor.get("idempotency_key") != request["idempotency_key"]:
        raise ConsoleProviderCanaryError("E_EXECUTOR_IDENTITY", "executor job identity drift")
    route = executor.get("route") or {}
    expected_cluster = request["routing_constraint"]["cluster_id"]
    if (route.get("provider_id"), route.get("cluster_id"), route.get("transport")) != ("qwen", expected_cluster, "BROWSER_CDP"):
        raise ConsoleProviderCanaryError("E_EXECUTOR_ROUTE", "provider/cluster/transport truth mismatch")
    if route.get("browser_owner_action") != "NONE" or route.get("requires_tab_lease") is not True:
        raise ConsoleProviderCanaryError("E_EXECUTOR_OWNERSHIP", "executor must use broker tab lease without browser-owner action")
    commit = executor.get("generation_commit") or {}
    if executor.get("dispatch_committed_count") != 1 or not commit.get("commit_id"):
        raise ConsoleProviderCanaryError("E_GENERATION_COMMIT", "exactly one committed generation is required")
    if any(executor.get(k) is not False for k in ("credential_values_read", "cookies_or_tokens_read", "provider_login_automated", "submission_authorized", "publication_authorized")):
        raise ConsoleProviderCanaryError("E_EXECUTOR_AUTHORITY", "executor crossed a forbidden authority/secret boundary")
    if executor.get("spend_usd") != 0:
        raise ConsoleProviderCanaryError("E_EXECUTOR_SPEND", "zero-spend canary required")
    before = executor.get("broker_before") or {}
    after = executor.get("broker_after") or {}
    if before.get("cluster_id") != expected_cluster or after.get("cluster_id") != expected_cluster:
        raise ConsoleProviderCanaryError("E_BROKER_CLUSTER", f"{expected_cluster} evidence required")
    if before.get("browser_owner_pid") != after.get("browser_owner_pid") or not before.get("browser_owner_pid"):
        raise ConsoleProviderCanaryError("E_BROWSER_OWNER_DRIFT", "broker browser owner changed during Console canary")
    if after.get("active_leases") != 0:
        raise ConsoleProviderCanaryError("E_LEASE_LEAK", "broker tab lease was not released")
    artifact = executor.get("artifact") or {}
    path = Path(str(artifact.get("path") or "")).resolve()
    sha = str(artifact.get("sha256") or "")
    if not path.is_file() or len(sha) != 64 or _sha_file(path) != sha:
        raise ConsoleProviderCanaryError("E_EXECUTOR_ARTIFACT", "provider artifact missing or hash mismatch")
    return path, sha


def _replay_existing(request: dict[str, Any], workspace: Path, final_path: Path) -> dict[str, Any] | None:
    if not final_path.is_file():
        journal = workspace / "provider-attempt.json"
        if journal.is_file():
            try:
                prior = json.loads(journal.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ConsoleProviderCanaryError("E_PRIOR_ATTEMPT_CORRUPT", str(exc)) from exc
            if prior.get("dispatch_committed") is True:
                raise ConsoleProviderCanaryError("E_PRIOR_DISPATCH_COMMITTED", "prior committed dispatch requires manual reconciliation; duplicate generation forbidden")
            raise ConsoleProviderCanaryError("E_PRIOR_ATTEMPT_PRESENT", "prior attempt exists; bounded canary will not auto-retry")
        return None
    prior = json.loads(final_path.read_text(encoding="utf-8"))
    if prior.get("schema") != RESULT_SCHEMA or prior.get("request_sha256") != _sha_json(request) or prior.get("result") != "PASS":
        raise ConsoleProviderCanaryError("E_FINAL_RECEIPT_CONFLICT", "existing final result conflicts with current request")
    master = prior.get("master") or {}
    master_path = Path(str(master.get("path") or "")).resolve()
    if not master_path.is_file() or _sha_file(master_path) != master.get("sha256"):
        raise ConsoleProviderCanaryError("E_FINAL_MASTER_DRIFT", "durable master no longer matches final receipt")
    replay = dict(prior)
    replay["idempotent_replay"] = True
    replay["provider_call_performed"] = False
    replay["replay_reason"] = "FINAL_RECEIPT_AND_MASTER_VERIFIED"
    return replay


def run_console_provider_canary(
    *,
    request: dict[str, Any],
    workspace: str | Path,
    execute_provider: Callable[[dict[str, Any], Path], dict[str, Any]],
) -> dict[str, Any]:
    validate_request(request)
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    final_path = root / "final-result.json"
    replay = _replay_existing(request, root, final_path)
    if replay is not None:
        return replay

    queue = FactoryJobQueue()
    intent = {
        "source_surface": "FACTORY_CONSOLE",
        "task_id": "FA-C010",
        "blueprint_id": request["blueprint_id"],
        "semantic_asset_id": request["semantic_asset_id"],
        "asset_type": request["asset_type"],
        "routing_constraint": request["routing_constraint"],
    }
    queue.submit(job_id=request["job_id"], idempotency_key=request["idempotency_key"], intent=intent)
    _atomic_json(root / "console-state.json", _console_state(queue, request, phase="READY"))
    queue.start(request["job_id"], owner="factory-console-fa-c010", lease_token=_sha_json({"job_id": request["job_id"], "idempotency_key": request["idempotency_key"]}))
    _atomic_json(root / "console-state.json", _console_state(queue, request, phase="RUNNING"))

    executor = execute_provider(request, root)
    artifact_path, provider_sha = _validate_executor_result(executor, request)
    intake = intake_provider_original(
        source_path=artifact_path,
        staging_root=root / "master-staging",
        attempt_id=request["job_id"] + "-provider-original",
        semantic_asset_id=request["semantic_asset_id"],
        blueprint_id=request["blueprint_id"],
        provider_id="qwen",
        expected_sha256=provider_sha,
        declared_mime_type=(executor.get("artifact") or {}).get("mime"),
    )
    staged_path = Path(intake["staged_blob_path"]).resolve()
    if not staged_path.is_file() or _sha_file(staged_path) != provider_sha:
        raise ConsoleProviderCanaryError("E_MASTER_STAGE", "durable staged master verification failed")
    with Image.open(staged_path) as image:
        image.load()
        master_dimensions = [image.width, image.height]
        master_format = image.format

    route = executor["route"]
    queue.succeed(request["job_id"], artifact_sha256=provider_sha)
    state = _console_state(queue, request, phase="SUCCEEDED", route=route)
    state["master_sha256"] = provider_sha
    _atomic_json(root / "console-state.json", state)

    lineage = {
        "schema": LINEAGE_SCHEMA,
        "task_id": "FA-C010",
        "job_id": request["job_id"],
        "idempotency_key": request["idempotency_key"],
        "semantic_asset_id": request["semantic_asset_id"],
        "blueprint_id": request["blueprint_id"],
        "provider": {"provider_id": "qwen", "cluster_id": request["routing_constraint"]["cluster_id"], "transport": "BROWSER_CDP"},
        "generation_commit_id": executor["generation_commit"]["commit_id"],
        "provider_original_sha256": provider_sha,
        "master_sha256": provider_sha,
        "transformation": "NONE",
        "provider_original_immutable": True,
        "master_staging": intake,
    }
    _atomic_json(root / "lineage.json", lineage)

    result = {
        "schema": RESULT_SCHEMA,
        "task_id": "FA-C010",
        "result": "PASS",
        "request_sha256": _sha_json(request),
        "job_id": request["job_id"],
        "idempotency_key": request["idempotency_key"],
        "source_surface": "FACTORY_CONSOLE",
        "factory_core_path": ["FactoryJobQueue", "MultiClusterScheduler", "ClusterAwareProviderRouter", "BrokerTabLease", "GovernedProviderWorker", "ProviderOriginalIntake"],
        "route": route,
        "generation_commit": executor["generation_commit"],
        "dispatch_committed_count": executor["dispatch_committed_count"],
        "provider_call_performed": True,
        "idempotent_replay": False,
        "master": {
            "path": str(staged_path),
            "sha256": provider_sha,
            "bytes": staged_path.stat().st_size,
            "format": master_format,
            "dimensions": master_dimensions,
            "provider_original_exact_copy": True,
        },
        "lineage_path": str(root / "lineage.json"),
        "console_state_path": str(root / "console-state.json"),
        "broker_before": executor["broker_before"],
        "broker_after": executor["broker_after"],
        "direct_gui_provider_browser_ownership": False,
        "credential_values_read": False,
        "cookies_or_tokens_read": False,
        "spend_usd": 0,
        "marketplace_submission_authorized": False,
        "publication_authorized": False,
        "account_creation_or_action_authorized": False,
        "captcha_checkpoint_bypass_authorized": False,
    }
    _atomic_json(final_path, result)
    return result


