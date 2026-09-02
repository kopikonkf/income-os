#!/usr/bin/env python3
"""Deterministically resolve the current DIE production card and next actor/action."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "die.production-active-card-resolution.v1"
DEFAULT_WORKSPACES = Path("/var/lib/die/workspaces")

PARKED_STATES = {"WAITING_FOUNDER_QC", "READY_FOR_MANUAL_PUBLISH", "MANUALLY_PUBLISHED"}
ACTIONABLE = {
    "SELECTED": ("hermes-operator", "PROD-RESOLVE-BLUEPRINT", "Resolve reusable-vs-new Blueprint path for the selected seed."),
    "BLUEPRINT_REQUIRED": ("die-lnx-division-001", "OP-REQUEST-DIVISION01-BLUEPRINT", "Request Division01 Blueprint authoring for the exact active family/seed."),
    "BLUEPRINT_READY": ("hermes-operator", "PROD-DISPATCH-WORKER", "Dispatch a bounded Worker job from the fixed Blueprint."),
    "WORKER_QUEUED": ("worker-template", "PROD-CONTINUE-WORKER", "Advance the queued bounded Worker job."),
    "WORKER_RUNNING": ("worker-template", "PROD-CONTINUE-WORKER", "Observe/continue the bounded Worker job without duplicating it."),
    "PROVIDER_RUNNING": ("muxia-provider", "PROD-CONTINUE-PROVIDER", "Observe/continue the existing provider job; verify filesystem artifact before completion."),
    "ARTIFACT_CREATED": ("hermes-operator", "PROD-RUN-POSTPROCESS", "Run deterministic postproduction for the existing artifact."),
    "POSTPROCESSING": ("hermes-operator", "PROD-CONTINUE-POSTPROCESS", "Continue deterministic postproduction from durable artifact state."),
    "QA_RUNNING": ("hermes-operator", "PROD-CONTINUE-QA", "Continue deterministic QA for the existing artifact."),
    "QC_RUNNING": ("hermes-operator", "PROD-CONTINUE-QC", "Continue deterministic QC for the existing artifact."),
    "FAILED_RETRYABLE": ("hermes-operator", "PROD-RETRY-FAILED-STAGE", "Retry only the recorded retryable failed stage after checking durable state."),
}
EXECUTION_SURFACES = {
    "OP-REQUEST-DIVISION01-BLUEPRINT": {
        "execution_surface": "PRODUCTION_COGNITION_LINE_V1",
        "execution_contract_ref": "company/die-agents/hermes/production-cognition/production_cognition_tick.py",
        "execution_ready": True,
        "execution_mode": "ASYNC_DELEGATED",
    },
}

BLOCKING = {
    "BLOCKED_LOGIN": ("founder", "FOUNDER-CREDENTIAL-ACTION-REQUIRED", "Preserve the card; credential/login action is outside autonomous authority."),
    "BLOCKED_PROVIDER_LIMIT": ("hermes-operator", "PROD-RETRY-PROVIDER-CHAIN", "Preserve the card and retry through configured provider/fallback policy; do not start a compensating seed."),
    "BLOCKED_RIGHTS": ("founder", "FOUNDER-RIGHTS-DECISION-REQUIRED", "Preserve the card for the required human rights decision."),
    "BLOCKED_QA": ("hermes-operator", "PROD-REMEDIATE-QA", "Preserve the card and perform only deterministic allowed QA remediation."),
    "BLOCKED_QC": ("hermes-operator", "PROD-REMEDIATE-QC", "Preserve the card and perform only deterministic allowed QC remediation."),
    "FAILED_TERMINAL": ("hermes-operator", "PROD-REPORT-TERMINAL-FAILURE", "Preserve terminal evidence and report the failure; do not invent continuation."),
}

FIELD_RE = re.compile(r"^-\s*([^:]+):\s*(.*)$")
SEED_RE = re.compile(r"\b(SEED-\d{6})\b(?:\s*\(([^)]+)\))?")

@dataclass(frozen=True)
class Card:
    task_id: str
    workspace: Path
    state: str
    state_source: str
    seed_id: str | None
    seed_name: str | None
    family: str | None
    started_at: str | None


def _fields(progress: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in progress.read_text(encoding="utf-8", errors="replace").splitlines():
        m = FIELD_RE.match(line.strip())
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def _legacy_parked_state(workspace: Path) -> str | None:
    """Recognize the accepted pre-state-field canary without treating arbitrary workspaces as production."""
    asset = workspace / "qa" / "asset.png"
    rights = workspace / "qa" / "rights-input.json"
    if not asset.is_file() or not rights.is_file():
        return None
    try:
        payload = json.loads(rights.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    review = payload.get("human_visual_review") if isinstance(payload, dict) else None
    if isinstance(review, dict) and review.get("state") == "NOT_REVIEWED" and review.get("reviewer") == "PENDING_FOUNDER":
        return "WAITING_FOUNDER_QC"
    return None


def discover_cards(workspaces_root: Path) -> tuple[list[Card], list[dict[str, str]]]:
    cards: list[Card] = []
    ambiguous: list[dict[str, str]] = []
    if not workspaces_root.is_dir():
        return cards, ambiguous
    known_states = PARKED_STATES | set(ACTIONABLE) | set(BLOCKING)
    for workspace in sorted(p for p in workspaces_root.iterdir() if p.is_dir()):
        progress = workspace / "PROGRESS.md"
        if not progress.is_file():
            continue
        fields = _fields(progress)
        explicit = fields.get("state", "").strip().upper()
        state_source = "PROGRESS_STATE"
        state = explicit
        if not state:
            inferred = _legacy_parked_state(workspace)
            if not inferred:
                continue
            state = inferred
            state_source = "LEGACY_RIGHTS_GATE_INFERENCE"
        if state not in known_states:
            ambiguous.append({"task_id": workspace.name, "state": state, "state_source": state_source})
            continue
        seed_text = fields.get("seed", "")
        seed_match = SEED_RE.search(seed_text)
        family = fields.get("family")
        cards.append(Card(
            task_id=workspace.name,
            workspace=workspace,
            state=state,
            state_source=state_source,
            seed_id=seed_match.group(1) if seed_match else None,
            seed_name=(seed_match.group(2).strip() if seed_match and seed_match.group(2) else None),
            family=family,
            started_at=fields.get("started"),
        ))
    return cards, ambiguous


def _card_payload(card: Card, classification: str, actor: str | None = None, action: str | None = None, instruction: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "task_id": card.task_id,
        "workspace": str(card.workspace),
        "state": card.state,
        "state_source": card.state_source,
        "classification": classification,
        "seed_id": card.seed_id,
        "seed_name": card.seed_name,
        "family": card.family,
        "started_at": card.started_at,
    }
    if actor is not None:
        out["required_actor"] = actor
    if action is not None:
        out["next_action_type"] = action
        surface = EXECUTION_SURFACES.get(action)
        if surface:
            out.update(surface)
        else:
            out["execution_ready"] = True
            out["execution_surface"] = "NATIVE_PRODUCTION_RUNTIME"
            out["execution_mode"] = "INLINE"
    if instruction is not None:
        out["next_action_instruction"] = instruction
    return out


def resolve_active_card(workspaces_root: Path) -> dict[str, Any]:
    if not workspaces_root.is_dir():
        return {"schema": SCHEMA, "status": "BLOCKED", "reason": "WORKSPACES_ROOT_UNAVAILABLE", "workspaces_root": str(workspaces_root), "authority_effect": "NONE", "existing_authority_unchanged": True}
    cards, ambiguous = discover_cards(workspaces_root)
    if ambiguous:
        return {"schema": SCHEMA, "status": "BLOCKED", "reason": "AMBIGUOUS_PRODUCTION_STATE", "ambiguous_cards": ambiguous, "authority_effect": "NONE", "existing_authority_unchanged": True}

    actionable = [c for c in cards if c.state in ACTIONABLE]
    blocking = [c for c in cards if c.state in BLOCKING]
    parked = [c for c in cards if c.state in PARKED_STATES]

    def order(card: Card) -> tuple[str, str]:
        return (card.started_at or "9999-99-99T99:99:99Z", card.task_id)

    if actionable:
        card = sorted(actionable, key=order)[0]
        actor, action, instruction = ACTIONABLE[card.state]
        payload = _card_payload(card, "ACTIONABLE", actor, action, instruction)
        if payload.get("execution_ready") is False:
            payload["classification"] = "EXECUTION_BLOCKED"
            return {
                "schema": SCHEMA,
                "status": "BLOCKED_ACTIVE_CARD",
                "reason": payload["blocker_code"],
                "active_card": payload,
                "parked_card_count": len(parked),
                "blocking_card_count": len(blocking),
                "authority_effect": "NONE",
                "existing_authority_unchanged": True,
            }
        if payload.get("execution_mode") == "ASYNC_DELEGATED":
            payload["classification"] = "ASYNC_DELEGATED"
            return {
                "schema": SCHEMA,
                "status": "DELEGATED_ACTIVE_CARD",
                "active_card": payload,
                "parked_card_count": len(parked),
                "blocking_card_count": len(blocking),
                "authority_effect": "NONE",
                "existing_authority_unchanged": True,
            }
        return {
            "schema": SCHEMA,
            "status": "CONTINUE_ACTIVE_CARD",
            "active_card": payload,
            "parked_card_count": len(parked),
            "blocking_card_count": len(blocking),
            "authority_effect": "NONE",
            "existing_authority_unchanged": True,
        }
    if blocking:
        card = sorted(blocking, key=order)[0]
        actor, action, instruction = BLOCKING[card.state]
        return {
            "schema": SCHEMA,
            "status": "BLOCKED_ACTIVE_CARD",
            "active_card": _card_payload(card, "BLOCKING", actor, action, instruction),
            "parked_card_count": len(parked),
            "authority_effect": "NONE",
            "existing_authority_unchanged": True,
        }
    return {
        "schema": SCHEMA,
        "status": "NO_ACTIVE_CARD",
        "parked_cards": [_card_payload(c, "PARKED_HUMAN_GATE") for c in sorted(parked, key=order)],
        "parked_card_count": len(parked),
        "authority_effect": "NONE",
        "existing_authority_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspaces", type=Path, default=DEFAULT_WORKSPACES)
    args = ap.parse_args(argv)
    out = resolve_active_card(args.workspaces)
    print(json.dumps(out, sort_keys=True))
    return 2 if out["status"] == "BLOCKED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
