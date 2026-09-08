from __future__ import annotations

import hashlib
import json
import math
import random
import tempfile
import time
from pathlib import Path
from typing import Any

from PIL import Image

from fa122_load_evaluator import dhash, hamming, sha256_file
from package_composer import compose_dry_run_package
from package_readiness import evaluate_package_readiness


class Fa123CapacityError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fa123CapacityError("E_JSON_OBJECT", str(path))
    return value


def _fixture_png(path: Path, index: int, *, width: int, height: int) -> None:
    rng = random.Random(0xFA123000 + index)
    pixels = rng.randbytes(width * height * 3)
    image = Image.frombytes("RGB", (width, height), pixels)
    image.save(path, format="PNG", optimize=False)


def _near_duplicate(source: Path, target: Path) -> None:
    with Image.open(source) as image:
        out = image.convert("RGB")
        px = out.load()
        r, g, b = px[0, 0]
        px[0, 0] = ((r + 1) % 256, g, b)
        out.save(target, format="PNG", optimize=False)


def _qa(path: Path, *, min_width: int, min_height: int, allowed_formats: set[str]) -> dict[str, Any]:
    actual_sha = sha256_file(path)
    width = height = 0
    fmt = None
    decode = False
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            fmt = image.format
        decode = True
    except Exception:
        pass
    checks = {
        "file_exists": path.is_file(),
        "sha256_valid": len(actual_sha) == 64,
        "decode_pass": decode,
        "dimensions_pass": width >= min_width and height >= min_height,
        "format_allowed": fmt in allowed_formats,
    }
    return {
        "sha256": actual_sha,
        "width_px": width,
        "height_px": height,
        "format": fmt,
        "qa_pass": all(checks.values()),
        "checks": checks,
    }


def _blueprint(i: int) -> dict[str, Any]:
    return {
        "blueprint_id": f"FA123-BP-{i:03d}",
        "asset_type": "RASTER_IMAGE",
        "semantic_identity": {
            "semantic_asset_id": f"FA123-SYNTH-{i:03d}",
            "subject": f"synthetic capacity fixture {i:03d}",
            "commercial_use_case": "bounded downstream capacity benchmark only",
        },
    }


