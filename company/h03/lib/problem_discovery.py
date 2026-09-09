from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import cognition_work_card
import problem_seed

BATCH_SCHEMA = "die.h03.problem-seed-batch.v1"


def build_seed_curator_work_card(*, batch_id: str, signal_artifact_ref: str) -> dict[str, Any]:
    card = {
        "schema_version": cognition_work_card.CARD_SCHEMA,
        "work_card_id": f"H03-WC-SEED-{batch_id}",
        "holding_id": "H03",
        "task_id": "H03-OPP-002",
        "role": "SEED_CURATOR",
        "queue": "seed-curation",
        "idempotency_key": f"h03-seed-curation:{batch_id}",
        "input_artifacts": [{"artifact_id": f"SIGNALS-{batch_id}", "kind": "governed_signal_packet", "ref": signal_artifact_ref, "sha256": None}],
        "output_contract": {"artifact_kind": "problem_seed_batch", "schema_version": BATCH_SCHEMA},
        "capability_requirements": cognition_work_card.standard_web_ai_capabilities(),
        "terminal_policy": {"max_attempts": 3, "retryable_failures": ["RATE_LIMITED","PROVIDER_UNAVAILABLE","PROFILE_UNAVAILABLE"]}
    }
    return cognition_work_card.validate_work_card(card)


def _canonical_text(value: str) -> str:
    return " ".join(value.lower().split())


def _dedupe_key(seed: dict[str, Any]) -> tuple[str, ...]:
    p = seed["persona"]
    pain = seed["pain"]
    return tuple(_canonical_text(x) for x in (
        p["actor"], p["qualifier"], seed["context"], seed["trigger"], seed["job_to_be_done"], pain["statement"], seed["desired_outcome"]
    ))


def normalize_discovered_seed(seed: dict[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(seed)
    # Curation may discover a problem; commercial validation belongs to DMD-001.
    candidate["commercial_signals"] = {
        "demand": {"state": "UNKNOWN", "evidence_refs": []},
        "willingness_to_pay": {"state": "UNKNOWN", "evidence_refs": []}
    }
    candidate["truth_status"] = "CANDIDATE"
    problem_seed.validate_problem_seed(candidate)
    return candidate


def deduplicate_problem_seeds(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    accepted: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for raw in candidates:
        seed = normalize_discovered_seed(raw)
        key = _dedupe_key(seed)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        accepted.append(seed)
    return accepted, duplicates


def build_problem_seed_batch(*, batch_id: str, source_signal_refs: list[str], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not source_signal_refs or len(source_signal_refs) != len(set(source_signal_refs)):
        raise ValueError("PROBLEM_DISCOVERY_SIGNAL_REFS_REQUIRED")
    seeds, duplicates = deduplicate_problem_seeds(candidates)
    return {
        "schema_version": BATCH_SCHEMA,
        "batch_id": batch_id,
        "holding_id": "H03",
        "source_signal_refs": list(source_signal_refs),
        "candidates": seeds,
        "dedupe_count": duplicates,
        "truth_status": "CANDIDATE"
    }
