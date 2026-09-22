"""AI-origin marketplace router (MARKETPLACE_DERIVATIVE_COMPATIBILITY_V1).

Deterministic, no network, no upload, no compatibility-PASS claims.
READY means manual Founder submission only; package-readiness human
gates (rights clearance + Founder QC) still apply downstream.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "company/factory-asset/registries/marketplace-ai-origin-policy.v1.json"


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _index(policy: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    policy = policy or load_policy()
    return {p["platform_id"]: p for p in policy["policies"]}


def is_marketplace(platform_id: str, policy: dict[str, Any] | None = None) -> bool:
    entry = _index(policy).get(platform_id)
    if entry is None:
        return False
    return bool(entry.get("marketplace"))


def route(
    platform_id: str, *, ai_origin: bool = True, policy: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Route one AI-origin asset to one platform.

    Returns READY_FOR_MANUAL_SUBMISSION / BLOCKED_AI_EXCLUDED /
    NOT_A_MARKETPLACE / UNKNOWN_PLATFORM. Never returns a
    compatibility PASS.
    """
    entry = _index(policy).get(platform_id)
    if entry is None:
        return {
            "platform_id": platform_id,
            "route": "UNKNOWN_PLATFORM",
            "upload": False,
            "reason": "No policy entry; fail closed.",
        }
    if not entry.get("marketplace"):
        return {
            "platform_id": platform_id,
            "route": "NOT_A_MARKETPLACE",
            "upload": False,
            "reason": entry.get("notes", ""),
        }
    if ai_origin and not entry.get("ai_accepted"):
        return {
            "platform_id": platform_id,
            "route": "BLOCKED_AI_EXCLUDED",
            "upload": False,
            "reason": entry.get("notes", ""),
        }
    out: dict[str, Any] = {
        "platform_id": platform_id,
        "route": "READY_FOR_MANUAL_SUBMISSION",
        "upload": True,
        "raster_delivery": list(entry.get("raster_delivery", [])),
        "disclosure": entry.get("disclosure"),
    }
    if entry.get("account_requirement"):
        out["account_requirement"] = entry["account_requirement"]
    return out


def disclosure_for(platform_id: str, policy: dict[str, Any] | None = None) -> str | None:
    entry = _index(policy).get(platform_id)
    if entry is None:
        return None
    return entry.get("disclosure")
