#!/usr/bin/env python3
"""Validate a Division01 Opportunity Signal receipt without collecting data."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_VERSION = "die.division001.opportunity-signals.v1"
DEFAULT_SCHEMA = Path(__file__).with_name("die.division001.opportunity-signals.v1.schema.json")

CLASS_TYPES = {
    "DEMAND": {
        "AUTOCOMPLETE_PRESENCE", "AUTOCOMPLETE_RANK", "RELATED_QUERY_PRESENCE",
        "SEARCH_INTEREST_INDEX", "SEARCH_INTEREST_DELTA", "VISIBLE_DOWNLOAD_COUNT",
        "VISIBLE_POPULARITY_COUNT",
    },
    "SUPPLY": {"SEARCH_RESULTS_COUNT", "VISIBLE_CONTRIBUTOR_COUNT", "ASSET_TYPE_MIX_RATIO"},
    "COMPETITION": {"SPONSORED_RESULT_SHARE", "TOP_RESULT_CONCENTRATION_RATIO", "EXACT_PHRASE_RESULT_COUNT"},
    "COMMERCIAL_INTENT": {"BUYER_TERM_PRESENCE", "LICENSE_SURFACE_PRESENCE", "VISIBLE_PRICE_POINT"},
    "TREND": {"TREND_INDEX", "TREND_DELTA", "SEASONALITY_INDEX"},
    "PLATFORM_FIT": {"CONTENT_TYPE_SURFACE_PRESENCE", "FILTER_OPTION_PRESENCE", "AI_LABEL_SURFACE_PRESENCE"},
}

VALUE_KIND_BY_TYPE = {
    "AUTOCOMPLETE_PRESENCE": "BOOLEAN", "AUTOCOMPLETE_RANK": "RANK",
    "RELATED_QUERY_PRESENCE": "BOOLEAN", "SEARCH_INTEREST_INDEX": "INDEX",
    "SEARCH_INTEREST_DELTA": "DELTA", "VISIBLE_DOWNLOAD_COUNT": "COUNT",
    "VISIBLE_POPULARITY_COUNT": "COUNT", "SEARCH_RESULTS_COUNT": "COUNT",
    "VISIBLE_CONTRIBUTOR_COUNT": "COUNT", "ASSET_TYPE_MIX_RATIO": "RATIO",
    "SPONSORED_RESULT_SHARE": "RATIO", "TOP_RESULT_CONCENTRATION_RATIO": "RATIO",
    "EXACT_PHRASE_RESULT_COUNT": "COUNT", "BUYER_TERM_PRESENCE": "BOOLEAN",
    "LICENSE_SURFACE_PRESENCE": "BOOLEAN", "VISIBLE_PRICE_POINT": "TEXT",
    "TREND_INDEX": "INDEX", "TREND_DELTA": "DELTA", "SEASONALITY_INDEX": "INDEX",
    "CONTENT_TYPE_SURFACE_PRESENCE": "BOOLEAN", "FILTER_OPTION_PRESENCE": "BOOLEAN",
    "AI_LABEL_SURFACE_PRESENCE": "BOOLEAN",
}

POLICY_METHODS = {
    "ALLOWED_BOUNDED": {
        "OFFICIAL_API", "PUBLIC_WEB_DOCUMENT", "PUBLIC_SEARCH_UI", "CONTRIBUTOR_UI",
        "MANUAL_OPERATOR", "OPERATOR_EVIDENCE_IMPORT",
    },
    "OPERATOR_REQUIRED": {"MANUAL_OPERATOR", "OPERATOR_EVIDENCE_IMPORT"},
    "OFFICIAL_API_ONLY": {"OFFICIAL_API"},
    "SYNTHETIC_ONLY": {"SYNTHETIC_FIXTURE"},
}


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


def validate(payload: dict[str, Any], schema: dict[str, Any], *, as_of: dt.datetime | None = None) -> list[str]:
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "$"
        errors.append(f"E_SCHEMA:{path}:{err.message}")
    if errors:
        return errors

    observed = parse_time(payload["observed_at"])
    recorded = parse_time(payload["recorded_at"])
    expires = parse_time(payload["expires_at"])
    if observed > recorded:
        errors.append("E_TIME_ORDER:observed_at_after_recorded_at")
    if expires <= recorded:
        errors.append("E_TIME_ORDER:expires_at_not_after_recorded_at")
    actual_window = int((expires - recorded).total_seconds())
    if actual_window != payload["freshness_window_seconds"]:
        errors.append("E_FRESHNESS_WINDOW:mismatch")

    check_time = as_of.astimezone(dt.timezone.utc) if as_of else dt.datetime.now(dt.timezone.utc)
    if check_time >= expires:
        errors.append("E_SIGNAL_STALE:expired")

    policy = payload["policy"]["classification"]
    method = payload["acquisition_method"]
    if method not in POLICY_METHODS[policy]:
        errors.append(f"E_POLICY_METHOD:{policy}:{method}")

    label = payload["evidence_label"]
    source_id = payload["source"]["source_id"]
    if label == "SYNTHETIC":
        if method != "SYNTHETIC_FIXTURE" or policy != "SYNTHETIC_ONLY" or source_id != "SYNTHETIC_FIXTURE":
            errors.append("E_SYNTHETIC_BOUNDARY:fixture_mismatch")
        if payload["cost_usd"] != 0:
            errors.append("E_SYNTHETIC_BOUNDARY:fixture_cost_nonzero")
    elif method == "SYNTHETIC_FIXTURE" or source_id == "SYNTHETIC_FIXTURE" or policy == "SYNTHETIC_ONLY":
        errors.append("E_SYNTHETIC_BOUNDARY:live_label_on_fixture")

    signal_class = payload["signal_class"]
    signal_type = payload["signal_type"]
    if signal_type not in CLASS_TYPES[signal_class]:
        errors.append(f"E_SIGNAL_CLASS_TYPE:{signal_class}:{signal_type}")
    expected_kind = VALUE_KIND_BY_TYPE[signal_type]
    if payload["value"]["kind"] != expected_kind:
        errors.append(f"E_SIGNAL_VALUE_KIND:{signal_type}:expected_{expected_kind}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("receipt")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--as-of", default=None, help="ISO-8601 evaluation time; defaults to now")
    args = ap.parse_args()
    payload = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    as_of = parse_time(args.as_of) if args.as_of else None
    errors = validate(payload, schema, as_of=as_of)
    result = {
        "schema": "die.division001.opportunity-signal-validation.v1",
        "receipt_schema": payload.get("schema_version"),
        "signal_id": payload.get("signal_id"),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
