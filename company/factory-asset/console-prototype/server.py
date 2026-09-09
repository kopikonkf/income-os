from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
from copy import deepcopy
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs,urlparse

STATIC_ROOT = Path(__file__).resolve().parent


def _resolve_factory_root(static_root: Path = STATIC_ROOT) -> Path:
    candidates = []
    try:
        candidates.append(static_root.parents[2])
    except IndexError:
        pass
    candidates.append(static_root.parent)
    for candidate in candidates:
        marker = candidate / "company/factory-asset/lib/blueprint_compiler.py"
        if marker.is_file():
            return candidate
    raise RuntimeError(
        "Factory Console runtime support tree not found. Expected company/factory-asset/lib under repository root or mirror root."
    )


ROOT = _resolve_factory_root()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


compiler = _load_module("factory_console_blueprint_compiler", ROOT / "company/factory-asset/lib/blueprint_compiler.py")
identity = _load_module("factory_console_asset_identity", ROOT / "company/factory-asset/lib/asset_identity.py")
factory_queue = _load_module("factory_console_factory_queue", ROOT / "company/factory-asset/lib/factory_queue.py")
console_contract = _load_module("factory_console_contract", ROOT / "company/factory-asset/lib/console_contract.py")
capacity_ledger = _load_module("factory_console_capacity_ledger", ROOT / "company/factory-asset/lib/capacity_ledger.py")
policy_gate = _load_module("factory_console_policy_gate", ROOT / "company/factory-asset/lib/policy_gate.py")
provider_router = _load_module("factory_console_provider_router", ROOT / "company/factory-asset/lib/provider_router.py")
observability = _load_module("factory_console_observability", ROOT / "company/factory-asset/lib/observability.py")
provider_dashboard = _load_module("factory_console_provider_dashboard", ROOT / "company/factory-asset/lib/provider_dashboard.py")
factory_core_synthetic = _load_module("factory_console_core_synthetic", ROOT / "company/factory-asset/lib/factory_core_synthetic_acceptance.py")
console_batch_acceptance = _load_module("factory_console_batch_acceptance", ROOT / "company/factory-asset/lib/console_batch_acceptance.py")
production_acceptance = _load_module("factory_console_production_acceptance", ROOT / "company/factory-asset/lib/console_production_acceptance.py")
founder_qc_gallery = _load_module("factory_console_founder_qc_gallery", ROOT / "company/factory-asset/lib/founder_qc_gallery.py")
cluster_topology = _load_module("factory_console_cluster_topology", ROOT / "company/factory-asset/lib/console_cluster_topology.py")

PROVIDER_POLICY_REGISTRY = json.loads((ROOT / "company/factory-asset/registries/provider-policy.v1.json").read_text(encoding="utf-8"))
PROVIDER_DASHBOARD_FIXTURE = json.loads((ROOT / "company/factory-asset/fixtures/provider-dashboard/synthetic-observed.v1.json").read_text(encoding="utf-8"))
OUTPUT_GALLERY_FIXTURE = json.loads((ROOT / "company/factory-asset/fixtures/output-gallery/fa029-actual-canary.v1.json").read_text(encoding="utf-8"))
CLUSTER_REGISTRY = json.loads((ROOT / "company/factory-asset/registries/web-ai-clusters.v1.json").read_text(encoding="utf-8"))
CORE_QUEUE = factory_queue.FactoryJobQueue()
RECONCILIATION_REQUIRED_JOB_IDS: set[str] = set()


class ConsoleRequestError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def compile_blueprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"blueprint", "ui_constraints"}:
        raise ConsoleRequestError("INVALID_COMPILE_ENVELOPE", "expected blueprint and ui_constraints only")
    blueprint = deepcopy(payload["blueprint"])
    ui_constraints = deepcopy(payload["ui_constraints"])
    if not isinstance(blueprint, dict) or not isinstance(ui_constraints, dict):
        raise ConsoleRequestError("INVALID_COMPILE_ENVELOPE", "blueprint/ui_constraints must be objects")
    allowed_ui = {"style_preset", "consistency_preset", "background"}
    unknown = sorted(set(ui_constraints) - allowed_ui)
    if unknown:
        raise ConsoleRequestError("UNSUPPORTED_UI_CONSTRAINT", ",".join(unknown))
    plan = compiler.compile_blueprint(blueprint)
    return {
        "schema": "die.factory-asset.console-compile-preview.v1",
        "result": "PASS",
        "plan": plan,
        "semantic_fingerprint": identity.semantic_fingerprint(blueprint),
        "packaging_fingerprint": identity.packaging_fingerprint(blueprint),
        "ui_constraints": ui_constraints,
        "dispatch_performed": False,
    }


