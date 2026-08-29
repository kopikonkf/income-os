#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
VALIDATOR_PATH = ROOT / "validate_demand_score.py"
SCHEMA_PATH = ROOT / "die.division001.demand-score.v1.schema.json"
MODEL_PATH = ROOT / "DEMAND_SCORE_MODEL_V1.contract.json"
CONF_RANK = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


class RankError(RuntimeError):
    pass


def _load_validator():
    spec = importlib.util.spec_from_file_location("oe002_rank_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RankError("cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def rank(scores: list[dict[str, Any]]) -> dict[str, Any]:
    validator = _load_validator()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    rankable: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for payload in scores:
        errors = validator.validate(payload, schema, model)
        if errors:
            raise RankError("E_SCORE_INVALID:" + " | ".join(errors))
        score_id = payload["score_id"]
        digest = _canonical_sha(payload)
        if score_id in seen:
            if seen[score_id] == digest:
                continue
            raise RankError(f"E_SCORE_ID_CONFLICT:{score_id}")
        seen[score_id] = digest
        if payload["score_status"] == "COMPLETE" and payload["final_score"] is not None:
            rankable.append(payload)
        else:
            deferred.append({
                "score_id": score_id,
                "subject_id": payload["subject"]["id"],
                "score_status": payload["score_status"],
                "required_coverage_ratio": payload["required_coverage_ratio"],
                "evidence_coverage_ratio": payload["evidence_coverage_ratio"],
                "hard_veto_status": payload["hard_veto"]["status"],
            })

    rankable.sort(key=lambda p: (-float(p["final_score"]), -CONF_RANK[p["confidence"]], p["score_id"]))
    ranked=[]
    for idx,payload in enumerate(rankable, start=1):
        ranked.append({
            "rank":idx,
            "score_id":payload["score_id"],
            "subject_id":payload["subject"]["id"],
            "final_score":payload["final_score"],
            "confidence":payload["confidence"],
            "evidence_coverage_ratio":payload["evidence_coverage_ratio"],
            "known_weight_ratio":payload["known_weight_ratio"],
            "score_sha256":_canonical_sha(payload),
        })
    deferred.sort(key=lambda row:(row["score_status"], row["score_id"]))
    return {
        "schema":"die.division001.demand-ranking.v1",
        "model_id":model["model_id"],
        "model_version":model["model_version"],
        "model_contract_sha256":hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
        "ranked_count":len(ranked),
        "deferred_count":len(deferred),
        "ranked":ranked,
        "deferred":deferred,
        "policy":"Only COMPLETE numeric scores are rankable; non-complete scores are deferred without artificial numeric imputation.",
    }


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("scores", nargs="+"); ap.add_argument("--output")
    args=ap.parse_args()
    try:
        payloads=[json.loads(Path(p).read_text(encoding="utf-8")) for p in args.scores]
        result=rank(payloads)
    except (OSError,json.JSONDecodeError,RankError) as exc:
        print(json.dumps({"schema":"die.division001.demand-ranking-run.v1","status":"FAIL","error":str(exc)},indent=2)); return 2
    text=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if args.output: Path(args.output).write_text(text,encoding="utf-8",newline="\n")
    else: print(text,end="")
    return 0

if __name__=="__main__": raise SystemExit(main())
