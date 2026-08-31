from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DIE_HOME = HERE.parents[3]
INSTANCES = DIE_HOME / "company" / "runtime-instances-v1.json"
VALID_INSTANCE_IDS = ("DIE-WINDOWS", "DIE-LINUX")


class CompanyInstanceError(RuntimeError):
    pass


def load_instances() -> dict[str, Any]:
    data = json.loads(INSTANCES.read_text(encoding="utf-8"))
    if data.get("schema") != "die.company.runtime-instances.v1":
        raise CompanyInstanceError("E_COMPANY_INSTANCE_SCHEMA")
    return data


def resolve_instance_id(snapshot: dict[str, Any] | None = None, env: dict[str, str] | None = None) -> str:
    candidate = None
    if snapshot is not None:
        candidate = snapshot.get("company_instance_id")
    if not candidate:
        candidate = (env or os.environ).get("DIE_COMPANY_INSTANCE")
    if candidate not in VALID_INSTANCE_IDS:
        raise CompanyInstanceError("E_COMPANY_INSTANCE_REQUIRED")
    return str(candidate)


def principal_for(instance_id: str, role: str) -> str:
    data = load_instances()
    try:
        return str(data["instances"][instance_id]["principals"][role])
    except KeyError as exc:
        raise CompanyInstanceError(f"E_COMPANY_INSTANCE_ROLE:{instance_id}:{role}") from exc