def create_batch_intent(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"compile_preview", "quantity", "label", "ui_constraints"}
    if set(payload) != required:
        raise ConsoleRequestError("INVALID_BATCH_ENVELOPE", "batch envelope fields mismatch")
    preview = payload["compile_preview"]
    if not isinstance(preview, dict) or preview.get("result") != "PASS" or preview.get("schema") != "die.factory-asset.console-compile-preview.v1":
        raise ConsoleRequestError("COMPILED_BLUEPRINT_REQUIRED", "a successful canonical compile preview is required")
    quantity = payload["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 1000:
        raise ConsoleRequestError("BATCH_QUANTITY_OUT_OF_RANGE", "quantity must be 1..1000")
    label = str(payload["label"]).strip()
    if not label or len(label) > 120:
        raise ConsoleRequestError("INVALID_BATCH_LABEL", "label must be 1..120 characters")
    plan = preview["plan"]
    derivative_count = quantity * len(plan.get("derivatives", []))
    return {
        "schema": "die.factory-asset.console-batch-intent.v1",
        "batch_id": "FC-BATCH-PREVIEW-" + preview["semantic_fingerprint"][:12].upper(),
        "label": label,
        "blueprint_id": plan["blueprint_id"],
        "semantic_asset_id": plan["semantic_asset_id"],
        "semantic_fingerprint": preview["semantic_fingerprint"],
        "packaging_fingerprint": preview["packaging_fingerprint"],
        "quantity": quantity,
        "semantic_asset_count": quantity,
        "packaging_derivative_count": derivative_count,
        "ui_constraints": deepcopy(payload["ui_constraints"]),
        "dispatch_authority": "SIMULATED_ONLY",
        "dispatch_performed": False,
    }


def _job_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _seed_queue() -> None:
    if CORE_QUEUE.list():
        return
    rows = [
        ("FCJOB-DEMO-READY", "FABP-SHOPPING_BAG_PHOTO", "FASA-DEMO-PHOTO-READY", "Ready demo"),
        ("FCJOB-DEMO-RUN", "FABP-SHOPPING_BAG_ISOLATED", "FASA-DEMO-ISOLATED-RUN", "Running demo"),
        ("FCJOB-DEMO-PAUSE", "FABP-SHOPPING_BAG_ICON", "FASA-DEMO-ICON-PAUSE", "Paused demo"),
        ("FCJOB-DEMO-RETRY", "FABP-SHOPPING_BAG_PATTERN", "FASA-DEMO-PATTERN-RETRY", "Retry demo"),
    ]
    for job_id, blueprint_id, semantic_id, label in rows:
        CORE_QUEUE.submit(job_id=job_id, idempotency_key=_job_key("seed", job_id), intent={"blueprint_id": blueprint_id, "semantic_asset_id": semantic_id, "label": label, "provider_id": None})
    CORE_QUEUE.start("FCJOB-DEMO-RUN", owner="console-seed", lease_token=_job_key("lease", "run"))
    CORE_QUEUE.start("FCJOB-DEMO-PAUSE", owner="console-seed", lease_token=_job_key("lease", "pause"))
    CORE_QUEUE.pause("FCJOB-DEMO-PAUSE")
    CORE_QUEUE.start("FCJOB-DEMO-RETRY", owner="console-seed", lease_token=_job_key("lease", "retry"))
    CORE_QUEUE.fail("FCJOB-DEMO-RETRY", code="RATE_LIMITED", retryable=True)


def provider_dashboard_state() -> dict[str, Any]:
    try: live = production_acceptance_state()
    except Exception: live = None
    if live and any(row.get("reachable") for row in live["live_pool"]["clusters"]):
        clusters = {row["cluster_id"]: row for row in CLUSTER_REGISTRY["clusters"]}
        providers = []
        for row in live["live_pool"]["routes"]:
            cluster = clusters.get(row["cluster_id"], {})
            healthy = row["health"] == "HEALTHY"
            providers.append({
                "provider_id": row["provider_id"], "cluster_id": row["cluster_id"], "profile_id": cluster.get("profile_id", "UNKNOWN"),
                "eligibility": "ELIGIBLE" if healthy else "COOLDOWN_OR_DEGRADED", "health": row["health"], "capacity": row["capacity"],
                "policy": "ALLOWED_EVIDENCED", "transport": "BROWSER_CDP", "last_evidence": live["observed_at"],
                "routing_reason": "SCHEDULABLE" if healthy and row["capacity"] == "AVAILABLE" else "NOT_SCHEDULABLE_CURRENT_STATE",
                "retry_after_seconds": None, "accepted_in_fa124": row["accepted_in_fa124"],
            })
        return {"schema":"die.factory-asset.provider-dashboard.v1","evidence_mode":"LIVE_BROKER_SANITIZED","observed_at":live["observed_at"],"route_asset_type":"RASTER","selected_profile_id":None,"providers":providers,"guessed_quota_present":False,"provider_dispatch_performed":False}
    return provider_dashboard.build_provider_dashboard(
        policy_registry=PROVIDER_POLICY_REGISTRY,
        fixture=PROVIDER_DASHBOARD_FIXTURE,
        capacity_ledger_cls=capacity_ledger.CapacityLedger,
        evaluate_policy=policy_gate.evaluate_policy,
        route_provider=provider_router.route_provider,
        observability=observability,
        today="2026-09-04",
        now="2026-09-04T03:15:00Z",
        route_asset_type="PHOTO",
    )


def run_console_synthetic_e2e() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="factory-console-c009-") as temp_root:
        core = factory_core_synthetic.run_synthetic_acceptance(Path(temp_root))
    if core.get("result") != "PASS" or core.get("provider_calls_performed") is not False or core.get("zero_false_success") is not True:
        raise ConsoleRequestError("SYNTHETIC_E2E_FAILED", "Factory Core synthetic acceptance did not pass")
    return {
        "schema":"die.factory-asset.console-synthetic-e2e.v1",
        "result":"PASS",
        "provider_calls_performed":False,
        "routing":core["routing"],
        "queue":core["queue"],
        "crash_recovery":core["crash_recovery"],
        "output":{
            "master_sha256":core["queue"]["artifact_sha256"],
            "ingestion_attempt_count":core["ingestion"]["attempt_count"],
            "unique_blob_count":core["ingestion"]["unique_blob_count"],
            "duplicate_blob_reused":core["ingestion"]["duplicate_blob_reused"],
            "canonical_truth":core["ingestion"]["canonical_truth"],
            "state_manager_commit_required":core["ingestion"]["state_manager_commit_required"],
        },
        "observability":{
            "attempts":core["observability"]["attempts"],
            "unique_masters":core["observability"]["unique_masters"],
            "failures":core["observability"]["failures"],
            "economics":core["observability"]["economics"],
        },
        "secret_observability_blocked":core["secret_observability_blocked"],
        "zero_false_success":core["zero_false_success"],
    }


