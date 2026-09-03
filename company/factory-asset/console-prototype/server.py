from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from copy import deepcopy
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
STATIC_ROOT = Path(__file__).resolve().parent


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

CORE_QUEUE = factory_queue.FactoryJobQueue()


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


def queue_state() -> dict[str, Any]:
    return {"schema": "die.factory-asset.console-queue-state.v1", "provider_dispatch_performed": False, "events": [console_contract.queue_event(row) for row in CORE_QUEUE.list()]}


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

    def do_GET(self) -> None:
        if self.path == "/api/queue/jobs":
            self._json(HTTPStatus.OK, queue_state())
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/compile", "/api/batch-intent", "/api/queue/submit", "/api/queue/action"}:
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
            else: result = apply_queue_command(payload)
            self._json(HTTPStatus.OK, result)
        except compiler.BlueprintCompileError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"result": "FAIL", "code": exc.code, "message": str(exc), "dispatch_performed": False})
        except (ConsoleRequestError, factory_queue.QueueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"result": "FAIL", "code": exc.code, "message": str(exc), "dispatch_performed": False})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"result": "FAIL", "code": "INVALID_JSON_BODY", "dispatch_performed": False})

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Factory Console prototype server is loopback-only")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Factory Console prototype: http://{host}:{port}/ (loopback-only, no live dispatch)")
    server.serve_forever()


if __name__ == "__main__":
    serve()