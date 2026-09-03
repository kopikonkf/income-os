from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorGateDecision:
    state: str
    reason_codes: tuple[str, ...]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "die.factory-asset.vectorizability-decision.v1",
            "state": self.state,
            "reason_codes": list(self.reason_codes),
            "evidence": self.evidence,
        }


class VectorGateInputError(ValueError):
    pass


def classify_vectorizability(evidence: dict[str, Any]) -> VectorGateDecision:
    required = {
        "source_representation",
        "declared_mode",
        "raster_trace_allowed",
        "photorealistic",
        "color_count",
        "edge_complexity",
        "estimated_path_count",
        "has_text_or_fonts",
    }
    missing = sorted(required - set(evidence))
    if missing:
        raise VectorGateInputError("missing evidence: " + ",".join(missing))

    source = evidence["source_representation"]
    mode = evidence["declared_mode"]
    trace_allowed = bool(evidence["raster_trace_allowed"])

    if source == "VECTOR_PATHS":
        return VectorGateDecision("NATIVE_VECTOR", ("SOURCE_ALREADY_VECTOR",), evidence)

    if source != "RASTER_PIXELS":
        return VectorGateDecision("NOT_VECTORIZABLE", ("UNSUPPORTED_SOURCE_REPRESENTATION",), evidence)

    reasons: list[str] = []
    if mode == "NOT_VECTORIZABLE":
        reasons.append("DECLARED_NOT_VECTORIZABLE")
    if evidence["photorealistic"]:
        reasons.append("PHOTOREALISTIC_INPUT")
    if evidence["has_text_or_fonts"]:
        reasons.append("TEXT_OR_FONT_DEPENDENCY")
    if int(evidence["color_count"]) > 16:
        reasons.append("COLOR_COMPLEXITY_EXCEEDED")
    if float(evidence["edge_complexity"]) > 0.35:
        reasons.append("EDGE_COMPLEXITY_EXCEEDED")
    if int(evidence["estimated_path_count"]) > 512:
        reasons.append("PATH_COUNT_EXCEEDED")
    if not trace_allowed:
        reasons.append("TRACE_NOT_AUTHORIZED")
    if mode != "TRACE_ELIGIBLE":
        reasons.append("TRACE_MODE_NOT_ELIGIBLE")

    if reasons:
        return VectorGateDecision("NOT_VECTORIZABLE", tuple(dict.fromkeys(reasons)), evidence)

    return VectorGateDecision(
        "TRACE_ELIGIBLE",
        ("LOW_COLOR_COMPLEXITY", "LOW_EDGE_COMPLEXITY", "BOUNDED_PATH_COUNT", "TRACE_EXPLICITLY_AUTHORIZED"),
        evidence,
    )