def run_console_synthetic_batch_acceptance() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="factory-console-c011-") as temp_root:
        result = console_batch_acceptance.run_console_batch_acceptance(Path(temp_root))
    if result.get("result") != "PASS" or result.get("provider_calls_performed") is not False:
        raise ConsoleRequestError("SYNTHETIC_BATCH_ACCEPTANCE_FAILED", "Factory Console batch acceptance did not pass")
    sanitized = deepcopy(result)
    sanitized.pop("evidence_paths", None)
    return sanitized


def output_gallery_state() -> dict[str, Any]:
    return json.loads(json.dumps(OUTPUT_GALLERY_FIXTURE))


def production_acceptance_state() -> dict[str, Any]:
    return production_acceptance.build_production_acceptance(ROOT)


def qc_gallery_state() -> dict[str, Any]:
    return founder_qc_gallery.build_gallery(ROOT)


def cluster_topology_state() -> dict[str, Any]:
    return cluster_topology.build_cluster_topology(ROOT)


def install_recovered_queue(queue: Any, *, reconciliation_required_job_ids: list[str] | tuple[str, ...] | set[str] = ()) -> None:
    global CORE_QUEUE, RECONCILIATION_REQUIRED_JOB_IDS
    CORE_QUEUE = queue
    RECONCILIATION_REQUIRED_JOB_IDS = {str(job_id) for job_id in reconciliation_required_job_ids}


