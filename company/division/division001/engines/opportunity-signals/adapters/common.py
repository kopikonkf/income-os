from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def make_signal_id(prefix: str, fingerprint: str) -> str:
    return f"OPSIG-{prefix}-{fingerprint[:20].upper()}"


def make_dedupe_key(source_id: str, subject_id: str, signal_type: str, observed_at: str) -> str:
    material = f"{source_id}|{subject_id}|{signal_type}|{observed_at}".encode("utf-8")
    return "oppsig:v1:" + hashlib.sha256(material).hexdigest()
