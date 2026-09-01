"""Deterministic UP-001 upscale/recovery boundary.

Enforces rights/safety gates, model hash pinning, no-op recovery,
input/output lineage and x4 dimension verification around an external
RealESRGAN backend. Rights/safety failures are never technically recoverable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from typing import Any

RECEIPT_SCHEMA = "die.asset.upscale.v1"
POLICY_SCHEMA = "die.asset.upscale-policy.v1"


class UpscaleError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int, str]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h, "PNG"
    if data[:2] == b"\xff\xd8":
        i = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while i + 4 <= len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if i + 2 > len(data):
                break
            size = struct.unpack(">H", data[i:i + 2])[0]
            if size < 2 or i + size > len(data):
                break
            if marker in sof and size >= 7:
                h, w = struct.unpack(">HH", data[i + 3:i + 7])
                return w, h, "JPEG"
            i += size
    raise UpscaleError(f"E_UNSUPPORTED_RASTER:{path}")


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema", "engine", "model_name", "model_path", "model_sha256",
        "scale", "tile", "tile_pad", "pre_pad", "half", "gpu_id", "backend_argv",
    }
    if not isinstance(policy, dict) or set(policy) != required or policy.get("schema") != POLICY_SCHEMA:
        raise UpscaleError("E_POLICY_SHAPE")
    if policy["scale"] != 4 or policy["half"] is not False or policy["gpu_id"] is not None:
        raise UpscaleError("E_POLICY_NOT_CPU_X4")
    if len(str(policy["model_sha256"])) != 64:
        raise UpscaleError("E_MODEL_PIN")
    if not isinstance(policy["backend_argv"], list) or not policy["backend_argv"]:
        raise UpscaleError("E_BACKEND_ARGV")
    return policy


def needs_upscale(width: int, height: int, min_width: int, min_height: int, min_megapixels: float) -> bool:
    return width < min_width or height < min_height or (width * height) / 1_000_000 < min_megapixels


def process(
    *, source: Path, output: Path, policy: dict[str, Any], min_width: int,
    min_height: int, min_megapixels: float, rights_state: str = "CLEAR",
    safety_state: str = "CLEAR", timeout_sec: int = 900,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    model = Path(policy["model_path"])
    if not source.is_file():
        raise UpscaleError("E_SOURCE_MISSING")
    width, height, fmt = image_dimensions(source)
    source_hash = sha256(source)
    base = {
        "schema": RECEIPT_SCHEMA,
        "source": {"path": str(source), "sha256": source_hash, "width": width, "height": height, "format": fmt},
        "technical_requirement": {"min_width": min_width, "min_height": min_height, "min_megapixels": min_megapixels},
        "rights_state": rights_state,
        "safety_state": safety_state,
        "authority_boundary": {"rights_or_safety_recoverable": False, "submission_authorized": False, "publication_authorized": False},
    }
    if rights_state not in {"CLEAR", "PASS"} or safety_state not in {"CLEAR", "PASS"}:
        return {**base, "status": "BLOCKED_RIGHTS_SAFETY", "action": "BLOCK", "transformed": False, "output": None, "model": None}
    if not needs_upscale(width, height, min_width, min_height, min_megapixels):
        return {
            **base, "status": "PASS", "action": "NO_OP", "transformed": False,
            "output": {"path": str(source), "sha256": source_hash, "width": width, "height": height, "format": fmt},
            "model": None,
            "checks": {"technical_requirement_satisfied": True, "lineage_hash_changed": False},
        }
    if not model.is_file():
        return {
            **base, "status": "BLOCKED_RUNTIME", "action": "UPSCALE_X4", "transformed": False, "output": None,
            "model": {"name": policy["model_name"], "path": str(model), "expected_sha256": policy["model_sha256"], "present": False},
        }
    actual_model_hash = sha256(model)
    if actual_model_hash != policy["model_sha256"]:
        raise UpscaleError("E_MODEL_HASH_MISMATCH")
    output.parent.mkdir(parents=True, exist_ok=True)
    argv = [str(x).format(input=str(source), output=str(output), model=str(model)) for x in policy["backend_argv"]]
    completed = subprocess.run(argv, text=True, capture_output=True, timeout=timeout_sec, check=False)
    if completed.returncode != 0 or not output.is_file():
        return {
            **base, "status": "FAILED_BACKEND", "action": "UPSCALE_X4", "transformed": False, "output": None,
            "model": {"name": policy["model_name"], "path": str(model), "sha256": actual_model_hash},
            "backend": {"argv0": argv[0], "returncode": completed.returncode, "stderr": completed.stderr[-1000:]},
        }
    out_width, out_height, out_fmt = image_dimensions(output)
    out_hash = sha256(output)
    if out_width != width * 4 or out_height != height * 4:
        raise UpscaleError(f"E_DIMENSION_REGRESSION:{width}x{height}->{out_width}x{out_height}")
    return {
        **base, "status": "PASS", "action": "UPSCALE_X4", "transformed": True,
        "output": {"path": str(output), "sha256": out_hash, "width": out_width, "height": out_height, "format": out_fmt},
        "model": {"name": policy["model_name"], "path": str(model), "sha256": actual_model_hash},
        "backend": {"argv0": argv[0], "returncode": 0},
        "checks": {"x4_dimensions": True, "output_nonempty": output.stat().st_size > 0, "lineage_hash_changed": out_hash != source_hash},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--min-width", type=int, default=0)
    ap.add_argument("--min-height", type=int, default=0)
    ap.add_argument("--min-megapixels", type=float, default=0)
    ap.add_argument("--rights-state", default="CLEAR")
    ap.add_argument("--safety-state", default="CLEAR")
    args = ap.parse_args()
    receipt = process(
        source=Path(args.source), output=Path(args.output), policy=load_policy(Path(args.policy)),
        min_width=args.min_width, min_height=args.min_height, min_megapixels=args.min_megapixels,
        rights_state=args.rights_state, safety_state=args.safety_state,
    )
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "action": receipt["action"]}))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
