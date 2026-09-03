from __future__ import annotations

import importlib.util
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

    def do_POST(self) -> None:
        if self.path not in {"/api/compile", "/api/batch-intent"}:
            self._json(HTTPStatus.NOT_FOUND, {"result": "FAIL", "code": "NOT_FOUND"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 256_000:
                raise ConsoleRequestError("INVALID_BODY_SIZE", "body size outside allowed range")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ConsoleRequestError("INVALID_JSON_BODY", "JSON body must be object")
            result = compile_blueprint_payload(payload) if self.path == "/api/compile" else create_batch_intent(payload)
            self._json(HTTPStatus.OK, result)
        except compiler.BlueprintCompileError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"result": "FAIL", "code": exc.code, "message": str(exc), "dispatch_performed": False})
        except ConsoleRequestError as exc:
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