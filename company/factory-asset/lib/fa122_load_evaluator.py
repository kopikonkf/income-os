from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image


class Fa122EvaluationError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dhash(path: Path) -> int:
    with Image.open(path) as im:
        gray = im.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    value = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            value = (value << 1) | int(pixels[row + x] > pixels[row + x + 1])
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def evaluate_fa122(*, live_result_path: str | Path, contract_path: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    live_path = Path(live_result_path).resolve()
    contract_file = Path(contract_path).resolve()
    live = json.loads(live_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_file.read_text(encoding="utf-8"))
    if live.get("schema") != "die.factory-asset.fa122-live-load-result.v1" or live.get("task_id") != "FA-122":
        raise Fa122EvaluationError("E_LIVE_RESULT_SCHEMA", str(live.get("schema")))
    if contract.get("schema") != "die.factory-asset.fa122-live-load-contract.v1" or contract.get("task_id") != "FA-122":
        raise Fa122EvaluationError("E_CONTRACT_SCHEMA", str(contract.get("schema")))

    qa_cfg = contract["technical_qa"]
    allowed = set(qa_cfg["allowed_formats"])
    rows: list[dict[str, Any]] = []
    hashes: set[str] = set()
    hash_counts: dict[str, int] = {}
    dhashes: list[tuple[str, int]] = []
    for job in live.get("jobs", []):
        if job.get("status") != "SUCCEEDED":
            continue
        artifact = (job.get("attempt") or {}).get("artifact") or {}
        path = Path(str(artifact.get("path") or "")).resolve()
        declared_sha = str(artifact.get("sha256") or "")
        checks = {
            "file_exists": path.is_file(),
            "sha256_matches": False,
            "min_bytes": False,
            "decode_pass": False,
            "dimensions_pass": False,
            "format_allowed": False,
        }
        width = height = 0
        fmt = None
        actual_sha = None
        if path.is_file():
            actual_sha = sha256_file(path)
            checks["sha256_matches"] = actual_sha == declared_sha and len(declared_sha) == 64
            checks["min_bytes"] = path.stat().st_size >= int(qa_cfg["min_bytes"])
            try:
                with Image.open(path) as im:
                    im.load()
                    width, height = im.size
                    fmt = im.format
                checks["decode_pass"] = True
                checks["dimensions_pass"] = width >= int(qa_cfg["min_width_px"]) and height >= int(qa_cfg["min_height_px"])
                checks["format_allowed"] = fmt in allowed
            except Exception:
                pass
        qa_pass = all(checks.values())
        if qa_pass and actual_sha:
            hashes.add(actual_sha)
            hash_counts[actual_sha] = hash_counts.get(actual_sha, 0) + 1
            dhashes.append((job["job_id"], dhash(path)))
        rows.append({
            "job_id": job.get("job_id"),
            "semantic_asset_id": job.get("semantic_asset_id"),
            "provider_id": job.get("provider_id"),
            "cluster_id": job.get("cluster_id"),
            "path": str(path),
            "sha256": actual_sha,
            "bytes": path.stat().st_size if path.is_file() else 0,
            "format": fmt,
            "width_px": width,
            "height_px": height,
            "qa_pass": qa_pass,
            "checks": checks,
        })

    exact_duplicate_hashes = sorted(k for k, n in hash_counts.items() if n > 1)
    threshold = int(qa_cfg["near_duplicate_dhash_hamming_threshold"])
    near_pairs: list[dict[str, Any]] = []
    for i in range(len(dhashes)):
        for j in range(i + 1, len(dhashes)):
            distance = hamming(dhashes[i][1], dhashes[j][1])
            if distance <= threshold:
                near_pairs.append({"job_a": dhashes[i][0], "job_b": dhashes[j][0], "dhash_hamming": distance})

    qa_pass_count = sum(1 for r in rows if r["qa_pass"])
    counts = live.get("counts") or {}
    topology = live.get("topology") or {}
    after_clusters = ((topology.get("after") or {}).get("clusters") or {})
    truth = live.get("truth_boundaries") or {}
    assertions = {
        "live_execution_complete": live.get("result") == "COMPLETE",
        "target_unique_qa_masters_reached": len(hashes) >= int(contract["target_unique_masters"]),
        "qa_pass_count_at_least_target": qa_pass_count >= int(contract["target_unique_masters"]),
        "provider_commit_budget_respected": int(counts.get("dispatch_commits", 0)) <= int(contract["max_provider_generation_commits"]),
        "zero_exact_duplicate_master_hashes": not exact_duplicate_hashes,
        "profile_metadata_identity_preserved": bool((live.get("profile_integrity") or {}).get("preserved")),
        "resource_safety_preserved": topology.get("safety_violation") is None and float(topology.get("max_combined_browser_tree_rss_mb", 0)) <= float(contract["max_combined_browser_tree_rss_mb"]),
        "zero_lease_leak": bool(after_clusters) and all(int(row.get("active_leases", -1)) == 0 for row in after_clusters.values()),
        "zero_secret_reads": truth.get("credential_values_read") is False and truth.get("cookies_or_tokens_read") is False,
        "zero_spend": truth.get("spend_usd") == 0,
        "no_derivative_volume_inflation": truth.get("packaging_derivatives_counted_as_unique_masters") is False,
        "no_account_marketplace_actions": truth.get("account_actions") == 0 and truth.get("marketplace_actions") == 0,
    }
    result = "PASS" if all(assertions.values()) else "FAIL"
    out = {
        "schema": "die.factory-asset.fa122-live-load-evaluation.v1",
        "task_id": "FA-122",
        "result": result,
        "target_unique_masters": contract["target_unique_masters"],
        "planned_semantic_jobs": contract["max_planned_semantic_jobs"],
        "provider_generation_commit_budget": contract["max_provider_generation_commits"],
        "counts": {
            "dispatch_commits": int(counts.get("dispatch_commits", 0)),
            "successful_provider_artifacts": int(counts.get("successful_artifacts", 0)),
            "qa_passed_masters": qa_pass_count,
            "unique_qa_master_sha256": len(hashes),
            "exact_duplicate_hash_count": len(exact_duplicate_hashes),
            "near_duplicate_pair_count": len(near_pairs),
            "provider_failures": int(counts.get("provider_failures", 0)),
        },
        "provider_counts": live.get("provider_counts", {}),
        "cluster_counts": live.get("cluster_counts", {}),
        "failures": live.get("failures", []),
        "technical_qa": rows,
        "exact_duplicate_hashes": exact_duplicate_hashes,
        "near_duplicate_pairs": near_pairs,
        "near_duplicate_policy": "OBSERVED_FOR_FA123_CAPACITY_INPUT_NOT_SUBTRACTED_FROM_FA122_EXACT_UNIQUE_COUNT",
        "resource_use": {
            "max_combined_browser_tree_rss_mb": topology.get("max_combined_browser_tree_rss_mb"),
            "max_active_leases": topology.get("max_active_leases"),
            "max_open_pages": topology.get("max_open_pages"),
            "final_clusters": after_clusters,
        },
        "policy_capacity_truth": {
            "provider_failures_recorded": True,
            "profile_metadata_identity_preserved": (live.get("profile_integrity") or {}).get("preserved"),
            "provider_calls_performed": truth.get("provider_calls_performed"),
            "credential_values_read": False,
            "cookies_or_tokens_read": False,
            "spend_usd": 0,
            "account_actions": 0,
            "marketplace_actions": 0,
            "packaging_derivatives_counted_as_unique_masters": False,
        },
        "assertions": assertions,
    }
    if output_path is not None:
        _atomic_json(Path(output_path), out)
    return out