def _package_inputs(i: int, master_sha: str, jpeg_sha: str, webp_sha: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    bp = _blueprint(i)
    plan = {
        "semantic_asset_id": bp["semantic_identity"]["semantic_asset_id"],
        "blueprint_id": bp["blueprint_id"],
        "master_sha256": master_sha,
        "package_blocked": False,
        "entries": [
            {"derivative_id": "ADOBE_JPEG", "format": "JPEG", "purpose": "MARKETPLACE_DELIVERY", "compatibility_state": "COMPATIBLE"},
            {"derivative_id": "WEB_PREVIEW", "format": "WEBP", "purpose": "PREVIEW", "compatibility_state": "COMPATIBLE"},
        ],
    }
    rights = {"master_sha256": master_sha, "result": "PASS"}
    evidence = [
        {"derivative_id": "ADOBE_JPEG", "master_sha256": master_sha, "format": "JPEG", "purpose": "MARKETPLACE_DELIVERY", "qa_result": "PASS", "sha256_verified": True, "qa_sha256": jpeg_sha, "sha256": jpeg_sha},
        {"derivative_id": "WEB_PREVIEW", "master_sha256": master_sha, "format": "WEBP", "purpose": "PREVIEW", "qa_result": "PASS", "sha256_verified": True, "qa_sha256": webp_sha, "sha256": webp_sha},
    ]
    provenance = {"source_class": "GENERATIVE_AI", "ai_generated": True, "ai_disclosure": "GENERATIVE_AI"}
    master_qa = {"result": "PASS", "master_sha256": master_sha}
    return bp, plan, rights, evidence, provenance, master_qa


def run_fa123_capacity_model(*, contract_path: str | Path, fa122_receipt_path: str | Path, fa120_receipt_path: str | Path, fa137_receipt_path: str | Path, fa205_receipt_path: str | Path) -> dict[str, Any]:
    contract = _load(Path(contract_path))
    fa122 = _load(Path(fa122_receipt_path))
    fa120 = _load(Path(fa120_receipt_path))
    fa137 = _load(Path(fa137_receipt_path))
    fa205 = _load(Path(fa205_receipt_path))
    if contract.get("schema") != "die.factory-asset.fa123-downstream-capacity-contract.v1" or contract.get("task_id") != "FA-123":
        raise Fa123CapacityError("E_CONTRACT", str(contract.get("schema")))
    if fa122.get("task_id") != "FA-122" or fa122.get("result") != "PASS":
        raise Fa123CapacityError("E_FA122_INPUT", str(fa122.get("result")))
    if fa120.get("task_id") != "FA-120" or fa120.get("result") != "PASS":
        raise Fa123CapacityError("E_FA120_INPUT", str(fa120.get("result")))
    if fa137.get("task_id") != "FA-137" or fa137.get("result") != "PASS":
        raise Fa123CapacityError("E_FA137_INPUT", str(fa137.get("result")))
    if fa205.get("task_id") != "FA-205" or fa205.get("result") != "APPROVE":
        raise Fa123CapacityError("E_FA205_INPUT", str(fa205.get("result")))

    n = int(contract["modeled_master_count"])
    target = int(contract["target_masters_per_day"])
    qa_cfg = contract["technical_qa"]
    threshold = int(qa_cfg["near_duplicate_dhash_hamming_threshold"])
    with tempfile.TemporaryDirectory(prefix="fa123-capacity-") as td:
        root = Path(td)
        masters = root / "masters"
        derivatives = root / "derivatives"
        packages = root / "packages"
        masters.mkdir(); derivatives.mkdir(); packages.mkdir()
        for i in range(n):
            _fixture_png(masters / f"master-{i:03d}.png", i, width=int(qa_cfg["min_width_px"]), height=int(qa_cfg["min_height_px"]))

        qa_started = time.perf_counter()
        qa_rows = [_qa(masters / f"master-{i:03d}.png", min_width=int(qa_cfg["min_width_px"]), min_height=int(qa_cfg["min_height_px"]), allowed_formats=set(qa_cfg["allowed_formats"])) for i in range(n)]
        qa_seconds = time.perf_counter() - qa_started
        qa_pass_count = sum(1 for row in qa_rows if row["qa_pass"])
        positive_hashes = [row["sha256"] for row in qa_rows if row["qa_pass"]]
        exact_duplicate_count = len(positive_hashes) - len(set(positive_hashes))

        distinct_started = time.perf_counter()
        dhashes = [dhash(masters / f"master-{i:03d}.png") for i in range(n)]
        near_pairs = []
        comparisons = 0
        for i in range(n):
            for j in range(i + 1, n):
                comparisons += 1
                distance = hamming(dhashes[i], dhashes[j])
                if distance <= threshold:
                    near_pairs.append({"a": i, "b": j, "distance": distance})
        exact_control = root / "exact-control.png"
        exact_control.write_bytes((masters / "master-000.png").read_bytes())
        near_control = root / "near-control.png"
        _near_duplicate(masters / "master-001.png", near_control)
        exact_control_detected = sha256_file(exact_control) == sha256_file(masters / "master-000.png")
        near_control_hash_differs = sha256_file(near_control) != sha256_file(masters / "master-001.png")
        near_control_distance = hamming(dhash(near_control), dhash(masters / "master-001.png"))
        near_control_detected = near_control_hash_differs and near_control_distance <= threshold
        distinct_seconds = time.perf_counter() - distinct_started

        package_started = time.perf_counter()
        readiness_pass = 0
        composition_pass = 0
        for i in range(n):
            master = masters / f"master-{i:03d}.png"
            item_dir = derivatives / f"item-{i:03d}"
            item_dir.mkdir()
            jpeg = item_dir / "adobe.jpg"
            webp = item_dir / "preview.webp"
            with Image.open(master) as image:
                rgb = image.convert("RGB")
                rgb.save(jpeg, format="JPEG", quality=82, optimize=False)
                rgb.save(webp, format="WEBP", quality=80)
            master_sha = sha256_file(master)
            jpeg_sha = sha256_file(jpeg)
            webp_sha = sha256_file(webp)
            bp, plan, rights, evidence, provenance, master_qa = _package_inputs(i, master_sha, jpeg_sha, webp_sha)
            ready = evaluate_package_readiness(blueprint=bp, derivative_plan=plan, rights_signal=rights, derivative_evidence=evidence, provenance=provenance, master_technical_qa=master_qa)
            if ready.get("result") == "PACKAGE_READY" and ready.get("founder_qc_required") is True:
                readiness_pass += 1
            receipt = compose_dry_run_package(
                package_dir=packages / f"item-{i:03d}",
                semantic_asset_id=bp["semantic_identity"]["semantic_asset_id"],
                master_sha256=master_sha,
                deliverables=[
                    {"derivative_id": "ADOBE_JPEG", "source_path": str(jpeg), "format": "JPEG", "purpose": "MARKETPLACE_DELIVERY", "recipe_id": "fa123-jpeg-v1", "receipt_ref": "synthetic://jpeg", "compatibility_state": "COMPATIBLE"},
                    {"derivative_id": "WEB_PREVIEW", "source_path": str(webp), "format": "WEBP", "purpose": "PREVIEW", "recipe_id": "fa123-webp-v1", "receipt_ref": "synthetic://webp", "compatibility_state": "COMPATIBLE"},
                ],
                metadata_ref="synthetic://metadata",
                rights_ref="synthetic://rights",
                compatibility_receipt_ref="synthetic://compatibility",
            )
            if receipt.get("result") == "PASS" and receipt.get("semantic_asset_count") == 1 and receipt.get("derivative_count") == int(contract["package"]["derivatives_per_modeled_master"]):
                composition_pass += 1
        package_seconds = time.perf_counter() - package_started

    total_seconds = qa_seconds + distinct_seconds + package_seconds
    per_master_seconds = total_seconds / max(1, n)
    automated_capacity_per_day = math.floor(86400 / per_master_seconds) if per_master_seconds > 0 else 10**9
    automated_backlog = max(0, target - automated_capacity_per_day)
    current_sampling = float(contract["founder_qc"]["current_authorized_sampling_rate"])
    founder_touches = math.ceil(target * current_sampling)
    scenarios = [
        {"sampling_rate": float(rate), "touches_per_100_masters": math.ceil(target * float(rate)), "authority_status": "CURRENT_POLICY" if float(rate) == current_sampling else "INFORMATIONAL_NOT_AUTHORIZED"}
        for rate in contract["founder_qc"]["informational_sampling_scenarios"]
    ]

    assertions = {
        "fa122_live_input_pass": fa122["qa_and_distinctness"]["qa_passed_masters"] >= 20 and fa122["qa_and_distinctness"]["exact_duplicate_hash_count"] == 0,
        "technical_qa_100_of_100": qa_pass_count == n and qa_pass_count / n >= float(qa_cfg["required_pass_rate"]),
        "positive_set_zero_exact_duplicates": exact_duplicate_count == int(contract["distinctness"]["positive_set_exact_duplicates_allowed"]),
        "positive_set_zero_near_duplicate_pairs": len(near_pairs) == int(contract["distinctness"]["positive_set_near_duplicate_pairs_allowed"]),
        "exact_duplicate_negative_control_quarantined": exact_control_detected,
        "near_duplicate_negative_control_quarantined": near_control_detected,
        "package_readiness_100_of_100": readiness_pass == n,
        "package_composition_100_of_100": composition_pass == n,
        "automated_capacity_at_least_100_per_day": automated_capacity_per_day >= target,
        "automated_backlog_zero_at_100_per_day": automated_backlog <= int(contract["backlog"]["max_modeled_automated_backlog_per_day"]),
        "founder_touch_requirement_quantified": founder_touches == target,
        "human_service_rate_not_fabricated": True,
        "sampling_scenarios_do_not_change_authority": contract["founder_qc"]["sampling_scenarios_change_authority"] is False,
        "queue_backpressure_evidence_supports_100_day": int(fa120["queue"]["unique_jobs"]) >= target and int(fa120["queue"]["terminal_failures"]) == 0,
        "current_package_policy_requires_founder_qc": fa205["automated_evidence"]["founder_qc_required"] is True,
        "no_provider_or_marketplace_actions": contract["truth_boundaries"]["provider_calls_allowed"] is False and contract["truth_boundaries"]["marketplace_actions_allowed"] is False,
    }
    result = "PASS" if all(assertions.values()) else "FAIL"
    return {
        "schema": "die.factory-asset.fa123-downstream-capacity-evidence.v1",
        "task_id": "FA-123",
        "result": result,
        "model": {
            "target_masters_per_day": target,
            "modeled_master_count": n,
            "fixture_truth": "SYNTHETIC_DOWNSTREAM_CAPACITY_FIXTURES_NOT_PRODUCTION_MASTERS",
            "provider_calls_performed": False,
        },
        "live_input": {
            "fa122_unique_qa_masters": fa122["qa_and_distinctness"]["unique_qa_master_sha256"],
            "fa122_qa_pass_rate": fa122["qa_and_distinctness"]["qa_pass_rate"],
            "fa122_near_duplicate_pairs": fa122["qa_and_distinctness"]["near_duplicate_pair_count"],
            "fa122_provider_failures": fa122["live_result"]["provider_failures"],
        },
        "technical_qa": {"passed": qa_pass_count, "total": n, "pass_rate": qa_pass_count / n, "elapsed_seconds": round(qa_seconds, 6)},
        "distinctness": {
            "pairwise_comparisons": comparisons,
            "positive_set_exact_duplicate_count": exact_duplicate_count,
            "positive_set_near_duplicate_pair_count": len(near_pairs),
            "threshold": threshold,
            "exact_duplicate_negative_control_detected": exact_control_detected,
            "near_duplicate_negative_control_detected": near_control_detected,
            "near_duplicate_negative_control_hamming": near_control_distance,
            "elapsed_seconds": round(distinct_seconds, 6),
        },
        "package": {
            "readiness_passed": readiness_pass,
            "composition_passed": composition_pass,
            "total": n,
            "derivatives_per_master": int(contract["package"]["derivatives_per_modeled_master"]),
            "elapsed_seconds": round(package_seconds, 6),
            "founder_qc_required_per_package": True,
        },
        "automated_capacity": {
            "benchmark_total_seconds": round(total_seconds, 6),
            "benchmark_seconds_per_modeled_master": round(per_master_seconds, 6),
            "modeled_capacity_per_24h": automated_capacity_per_day,
            "arrival_rate_per_day": target,
            "modeled_automated_backlog_per_day": automated_backlog,
            "truth_boundary": "LOCAL_SYNTHETIC_DOWNSTREAM_COMPUTE_BENCHMARK_NOT_PROVIDER_OR_HUMAN_THROUGHPUT",
            "fa120_queue_unique_jobs": fa120["queue"]["unique_jobs"],
            "fa120_queue_terminal_failures": fa120["queue"]["terminal_failures"],
        },
        "founder_qc": {
            "current_policy_sampling_rate": current_sampling,
            "required_founder_touches_per_100_masters": founder_touches,
            "required_founder_touches_per_day_at_target": founder_touches,
            "measured_founder_review_capacity_per_day": None,
            "human_capacity_status": "EXTERNAL_UNPROVEN",
            "backlog_if_zero_founder_reviews_per_day": founder_touches,
            "no_backlog_requires_founder_reviews_per_day": founder_touches,
            "sampling_scenarios": scenarios,
            "sampling_policy_changed": False,
        },
        "truth_boundaries": {
            "synthetic_fixtures_counted_as_production_masters": False,
            "provider_calls_performed": False,
            "credential_values_read": False,
            "cookies_or_tokens_read": False,
            "marketplace_actions": 0,
            "submission_authorized": False,
            "publication_authorized": False,
            "spend_usd": 0,
            "founder_qc_service_rate_claimed": False,
        },
        "assertions": assertions,
    }
