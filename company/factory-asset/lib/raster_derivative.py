"""FA-021: deterministic PNG derivatives; no provider or package authority.

A successful conversion has green QA but remains FAIL/COMPATIBILITY_UNKNOWN
in the FA-020 receipt until a separate compatibility gate accepts the package.
Pre-output errors use RasterDerivativeError: the receipt schema requires real
output bytes, so failures never manufacture placeholder hashes/artifacts.
"""
from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import warnings

import jsonschema
import PIL
from PIL import Image, features

ROOT = Path(__file__).resolve().parents[1]
PILLOW_VERSION = "11.3.0"
ENGINE = "fa021-raster/1.0.0"
MAX_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 25_000_000
EXTENSIONS = {"JPEG": "jpg", "WEBP": "webp", "TIFF": "tif"}


class RasterDerivativeError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code, message):
    raise RasterDerivativeError(code, message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _schema(value, name):
    try:
        jsonschema.Draft202012Validator(_load(ROOT / "schemas" / name)).validate(value)
    except jsonschema.ValidationError as exc:
        _fail("SCHEMA_INVALID", exc.message)


def runtime():
    if PIL.__version__ != PILLOW_VERSION:
        _fail("ENCODER_VERSION_MISMATCH", f"requires Pillow {PILLOW_VERSION}")
    if not features.check("webp") or not features.check("jpg"):
        _fail("ENCODER_UNAVAILABLE", "JPEG and WebP codecs are required")
    return {"engine": ENGINE, "pillow": PIL.__version__,
            "jpeg": features.version("jpg"), "webp": features.version("webp"),
            "tiff": "raw-uncompressed"}


def _validate(recipe):
    _schema(recipe, "derivative-recipe.schema.json")
    if recipe["recipe_version"] != "1.0.0":
        _fail("RECIPE_VERSION_UNSUPPORTED", "this worker implements recipe version 1.0.0")
    if recipe["input"]["format"] != "PNG":
        _fail("INPUT_FORMAT_UNSUPPORTED", "only PNG masters")
    spec = recipe["output"]
    if spec["format"] not in EXTENSIONS:
        _fail("OUTPUT_FORMAT_UNSUPPORTED", "only JPEG, WEBP and TIFF")
    if not {"width_px", "height_px", "alpha_policy", "color_space"} <= spec.keys():
        _fail("RECIPE_INCOMPLETE", "dimensions, alpha policy and color space must be explicit")
    if spec["width_px"] * spec["height_px"] > MAX_PIXELS:
        _fail("OUTPUT_TOO_LARGE", "maximum 25 million pixels")
    if spec["color_space"] != "SRGB":
        _fail("COLOR_POLICY_UNSUPPORTED", "only explicitly tagged sRGB input")
    if spec["alpha_policy"] not in {"PRESERVE", "FLATTEN_WHITE", "FORBID"}:
        _fail("ALPHA_POLICY_UNSUPPORTED", "explicit raster alpha policy required")
    if spec["format"] == "JPEG" and spec["alpha_policy"] == "PRESERVE":
        _fail("ALPHA_FORMAT_CONFLICT", "JPEG cannot preserve alpha")
    if spec["format"] in {"JPEG", "WEBP"} and "quality" not in spec:
        _fail("RECIPE_INCOMPLETE", "lossy quality must be explicit")
    if spec["format"] == "TIFF" and "quality" in spec:
        _fail("QUALITY_NOT_APPLICABLE", "raw TIFF has no quality setting")
    profiles = _load(ROOT / "registries/marketplace-delivery-profiles.v1.json")
    pin = recipe["marketplace_profile"]
    if profiles["revision"] != pin["profile_revision"]:
        _fail("PROFILE_REVISION_MISMATCH", "recipe must pin the loaded registry revision")
    if pin["platform_id"] not in {p["platform_id"] for p in profiles["profiles"]}:
        _fail("PROFILE_UNKNOWN", "unknown marketplace profile")
    material = {"master_sha256": recipe["input"]["master_sha256"],
                "recipe_id": recipe["recipe_id"], "recipe_version": recipe["recipe_version"],
                "marketplace_profile": pin, "output": spec}
    return _hash(_json(material))


def _master(path, expected):
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        _fail("MASTER_TOO_LARGE", "maximum 64 MiB")
    if _hash(data) != expected:
        _fail("MASTER_HASH_MISMATCH", "master bytes differ from recipe pin")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        _fail("MASTER_MAGIC_MISMATCH", "master must contain PNG bytes")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > MAX_PIXELS:
                    _fail("MASTER_TOO_LARGE", "maximum 25 million pixels")
                if getattr(source, "n_frames", 1) != 1:
                    _fail("ANIMATED_INPUT_UNSUPPORTED", "a raster master must be one frame")
                if source.mode not in {"RGB", "RGBA", "P", "L", "LA"}:
                    _fail("MASTER_MODE_UNSUPPORTED", source.mode)
                # Full ICC/DPI/metadata contract belongs to FA-023. Fail closed.
                if source.info.get("srgb") not in (0, 1, 2, 3) or source.info.get("icc_profile"):
                    _fail("COLOR_EVIDENCE_REQUIRED", "requires PNG sRGB chunk without ICC ambiguity")
                if "gamma" in source.info and abs(source.info["gamma"] - 0.45455) > 0.00001:
                    _fail("COLOR_EVIDENCE_CONFLICT", "non-sRGB gamma")
                if "chromaticity" in source.info:
                    _fail("COLOR_POLICY_UNSUPPORTED", "chromaticity handling awaits color contract")
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                source.load()
                return source.convert("RGBA"), ("A" in source.getbands() or "transparency" in source.info)
    except RasterDerivativeError:
        raise
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        _fail("MASTER_DECODE_FAILED", str(exc))


def _encode(master, spec, has_alpha):
    policy = spec["alpha_policy"]
    if policy == "FORBID" and has_alpha:
        _fail("ALPHA_FORBIDDEN", "master has an alpha channel or transparency entry")
    if policy == "FLATTEN_WHITE":
        image = Image.alpha_composite(Image.new("RGBA", master.size, "white"), master).convert("RGB")
    elif policy == "FORBID":
        image = master.convert("RGB")
    else:
        image = master
    size = (spec["width_px"], spec["height_px"])
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    # A fresh pixel image prevents silent EXIF/ICC/text/DPI propagation.
    image = Image.frombytes(image.mode, image.size, image.tobytes())
    options = {
        "JPEG": {"quality": spec.get("quality"), "subsampling": 0, "optimize": False, "progressive": False},
        "WEBP": {"quality": spec.get("quality"), "lossless": False, "method": 6, "exact": True},
        "TIFF": {"compression": "raw"},
    }[spec["format"]]
    output = io.BytesIO()
    image.save(output, format=spec["format"], **options)
    return output.getvalue(), image


def _verify(data, spec, expected_image=None):
    fmt = spec["format"]
    magic = {"JPEG": data.startswith(b"\xff\xd8\xff"),
             "WEBP": data[:4] == b"RIFF" and data[8:12] == b"WEBP",
             "TIFF": data[:4] in (b"II*\x00", b"MM\x00*")}[fmt]
    if not magic:
        _fail("OUTPUT_MAGIC_MISMATCH", fmt)
    try:
        with Image.open(io.BytesIO(data)) as output:
            output.load()
            if output.format != fmt or output.size != (spec["width_px"], spec["height_px"]):
                _fail("OUTPUT_SPEC_MISMATCH", "format or dimensions")
            has_alpha = "A" in output.getbands()
            if spec["alpha_policy"] != "PRESERVE" and has_alpha:
                _fail("OUTPUT_ALPHA_MISMATCH", "unexpected output alpha")
            if spec["alpha_policy"] == "PRESERVE" and expected_image is not None:
                actual = output.convert("RGBA").getchannel("A").tobytes()
                if actual != expected_image.getchannel("A").tobytes():
                    _fail("OUTPUT_ALPHA_MISMATCH", "alpha values changed")
    except (OSError, ValueError) as exc:
        if isinstance(exc, RasterDerivativeError):
            raise
        _fail("OUTPUT_DECODE_FAILED", str(exc))


def _receipt(recipe, key, data):
    spec = recipe["output"]
    receipt = {
        "schema": "die.factory-asset.derivative-receipt.v1",
        "recipe_id": recipe["recipe_id"], "recipe_version": recipe["recipe_version"],
        "idempotency_key": key,
        "input": {k: recipe["input"][k] for k in ("master_sha256", "semantic_asset_id")},
        "marketplace_profile": recipe["marketplace_profile"],
        "output": {"format": spec["format"], "sha256": _hash(data), "bytes": len(data),
                   "width_px": spec["width_px"], "height_px": spec["height_px"], "semantic_identity_effect": "NONE"},
        "qa": {"magic_mime_match": True, "decode_reopen": True, "sha256_verified": True, "failure_code": None},
        "compatibility": {"state": "COMPATIBILITY_UNKNOWN",
                          "reason": "Conversion QA passed; marketplace package compatibility has not been evaluated."},
        "result": "FAIL",
    }
    _schema(receipt, "derivative-receipt.schema.json")
    return receipt


def _write(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _convert(master_path, recipe, output_root):
    """Return {conversion_status, artifact_path, receipt_path, receipt}.

    Linux-only. Atomic directory publication and flock serialize same-root
    writers. Existing content is verified and never repaired or overwritten.
    The output root must be worker-owned, not writable by untrusted processes.
    """
    # Snapshot caller data to keep keys/receipts independent of caller mutation.
    recipe = json.loads(_json(recipe))
    key = _validate(recipe)
    encoder = runtime()
    master_path = Path(master_path).resolve(strict=True)
    master, has_alpha = _master(master_path, recipe["input"]["master_sha256"])
    data, image = _encode(master, recipe["output"], has_alpha)
    _verify(data, recipe["output"], image)
    receipt = _receipt(recipe, key, data)
    root = Path(output_root).resolve()
    final = root / key
    if master_path == final or final in master_path.parents:
        _fail("MASTER_OUTPUT_COLLISION", "master lies within target derivative directory")
    root.mkdir(parents=True, exist_ok=True)
    filename = "derivative." + EXTENSIONS[recipe["output"]["format"]]
    manifest = {"schema": "die.factory-asset.raster-worker-manifest.v1", "runtime": encoder,
                "recipe": recipe, "artifact": filename,
                "metadata_policy": "STRIP_EXIF_ICC_TEXT_DPI", "source_color_evidence": "PNG_SRGB_CHUNK"}
    lock = os.open(root / ".fa021.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(final):
            if final.is_symlink() or not final.is_dir():
                _fail("OUTPUT_COLLISION", "target is not an owned derivative directory")
            expected = {filename: data, "receipt.json": _json(receipt), "manifest.json": _json(manifest)}
            if {p.name for p in final.iterdir()} != set(expected):
                _fail("OUTPUT_COLLISION", "incomplete or unexpected directory content")
            for name, content in expected.items():
                path = final / name
                if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                    _fail("OUTPUT_COLLISION", f"existing {name} does not match pinned conversion")
            status = "REUSED"
        else:
            temp = Path(tempfile.mkdtemp(prefix=".fa021-", dir=root))
            try:
                _write(temp / filename, data)
                durable = (temp / filename).read_bytes()
                if _hash(durable) != receipt["output"]["sha256"]:
                    _fail("OUTPUT_HASH_MISMATCH", "disk bytes differ from encoded output")
                _verify(durable, recipe["output"], image)
                _write(temp / "receipt.json", _json(receipt))
                _write(temp / "manifest.json", _json(manifest))
                _fsync_dir(temp)
                os.rename(temp, final)
                _fsync_dir(root)
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
            status = "CREATED"
    finally:
        os.close(lock)
    return {"conversion_status": status, "artifact_path": str(final / filename),
            "receipt_path": str(final / "receipt.json"), "receipt": receipt}


def convert(master_path, recipe, output_root):
    """Convert locally; return durable receipts or a typed, artifact-free error."""
    try:
        return _convert(master_path, recipe, output_root)
    except RasterDerivativeError:
        raise
    except OSError as exc:
        raise RasterDerivativeError("IO_ERROR", str(exc)) from exc
