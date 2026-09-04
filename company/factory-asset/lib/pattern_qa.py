"""FA-033: fail-closed QA for FA-032 SCATTERED_DIAMONDS v1 tiles.

Read-only verification of actual SVG/PNG bytes. Compatibility is scoped to
pattern tile QA, never marketplace acceptance or submission authority.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import re
import warnings
import xml.etree.ElementTree as ET

import jsonschema
from PIL import Image, ImageDraw, ImageColor
from procedural_pattern import _validate_request, NATIVE_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("lineage", "editable_paths", "tile_bounds", "seams", "renderability", "preview_consistency")
NUMBER = r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
PATH = re.compile(rf"M\s+{NUMBER}\s+{NUMBER}(?:\s+L\s+{NUMBER}\s+{NUMBER}){{3,}}\s+Z")
COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
MAX_MASTER_BYTES = 1024 * 1024
MAX_PREVIEW_PIXELS = 16_000_000
MAX_PREVIEW_BYTES = 64 * 1024 * 1024
NS = "{http://www.w3.org/2000/svg}"


class PatternQAError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _require(condition, code, message):
    if not condition:
        raise PatternQAError(code, message)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _read(path, limit):
    with Path(path).open("rb") as f:
        data = f.read(limit + 1)
    _require(len(data) <= limit, "RESOURCE_LIMIT", "artifact exceeds QA byte budget")
    return data


def _paths(data):
    _require(b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(),
             "UNSAFE_XML", "DTD/entity declarations are unsupported")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise PatternQAError("SVG_XML_INVALID", str(exc)) from exc
    _require(root.tag == NS + "svg" and set(root.attrib) == {"viewBox"},
             "SVG_PROFILE_UNSUPPORTED", "only the FA-032 flat SVG profile is accepted")
    children = list(root)
    _require(2 <= len(children) <= 129, "PATH_COUNT_INVALID", "background plus 1..128 motifs required")
    paths = []
    for element in children:
        _require(element.tag == NS + "path" and not list(element),
                 "NON_EDITABLE_CONTENT", "only direct editable paths; no raster, font, script, group or external reference")
        _require(set(element.attrib) == {"d", "fill", "stroke"} and element.attrib["stroke"] == "none",
                 "PATH_STYLE_UNSUPPORTED", "transforms, CSS, references and strokes are unsupported")
        d, fill = element.attrib["d"], element.attrib["fill"]
        _require(PATH.fullmatch(d) is not None and COLOR.fullmatch(fill) is not None,
                 "PATH_SYNTAX_UNSUPPORTED", "requires closed absolute M/L/Z paths with solid RGB fill")
        values = [float(n) for n in re.findall(NUMBER, d)]
        points = list(zip(values[::2], values[1::2]))
        _require(all(math.isfinite(n) for n in values), "PATH_NONFINITE", "coordinates must be finite")
        _require(points[0] == points[-1], "PATH_NOT_CLOSED", "explicit closed polygon required")
        area = abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:])))
        _require(area > 0, "PATH_DEGENERATE", "zero-area polygon")
        paths.append((points, fill))
    try:
        viewbox = [float(x) for x in root.attrib["viewBox"].split()]
    except ValueError as exc:
        raise PatternQAError("VIEWBOX_INVALID", str(exc)) from exc
    return viewbox, paths


def verify_pattern(request, production):
    """Return a deterministic typed receipt. Never modify input artifacts."""
    checks = {name: "NOT_RUN" for name in STAGES}
    receipt = {
        "schema": "die.factory-asset.pattern-qa.v1", "result": "FAIL",
        "checks": checks, "failures": [],
        "compatibility": {"scope": "FA032_PATTERN_TILE", "state": "INCOMPATIBLE"},
        "marketplace_compatibility": "COMPATIBILITY_UNKNOWN",
        "semantic_identity_effect": "NONE",
    }
    stage = "lineage"
    try:
        p = _validate_request(request)
        _require(request["producer_version"] == "1.0.0", "PRODUCER_VERSION_UNSUPPORTED", "FA-032 v1 only")
        w, h, repeat = p["tile_width"], p["tile_height"], p["preview_repeat"]
        _require(w*h*repeat*repeat <= MAX_PREVIEW_PIXELS, "RESOURCE_LIMIT", "preview exceeds 16 million pixels")
        native, pattern, preview = production["native_receipt"], production["pattern"], production["preview"]
        jsonschema.Draft202012Validator(NATIVE_SCHEMA).validate(native)
        _require(native["result"] == "PASS", "PRODUCTION_NOT_PASS", "cannot QA a cancelled/failed producer as success")
        for field in ("job_id", "idempotency_key", "producer_class", "producer_version"):
            _require(native[field] == request[field], "LINEAGE_MISMATCH", field)
        native_base = {k:v for k,v in native.items() if k != "deterministic_receipt_sha256"}
        _require(_digest(_canonical(native_base)) == native["deterministic_receipt_sha256"],
                 "NATIVE_RECEIPT_HASH_MISMATCH", "native receipt changed")
        master = _read(pattern["master_path"], MAX_MASTER_BYTES)
        png = _read(preview["path"], MAX_PREVIEW_BYTES)
        master_sha, preview_sha = _digest(master), _digest(png)
        receipt["input"] = {"semantic_asset_id": request["semantic_asset_id"], "job_id": request["job_id"],
                            "master_sha256": master_sha, "preview_sha256": preview_sha}
        _require(native["master"]["format"] == "SVG" and native["master"]["bytes"] == len(master),
                 "MASTER_SPEC_MISMATCH", "native SVG byte count/format")
        _require(native["master"]["sha256"] == pattern["master_sha256"] == preview["source_master_sha256"] == master_sha,
                 "MASTER_HASH_MISMATCH", "master lineage is not bound to actual bytes")
        _require(preview["sha256"] == preview_sha and preview["bytes"] == len(png),
                 "PREVIEW_HASH_MISMATCH", "preview bytes differ from receipt")
        _require(pattern["parameters"] == p and pattern["seed"] == p["seed"] and pattern["recipe_kind"] == p["recipe_kind"],
                 "RECIPE_MISMATCH", "pattern parameter pin changed")
        _require(preview["repeat"] == [repeat, repeat] and preview["dimensions"] == [w*repeat,h*repeat]
                 and preview["format"] == "PNG", "PREVIEW_SPEC_MISMATCH", "preview repeat/dimension/format pin")
        checks[stage] = "PASS"

        stage = "editable_paths"
        viewbox, paths = _paths(master)
        _require(len(paths) == p["motif_count"]+1 == pattern["path_count"],
                 "PATH_COUNT_MISMATCH", "actual SVG path count does not match recipe")
        _require(pattern["editable_vector_paths"] is True and pattern["embedded_raster"] is False,
                 "EDITABILITY_CLAIM_MISMATCH", "producer editability claim differs")
        checks[stage] = "PASS"

        stage = "tile_bounds"
        _require(viewbox == [0,0,w,h], "VIEWBOX_MISMATCH", "tile viewBox differs from pinned dimensions")
        for points, _ in paths:
            _require(all(0 <= x <= w and 0 <= y <= h for x,y in points),
                     "PATH_OUT_OF_BOUNDS", "polygon crosses the tile boundary")
        _require(paths[0] == ([(0,0),(w,0),(w,h),(0,h),(0,0)],p["background_color"]),
                 "BACKGROUND_MISMATCH", "background must cover exactly one tile")
        # This gate supports the FA-032 diamond geometry, not arbitrary SVG.
        half = p["motif_size"] // 2
        for points, fill in paths[1:]:
            _require(len(points) == 5, "MOTIF_GEOMETRY_INVALID", "four vertices plus closure required")
            cx, cy = points[0][0], points[1][1]
            expected = [(cx,cy-half),(cx+half,cy),(cx,cy+half),(cx-half,cy),(cx,cy-half)]
            _require(points == expected and fill in p["motif_colors"],
                     "MOTIF_GEOMETRY_INVALID", "diamond geometry or palette differs from recipe")
        checks[stage] = "PASS"

        stage = "seams"
        _require(all(1 <= x <= w-1 and 1 <= y <= h-1 for pts,_ in paths[1:] for x,y in pts),
                 "BROKEN_SEAM", "FA-032 motifs require a continuous background border")
        checks[stage] = "PASS"

        stage = "renderability"
        # Independently reconstruct from parsed SVG geometry, never producer motif data.
        tile = Image.new("RGB", (w+1,h+1))
        draw = ImageDraw.Draw(tile)
        for points, fill in paths:
            draw.polygon(points[:-1], fill=fill)
        bg = ImageColor.getrgb(p["background_color"])
        border = [tile.getpixel((x,y)) for x in range(w+1) for y in (0,h)]
        border += [tile.getpixel((x,y)) for y in range(h+1) for x in (0,w)]
        _require(all(pixel == bg for pixel in border), "BROKEN_SEAM", "rendered border is discontinuous")
        # Sample the same continuous SVG boundary (0 and w/h), not adjacent
        # pixel centers (0 and w-1/h-1), which need not have equal colors.
        tile = tile.crop((0,0,w,h))
        checks[stage] = "PASS"

        stage = "preview_consistency"
        _require(png.startswith(b"\x89PNG\r\n\x1a\n"), "PREVIEW_MAGIC_INVALID", "PNG bytes required")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(png)) as im:
                _require(im.format == "PNG" and im.size == (w*repeat,h*repeat) and im.mode == "RGB"
                         and getattr(im,"n_frames",1) == 1, "PREVIEW_DECODE_SPEC_MISMATCH", "decoded preview differs")
                im.load()
                expected_tile = tile.tobytes()
                for ty in range(repeat):
                    for tx in range(repeat):
                        actual = im.crop((tx*w,ty*h,(tx+1)*w,(ty+1)*h))
                        _require(actual.tobytes() == expected_tile, "PREVIEW_INCONSISTENT",
                                 "every repeated preview tile must match the SVG-derived render")
        checks[stage] = "PASS"
        receipt["result"] = "PASS"
        receipt["compatibility"]["state"] = "COMPATIBLE"
    except (PatternQAError, ValueError, OSError, KeyError, TypeError, jsonschema.ValidationError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        checks[stage] = "FAIL"
        receipt["failures"].append({"code": getattr(exc,"code","INVALID_INPUT_OR_ARTIFACT"), "stage": stage})
    schema = json.loads((ROOT/"schemas/pattern-qa.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(receipt)
    return receipt