def queue_state() -> dict[str, Any]:
    return {"schema": "die.factory-asset.console-queue-state.v1", "provider_dispatch_performed": False, "reconciliation_required_job_ids": sorted(RECONCILIATION_REQUIRED_JOB_IDS), "events": [console_contract.queue_event(row) for row in CORE_QUEUE.list()]}


def submit_batch_to_queue(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"batch_intent"}:
        raise ConsoleRequestError("INVALID_QUEUE_SUBMIT_ENVELOPE", "expected batch_intent only")
    batch = payload["batch_intent"]
    if not isinstance(batch, dict) or batch.get("schema") != "die.factory-asset.console-batch-intent.v1":
        raise ConsoleRequestError("VALID_BATCH_INTENT_REQUIRED", "create a local batch intent first")
    if batch.get("dispatch_authority") != "SIMULATED_ONLY" or batch.get("dispatch_performed") is not False:
        raise ConsoleRequestError("LIVE_DISPATCH_FORBIDDEN", "queue submit accepts non-dispatch batch intents only")
    quantity = batch.get("quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 1000:
        raise ConsoleRequestError("BATCH_QUANTITY_OUT_OF_RANGE", "quantity must be 1..1000")
    created = []
    prefix = batch["semantic_fingerprint"][:12].upper()
    for index in range(1, quantity + 1):
        job_id = f"FCJOB-{prefix}-{index:04d}"
        semantic_id = f"{batch['semantic_asset_id']}-Q{index:04d}"
        intent = {"blueprint_id": batch["blueprint_id"], "semantic_asset_id": semantic_id, "label": f"{batch['label']} #{index:04d}", "provider_id": None}
        job = CORE_QUEUE.submit(job_id=job_id, idempotency_key=_job_key(batch["batch_id"], str(index), batch["semantic_fingerprint"]), intent=intent)
        created.append(console_contract.queue_event(job.as_dict()))
    return {"schema": "die.factory-asset.console-queue-submit.v1", "result": "PASS", "created_or_reused": len(created), "provider_dispatch_performed": False, "events": created}


def apply_queue_command(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "kind", "command_id", "job_id", "action"}
    if set(payload) != required or payload.get("schema") != "die.factory-asset.console-api.v1" or payload.get("kind") != "CONTROL_COMMAND":
        raise ConsoleRequestError("INVALID_CONTROL_COMMAND", "normalized CONTROL_COMMAND required")
    job_id = str(payload["job_id"]); action = str(payload["action"]); command_id = str(payload["command_id"])
    if job_id in RECONCILIATION_REQUIRED_JOB_IDS and action in {"START", "RESUME", "RETRY"}:
        raise ConsoleRequestError("RECONCILIATION_REQUIRED", "committed dispatch requires durable reconciliation before redispatch-capable control actions")
    if action == "START": CORE_QUEUE.start(job_id, owner="factory-console-local", lease_token=_job_key("control", command_id, job_id))
    elif action == "PAUSE": CORE_QUEUE.pause(job_id)
    elif action == "RESUME": CORE_QUEUE.resume(job_id)
    elif action == "CANCEL": CORE_QUEUE.cancel(job_id)
    elif action == "RETRY": CORE_QUEUE.retry(job_id)
    else: raise ConsoleRequestError("CONTROL_ACTION_UNKNOWN", action)
    return {"schema": "die.factory-asset.console-control-result.v1", "result": "PASS", "provider_dispatch_performed": False, "event": console_contract.queue_event(CORE_QUEUE.get(job_id).as_dict())}

_seed_queue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def _json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed=urlparse(self.path)
        if parsed.path == "/api/qc-image":
            q=parse_qs(parsed.query);asset_id=(q.get("id") or [""])[0];variant=(q.get("variant") or ["thumb"])[0]
            try: body,ctype=founder_qc_gallery.image_payload(ROOT,asset_id,variant)
            except (KeyError,ValueError): self._json(HTTPStatus.NOT_FOUND,{"result":"FAIL","code":"QC_ASSET_NOT_FOUND"});return
            self._bytes(HTTPStatus.OK,body,ctype);return
        if parsed.path == "/api/qc-gallery":
            self._json(HTTPStatus.OK,qc_gallery_state());return
        if self.path == "/api/queue/jobs":
            self._json(HTTPStatus.OK, queue_state())
            return
        if self.path == "/api/providers":
            self._json(HTTPStatus.OK, provider_dashboard_state())
            return
        if self.path == "/api/cluster-topology":
            self._json(HTTPStatus.OK, cluster_topology_state())
            return
        if self.path == "/api/outputs":
            self._json(HTTPStatus.OK, output_gallery_state())
            return
        if self.path == "/api/production-acceptance":
            self._json(HTTPStatus.OK, production_acceptance_state())
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/compile", "/api/batch-intent", "/api/queue/submit", "/api/queue/action", "/api/synthetic/e2e", "/api/synthetic/batch-acceptance"}:
            self._json(HTTPStatus.NOT_FOUND, {"result": "FAIL", "code": "NOT_FOUND"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 256_000:
                raise ConsoleRequestError("INVALID_BODY_SIZE", "body size outside allowed range")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ConsoleRequestError("INVALID_JSON_BODY", "JSON body must be object")
            if self.path == "/api/compile": result = compile_blueprint_payload(payload)
            elif self.path == "/api/batch-intent": result = create_batch_intent(payload)
            elif self.path == "/api/queue/submit": result = submit_batch_to_queue(payload)
            elif self.path == "/api/queue/action": result = apply_queue_command(payload)
            elif self.path == "/api/synthetic/e2e":
                if set(payload) != {"schema"} or payload.get("schema") != "die.factory-asset.console-synthetic-e2e-request.v1":
                    raise ConsoleRequestError("INVALID_SYNTHETIC_E2E_REQUEST", "synthetic E2E request schema required")
                result = run_console_synthetic_e2e()
            else:
                if set(payload) != {"schema"} or payload.get("schema") != "die.factory-asset.console-batch-acceptance-request.v1":
                    raise ConsoleRequestError("INVALID_SYNTHETIC_BATCH_ACCEPTANCE_REQUEST", "synthetic batch acceptance request schema required")
                result = run_console_synthetic_batch_acceptance()
            self._json(HTTPStatus.OK, result)
        except compiler.BlueprintCompileError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"result": "FAIL", "code": exc.code, "message": str(exc), "dispatch_performed": False})
        except (ConsoleRequestError, factory_queue.QueueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"result": "FAIL", "code": exc.code, "message": str(exc), "dispatch_performed": False})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"result": "FAIL", "code": "INVALID_JSON_BODY", "dispatch_performed": False})

    def log_message(self, format: str, *args: Any) -> None:
        return


DEFAULT_PORT = 8876
FALLBACK_PORTS = (8877, 0)


def _bind_loopback_server(host: str, preferred_port: int) -> tuple[ThreadingHTTPServer, int, list[tuple[int, str]]]:
    attempts: list[tuple[int, str]] = []
    candidates: list[int] = []
    for candidate in (preferred_port, *FALLBACK_PORTS):
        if candidate not in candidates:
            candidates.append(candidate)
    last_error: OSError | None = None
    for candidate in candidates:
        try:
            server = ThreadingHTTPServer((host, candidate), Handler)
            return server, int(server.server_port), attempts
        except OSError as exc:
            last_error = exc
            attempts.append((candidate, f"{type(exc).__name__}: {exc}"))
    assert last_error is not None
    raise last_error


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Factory Console prototype server is loopback-only")
    server, bound_port, attempts = _bind_loopback_server(host, port)
    for failed_port, reason in attempts:
        print(f"Factory Console port {failed_port} unavailable; trying fallback. {reason}")
    print(f"Factory Console prototype: http://{host}:{bound_port}/ (loopback-only, no live dispatch)")
    server.serve_forever()


if __name__ == "__main__":
    serve()
