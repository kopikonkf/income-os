from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import cognition_work_card
import orchestrator_queue

ARTIFACT_SCHEMA = "die.h03.durable-artifact-envelope.v1"
RESULT_RECEIPT_SCHEMA = "die.h03.work-card-result-receipt.v1"
_REF_RE = re.compile(r"^artifact://h03/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
_FORBIDDEN = {
    "cookie", "cookies", "token", "tokens", "access_token", "refresh_token",
    "authorization", "oauth", "session_key", "session_bytes", "credentials",
    "credential", "browser_profile_path", "profile_dir", "password",
}


def _scan(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN:
                raise ValueError(f"ARTIFACT_SECRET_MATERIAL_FORBIDDEN:{path}.{key}")
            _scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan(child, f"{path}[{index}]")


def _safe_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"ARTIFACT_{label}_INVALID")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ArtifactCourier:
    """Host-local durable artifact store for H03 cognition handoffs.

    Browser workers never receive this path. They receive expanded bounded payloads;
    artifact:// refs are for the orchestrator only.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / _safe_id(run_id, "RUN_ID")

    def _artifact_path(self, run_id: str, artifact_id: str) -> Path:
        return self._run_dir(run_id) / "artifacts" / f"{_safe_id(artifact_id, 'ID')}.json"

    def _queue_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "queue-state.json"

    def _result_path(self, run_id: str, idempotency_key: str) -> Path:
        key = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        return self._run_dir(run_id) / "results" / f"{key}.json"

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def create_or_load_queue(self, run_id: str) -> dict[str, Any]:
        path = self._queue_path(run_id)
        if not path.exists():
            state = orchestrator_queue.create_state(run_id)
            self.save_queue(run_id, state)
            return state
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("schema_version") != orchestrator_queue.SCHEMA or state.get("batch_id") != run_id:
            raise ValueError("ARTIFACT_QUEUE_STATE_INVALID")
        return state

    def save_queue(self, run_id: str, state: dict[str, Any]) -> None:
        if state.get("schema_version") != orchestrator_queue.SCHEMA or state.get("batch_id") != run_id:
            raise ValueError("ARTIFACT_QUEUE_STATE_INVALID")
        _scan(state)
        self._atomic_write(self._queue_path(run_id), _json_bytes(state))

    def commit_payload(
        self,
        *,
        run_id: str,
        artifact_id: str,
        kind: str,
        declared_schema: str,
        producer_work_card_id: str,
        payload: Any,
    ) -> dict[str, Any]:
        _safe_id(run_id, "RUN_ID")
        _safe_id(artifact_id, "ID")
        _safe_id(producer_work_card_id, "WORK_CARD_ID")
        if not isinstance(kind, str) or not kind.strip() or not isinstance(declared_schema, str) or not declared_schema.strip():
            raise ValueError("ARTIFACT_CONTRACT_INVALID")
        _scan(payload)
        envelope = {
            "schema_version": ARTIFACT_SCHEMA,
            "holding_id": "H03",
            "run_id": run_id,
            "artifact_id": artifact_id,
            "kind": kind,
            "declared_payload_schema": declared_schema,
            "producer_work_card_id": producer_work_card_id,
            "payload": payload,
        }
        data = _json_bytes(envelope)
        digest = _sha256(data)
        path = self._artifact_path(run_id, artifact_id)
        if path.exists():
            existing = path.read_bytes()
            if _sha256(existing) != digest:
                raise ValueError("ARTIFACT_ID_CONFLICT")
        else:
            self._atomic_write(path, data)
        return {
            "artifact_id": artifact_id,
            "kind": kind,
            "ref": f"artifact://h03/{run_id}/{artifact_id}",
            "sha256": digest,
        }

    def existing_ref(self, *, run_id: str, artifact_id: str, kind: str | None = None) -> dict[str, Any] | None:
        path = self._artifact_path(run_id, artifact_id)
        if not path.exists():
            return None
        raw = path.read_bytes()
        envelope = json.loads(raw.decode("utf-8"))
        if (
            envelope.get("schema_version") != ARTIFACT_SCHEMA
            or envelope.get("holding_id") != "H03"
            or envelope.get("run_id") != run_id
            or envelope.get("artifact_id") != artifact_id
        ):
            raise ValueError("ARTIFACT_ENVELOPE_INVALID")
        if kind is not None and envelope.get("kind") != kind:
            raise ValueError("ARTIFACT_KIND_MISMATCH")
        _scan(envelope)
        return {
            "artifact_id": artifact_id,
            "kind": envelope["kind"],
            "ref": f"artifact://h03/{run_id}/{artifact_id}",
            "sha256": _sha256(raw),
        }

    def resolve(self, artifact_ref: dict[str, Any]) -> Any:
        if not isinstance(artifact_ref, dict):
            raise ValueError("ARTIFACT_REF_INVALID")
        ref = artifact_ref.get("ref")
        match = _REF_RE.fullmatch(str(ref or ""))
        if not match:
            raise ValueError("ARTIFACT_REF_UNSUPPORTED")
        run_id, artifact_id = match.groups()
        path = self._artifact_path(run_id, artifact_id)
        if not path.exists():
            raise FileNotFoundError("ARTIFACT_REF_NOT_FOUND")
        raw = path.read_bytes()
        digest = _sha256(raw)
        expected = artifact_ref.get("sha256")
        if expected and expected != digest:
            raise ValueError("ARTIFACT_SHA256_MISMATCH")
        envelope = json.loads(raw.decode("utf-8"))
        if envelope.get("schema_version") != ARTIFACT_SCHEMA or envelope.get("artifact_id") != artifact_id:
            raise ValueError("ARTIFACT_ENVELOPE_INVALID")
        _scan(envelope)
        return envelope["payload"]

    def expand_inputs(self, card: dict[str, Any], *, max_chars: int = 80_000) -> str:
        cognition_work_card.validate_work_card(card)
        blocks: list[str] = []
        total = 0
        for item in card["input_artifacts"]:
            payload = self.resolve(item)
            rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
            block = (
                f"ARTIFACT_ID: {item['artifact_id']}\n"
                f"KIND: {item['kind']}\n"
                f"REF: {item['ref']}\n"
                f"CONTENT:\n{rendered}"
            )
            total += len(block)
            if total > max_chars:
                raise ValueError("ARTIFACT_INPUT_CONTEXT_LIMIT_EXCEEDED")
            blocks.append(block)
        return "\n\n--- H03 ARTIFACT BOUNDARY ---\n\n".join(blocks)

    def save_result_receipt(self, run_id: str, card: dict[str, Any], result: dict[str, Any]) -> None:
        cognition_work_card.validate_worker_result(card, result)
        receipt = {
            "schema_version": RESULT_RECEIPT_SCHEMA,
            "holding_id": "H03",
            "run_id": run_id,
            "idempotency_key": card["idempotency_key"],
            "result": result,
        }
        _scan(receipt)
        self._atomic_write(self._result_path(run_id, card["idempotency_key"]), _json_bytes(receipt))

    def load_result_receipt(self, run_id: str, card: dict[str, Any]) -> dict[str, Any] | None:
        path = self._result_path(run_id, card["idempotency_key"])
        if not path.exists():
            return None
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if (
            receipt.get("schema_version") != RESULT_RECEIPT_SCHEMA
            or receipt.get("run_id") != run_id
            or receipt.get("idempotency_key") != card["idempotency_key"]
        ):
            raise ValueError("RESULT_RECEIPT_INVALID")
        cognition_work_card.validate_worker_result(card, receipt["result"])
        return receipt["result"]
