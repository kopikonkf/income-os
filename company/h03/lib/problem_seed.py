from __future__ import annotations

from typing import Any

SCHEMA = "die.h03.human-problem-seed.v1"
_SIGNAL_STATES = {"UNKNOWN", "PARTIAL", "OBSERVED"}
_OBS_STATES = {"UNKNOWN", "OBSERVED"}


def _text(value: Any, field: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValueError(f"PROBLEM_SEED_FIELD_REQUIRED:{field}")
    return value.strip()


def _signal(value: Any, field: str) -> None:
    if not isinstance(value, dict) or value.get("state") not in _SIGNAL_STATES:
        raise ValueError(f"PROBLEM_SEED_SIGNAL_INVALID:{field}")
    refs = value.get("evidence_refs")
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or any(not isinstance(r, str) or not r.strip() for r in refs):
        raise ValueError(f"PROBLEM_SEED_SIGNAL_EVIDENCE_INVALID:{field}")
    if value["state"] == "UNKNOWN" and refs:
        raise ValueError(f"PROBLEM_SEED_UNKNOWN_SIGNAL_HAS_EVIDENCE:{field}")
    if value["state"] != "UNKNOWN" and not refs:
        raise ValueError(f"PROBLEM_SEED_OBSERVED_SIGNAL_NEEDS_EVIDENCE:{field}")


def validate_problem_seed(seed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(seed, dict) or seed.get("schema_version") != SCHEMA or seed.get("holding_id") != "H03":
        raise ValueError("PROBLEM_SEED_SCHEMA_INVALID")
    _text(seed.get("problem_seed_id"), "problem_seed_id", 8)
    persona = seed.get("persona")
    if not isinstance(persona, dict):
        raise ValueError("PROBLEM_SEED_PERSONA_REQUIRED")
    _text(persona.get("actor"), "persona.actor", 2)
    _text(persona.get("qualifier"), "persona.qualifier")
    for field in ("context", "trigger", "job_to_be_done", "desired_outcome"):
        _text(seed.get(field), field, 3)
    pain = seed.get("pain")
    if not isinstance(pain, dict):
        raise ValueError("PROBLEM_SEED_PAIN_REQUIRED")
    _text(pain.get("statement"), "pain.statement", 3)
    for field in ("severity_state", "frequency_state", "urgency_state"):
        if pain.get(field) not in _OBS_STATES:
            raise ValueError(f"PROBLEM_SEED_PAIN_STATE_INVALID:{field}")
    signals = seed.get("commercial_signals")
    if not isinstance(signals, dict):
        raise ValueError("PROBLEM_SEED_COMMERCIAL_SIGNALS_REQUIRED")
    _signal(signals.get("demand"), "demand")
    _signal(signals.get("willingness_to_pay"), "willingness_to_pay")
    refs = seed.get("source_refs")
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or any(not isinstance(r, str) or not r.strip() for r in refs):
        raise ValueError("PROBLEM_SEED_SOURCE_REFS_INVALID")
    if seed.get("truth_status") not in {"CANDIDATE", "VALIDATED"}:
        raise ValueError("PROBLEM_SEED_TRUTH_STATUS_INVALID")
    return seed
