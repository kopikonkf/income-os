#!/usr/bin/env python3
"""Bounded Human Atlas demand-context retrieval adapter v1."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "HUMAN_CONTEXT_REGISTRY_V1.json"
SCHEMA_PATH = ROOT / "die.human-atlas.context-registry.v1.schema.json"
MAX_RESULTS = 25
ALLOWED_KEYS = {"object_name","human","activity","place","industry","commercial_intent","problem","limit"}
SEARCH_FIELDS = ["human","activity","place","industry","commercial_intent","problem"]


class ContextRetrievalError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tokens(value: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", value.lower()) if len(x) > 1}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    if a.lower().strip() == b.lower().strip():
        return 1.0
    return len(ta & tb) / len(ta | tb)


def _validate_query(query: dict[str, Any]) -> None:
    extra = set(query) - ALLOWED_KEYS
    if extra:
        raise ContextRetrievalError("E_HCTX_QUERY_KEY:" + ",".join(sorted(extra)))
    limit = query.get("limit", 10)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > MAX_RESULTS:
        raise ContextRetrievalError("E_HCTX_LIMIT")
    if not any(str(query.get(k, "")).strip() for k in ALLOWED_KEYS - {"limit"}):
        raise ContextRetrievalError("E_HCTX_QUERY_UNBOUNDED")


def _load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(payload), key=lambda e:list(e.absolute_path))
    if errors:
        raise ContextRetrievalError("E_HCTX_REGISTRY_SCHEMA:" + errors[0].message)
    ids=[x["context_id"] for x in payload["contexts"]]
    if len(ids) != len(set(ids)):
        raise ContextRetrievalError("E_HCTX_DUPLICATE_ID")
    return payload


def retrieve(query: dict[str, Any], *, registry_path: Path = DEFAULT_REGISTRY, registry_sha256: str | None = None, verify_hash: bool = False) -> dict[str, Any]:
    _validate_query(query)
    registry_path = registry_path.expanduser().resolve()
    if not registry_path.is_file():
        raise ContextRetrievalError("E_HCTX_REGISTRY_MISSING")
    actual_sha = _sha(registry_path)
    if registry_sha256 is None:
        registry_sha256 = actual_sha
    if len(registry_sha256) != 64 or any(c not in "0123456789abcdef" for c in registry_sha256):
        raise ContextRetrievalError("E_HCTX_REGISTRY_SHA256")
    if verify_hash and registry_sha256 != actual_sha:
        raise ContextRetrievalError("E_HCTX_REGISTRY_HASH_MISMATCH")
    registry = _load_registry(registry_path)

    anchors=[k for k in ALLOWED_KEYS - {"limit"} if str(query.get(k, "")).strip()]
    scored=[]
    for ctx in registry["contexts"]:
        contributions=[]
        details={}
        for key in anchors:
            wanted=str(query[key]).strip()
            if key == "object_name":
                sims=[_similarity(wanted,hint) for hint in ctx["object_hints"]]
                score=max(sims) if sims else 0.0
            else:
                score=_similarity(wanted,str(ctx[key]))
            details[key]=round(score,6)
            contributions.append(score)
        # Require at least one meaningful match. Average prevents more anchors from
        # automatically inflating relevance; users can narrow deterministically.
        best=max(contributions) if contributions else 0.0
        avg=sum(contributions)/len(contributions) if contributions else 0.0
        if best <= 0:
            continue
        scored.append((round(avg,6),round(best,6),ctx["context_id"],details,ctx))
    scored.sort(key=lambda row:(-row[0],-row[1],row[2]))
    selected=scored[:query.get("limit",10)]
    results=[]
    for avg,best,_,details,ctx in selected:
        results.append({"context":ctx,"compatibility_score":avg,"best_anchor_score":best,"anchor_scores":details})
    receipt_id="HCTXRET-"+hashlib.sha256(json.dumps({"registry":registry_sha256,"query":query,"ids":[r["context"]["context_id"] for r in results]},sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24].upper()
    return {
      "schema":"die.human-atlas.context-retrieval.v1",
      "receipt_id":receipt_id,
      "registry":{"path_ref":str(registry_path),"sha256":registry_sha256,"version":registry["registry_version"],"status":registry["status"]},
      "query":query,
      "policy":{"max_results":MAX_RESULTS,"exhaustive_cartesian":False,"market_evidence":False,"result_label":"HYPOTHESIS_CONTEXT_COMPATIBILITY"},
      "result_count":len(results),
      "results":results,
    }


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--query",required=True); ap.add_argument("--registry",default=str(DEFAULT_REGISTRY)); ap.add_argument("--registry-sha256"); ap.add_argument("--verify-hash",action="store_true")
    args=ap.parse_args()
    try:
        query=json.loads(Path(args.query).read_text(encoding="utf-8"))
        print(json.dumps(retrieve(query,registry_path=Path(args.registry),registry_sha256=args.registry_sha256,verify_hash=args.verify_hash),indent=2,ensure_ascii=False))
        return 0
    except (OSError,json.JSONDecodeError,ContextRetrievalError) as exc:
        print(json.dumps({"schema":"die.human-atlas.context-retrieval-run.v1","status":"FAIL","error":str(exc)},indent=2)); return 2

if __name__=="__main__": raise SystemExit(main())
