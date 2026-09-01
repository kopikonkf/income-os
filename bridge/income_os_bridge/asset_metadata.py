"""META-001 deterministic metadata compiler/injector.

Division01 remains the semantic author. This module validates an authored
metadata payload against Blueprint metadata_direction, normalizes ordering,
serializes a canonical sidecar, embeds XMP in PNG/JPEG, embeds IPTC IIM in JPEG,
and reads back only the metadata it wrote. It never invents titles, descriptions,
keywords, categories, disclosures, or commercial intent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib
from typing import Any
from xml.sax.saxutils import escape

SCHEMA = "die.asset.metadata.v1"
AUTHOR_PRINCIPAL = "division-head-division01"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


class MetadataError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _norm(value: str) -> str:
    return " ".join(str(value).split()).strip()


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _norm(raw)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def compile_metadata(blueprint: dict[str, Any], authored: dict[str, Any]) -> dict[str, Any]:
    direction = blueprint.get("metadata_direction")
    if not isinstance(direction, dict):
        raise MetadataError("E_BLUEPRINT_METADATA_DIRECTION")
    required_authored = {
        "schema", "author_principal_id", "blueprint_id", "blueprint_sha256",
        "title", "description", "primary_keywords", "secondary_keywords",
        "categories", "ai_disclosure",
    }
    if not isinstance(authored, dict) or set(authored) != required_authored:
        raise MetadataError("E_AUTHORED_METADATA_SHAPE")
    if authored["schema"] != "die.division001.asset-metadata-authoring.v1":
        raise MetadataError("E_AUTHORED_METADATA_SCHEMA")
    if authored["author_principal_id"] != AUTHOR_PRINCIPAL:
        raise MetadataError("E_SEMANTIC_AUTHORITY")
    if authored["blueprint_id"] != blueprint.get("blueprint_id"):
        raise MetadataError("E_BLUEPRINT_ID_MISMATCH")
    if authored["blueprint_sha256"] != canonical_sha256(blueprint):
        raise MetadataError("E_BLUEPRINT_HASH_MISMATCH")

    primary = _dedupe(list(authored["primary_keywords"]))
    secondary = _dedupe(list(authored["secondary_keywords"]))
    categories = _dedupe(list(authored["categories"]))
    allowed_primary = {str(x).strip().casefold() for x in direction.get("primary_keywords", [])}
    allowed_secondary = {str(x).strip().casefold() for x in direction.get("secondary_keywords", [])}
    allowed_categories = {str(x).strip().casefold() for x in direction.get("category_direction", [])}
    if any(x.casefold() not in allowed_primary for x in primary):
        raise MetadataError("E_PRIMARY_KEYWORD_INVENTED")
    if any(x.casefold() not in allowed_secondary for x in secondary):
        raise MetadataError("E_SECONDARY_KEYWORD_INVENTED")
    if any(x.casefold() not in allowed_categories for x in categories):
        raise MetadataError("E_CATEGORY_INVENTED")
    if {x.casefold() for x in primary} & {x.casefold() for x in secondary}:
        raise MetadataError("E_KEYWORD_OVERLAP")

    title = _norm(authored["title"])
    description = _norm(authored["description"])
    disclosure = _norm(authored["ai_disclosure"])
    if not title or not description or not disclosure:
        raise MetadataError("E_REQUIRED_TEXT_MISSING")
    return {
        "schema": SCHEMA,
        "blueprint_id": authored["blueprint_id"],
        "blueprint_sha256": authored["blueprint_sha256"],
        "semantic_author": AUTHOR_PRINCIPAL,
        "title": title,
        "description": description,
        "keywords": primary + secondary,
        "primary_keywords": primary,
        "secondary_keywords": secondary,
        "categories": categories,
        "ai_disclosure": disclosure,
        "title_direction_ref": _norm(direction.get("title_direction", "")),
        "semantic_content_invented_by_engine": False,
    }


def _xmp(metadata: dict[str, Any]) -> bytes:
    subjects = "".join(f"<rdf:li>{escape(x)}</rdf:li>" for x in metadata["keywords"])
    categories = ", ".join(metadata["categories"])
    xml = f'''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" xmlns:die="https://income-os.local/ns/1.0/" die:MetadataVersion="1" die:BlueprintId="{escape(metadata['blueprint_id'])}" xmp:Label="{escape(metadata['ai_disclosure'])}" photoshop:Category="{escape(categories)}">
<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{escape(metadata['title'])}</rdf:li></rdf:Alt></dc:title>
<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{escape(metadata['description'])}</rdf:li></rdf:Alt></dc:description>
<dc:subject><rdf:Bag>{subjects}</rdf:Bag></dc:subject>
</rdf:Description></rdf:RDF></x:xmpmeta>
<?xpacket end="w"?>'''
    return xml.encode("utf-8")


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _embed_png(raw: bytes, xmp: bytes) -> bytes:
    if not raw.startswith(PNG_SIG):
        raise MetadataError("E_NOT_PNG")
    i = len(PNG_SIG)
    out = bytearray(PNG_SIG)
    inserted = False
    while i + 12 <= len(raw):
        size = struct.unpack(">I", raw[i:i + 4])[0]
        end = i + 12 + size
        if end > len(raw):
            raise MetadataError("E_PNG_TRUNCATED")
        kind = raw[i + 4:i + 8]
        if kind == b"IEND" and not inserted:
            payload = b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xmp
            out.extend(_png_chunk(b"iTXt", payload))
            inserted = True
        out.extend(raw[i:end])
        i = end
    if not inserted:
        raise MetadataError("E_PNG_IEND_MISSING")
    return bytes(out)


def _iptc_dataset(dataset: int, text: str) -> bytes:
    data = text.encode("utf-8")
    if len(data) > 0x7FFF:
        raise MetadataError("E_IPTC_FIELD_TOO_LONG")
    return b"\x1c\x02" + bytes([dataset]) + struct.pack(">H", len(data)) + data


def _iptc_payload(metadata: dict[str, Any]) -> bytes:
    iim = _iptc_dataset(5, metadata["title"])
    for keyword in metadata["keywords"]:
        iim += _iptc_dataset(25, keyword)
    iim += _iptc_dataset(120, metadata["description"])
    name = b"\x00\x00"
    resource = b"8BIM" + struct.pack(">H", 0x0404) + name + struct.pack(">I", len(iim)) + iim
    if len(iim) % 2:
        resource += b"\x00"
    return b"Photoshop 3.0\x00" + resource


def _jpeg_segment(marker: int, payload: bytes) -> bytes:
    if len(payload) + 2 > 0xFFFF:
        raise MetadataError("E_JPEG_METADATA_TOO_LARGE")
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def _embed_jpeg(raw: bytes, xmp: bytes, metadata: dict[str, Any]) -> bytes:
    if not raw.startswith(b"\xff\xd8"):
        raise MetadataError("E_NOT_JPEG")
    xmp_seg = _jpeg_segment(0xE1, XMP_HEADER + xmp)
    iptc_seg = _jpeg_segment(0xED, _iptc_payload(metadata))
    return raw[:2] + xmp_seg + iptc_seg + raw[2:]


def inject(source: Path, output: Path, sidecar: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    sidecar = sidecar.resolve()
    raw = source.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    xmp = _xmp(metadata)
    if raw.startswith(PNG_SIG):
        transformed = _embed_png(raw, xmp)
        fmt = "PNG"
        embedded = ["XMP"]
    elif raw.startswith(b"\xff\xd8"):
        transformed = _embed_jpeg(raw, xmp, metadata)
        fmt = "JPEG"
        embedded = ["IPTC-IIM", "XMP"]
    else:
        raise MetadataError("E_UNSUPPORTED_FORMAT")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(transformed)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar_payload = {
        "schema": "die.asset.metadata-sidecar.v1",
        "artifact_input_sha256": source_hash,
        "metadata": metadata,
        "embedded": embedded,
    }
    sidecar.write_text(json.dumps(sidecar_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readback = read_back(output)
    expected = {"title": metadata["title"], "description": metadata["description"], "keywords": metadata["keywords"]}
    if readback != expected:
        raise MetadataError(f"E_READBACK_MISMATCH:{readback!r}")
    return {
        "schema": "die.asset.metadata-injection-receipt.v1",
        "format": fmt,
        "input_sha256": source_hash,
        "output_sha256": sha256(output),
        "sidecar_sha256": sha256(sidecar),
        "embedded": embedded,
        "readback_verified": True,
        "metadata": metadata,
        "lineage_hash_changed": sha256(output) != source_hash,
        "authority_boundary": {"semantic_author": AUTHOR_PRINCIPAL, "engine_invented_semantics": False, "submission_authorized": False},
    }


def _extract_xmp(raw: bytes) -> bytes:
    if raw.startswith(PNG_SIG):
        i = len(PNG_SIG)
        while i + 12 <= len(raw):
            size = struct.unpack(">I", raw[i:i + 4])[0]
            kind = raw[i + 4:i + 8]
            data = raw[i + 8:i + 8 + size]
            if kind == b"iTXt" and data.startswith(b"XML:com.adobe.xmp\x00"):
                parts = data.split(b"\x00", 5)
                if len(parts) == 6:
                    return parts[5]
            i += 12 + size
    elif raw.startswith(b"\xff\xd8"):
        i = 2
        while i + 4 <= len(raw) and raw[i] == 0xFF:
            marker = raw[i + 1]
            if marker == 0xDA:
                break
            size = struct.unpack(">H", raw[i + 2:i + 4])[0]
            payload = raw[i + 4:i + 2 + size]
            if marker == 0xE1 and payload.startswith(XMP_HEADER):
                return payload[len(XMP_HEADER):]
            i += 2 + size
    raise MetadataError("E_XMP_NOT_FOUND")


def read_back(path: Path) -> dict[str, Any]:
    xmp = _extract_xmp(path.read_bytes())
    root = ET.fromstring(xmp.decode("utf-8-sig").replace("<?xpacket begin=\"\ufeff\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?>", "").replace("<?xpacket end=\"w\"?>", ""))
    ns = {"dc": "http://purl.org/dc/elements/1.1/", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
    title = root.find(".//dc:title/rdf:Alt/rdf:li", ns)
    desc = root.find(".//dc:description/rdf:Alt/rdf:li", ns)
    keywords = [x.text or "" for x in root.findall(".//dc:subject/rdf:Bag/rdf:li", ns)]
    return {"title": title.text if title is not None else "", "description": desc.text if desc is not None else "", "keywords": keywords}


def platform_preflight(metadata: dict[str, Any], *, max_title: int, max_keywords: int, require_ai_disclosure: bool) -> dict[str, Any]:
    failures = []
    if len(metadata["title"]) > max_title:
        failures.append("TITLE_TOO_LONG")
    if len(metadata["keywords"]) > max_keywords:
        failures.append("TOO_MANY_KEYWORDS")
    if require_ai_disclosure and not metadata["ai_disclosure"]:
        failures.append("AI_DISCLOSURE_MISSING")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "keyword_count": len(metadata["keywords"]), "title_length": len(metadata["title"])}


def platform_mapping_preflight(metadata: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Map canonical metadata to one QA platform profile and fail closed on unknown metadata/disclosure contract."""
    if profile.get("schema_version") != "die.asset.qa-platform-profile.v1":
        raise MetadataError("E_PLATFORM_PROFILE_SCHEMA")
    requirements = profile.get("requirements")
    if not isinstance(requirements, dict):
        raise MetadataError("E_PLATFORM_REQUIREMENTS")
    failures: list[str] = []
    unknowns: list[str] = []
    for key in ("metadata_constraints", "ai_disclosure"):
        row = requirements.get(key)
        if not isinstance(row, dict) or row.get("status") not in {"KNOWN", "UNKNOWN"}:
            raise MetadataError(f"E_PLATFORM_REQUIREMENT:{key}")
        if row["status"] == "UNKNOWN":
            unknowns.append(key)
    ai = requirements.get("ai_disclosure", {})
    if ai.get("status") == "KNOWN" and isinstance(ai.get("value"), dict) and ai["value"].get("required") is True and not metadata.get("ai_disclosure"):
        failures.append("AI_DISCLOSURE_MISSING")
    if failures:
        status = "FAIL"
    elif unknowns:
        status = "BLOCKED_UNKNOWN_REQUIREMENT"
    else:
        status = "PASS"
    return {
        "schema": "die.asset.metadata-platform-map.v1",
        "platform": profile.get("platform"),
        "profile_id": profile.get("profile_id"),
        "status": status,
        "mapped_fields": {
            "title": metadata["title"],
            "description": metadata["description"],
            "keywords": list(metadata["keywords"]),
            "categories": list(metadata["categories"]),
            "ai_disclosure": metadata["ai_disclosure"],
        },
        "failures": failures,
        "unknown_requirements": unknowns,
        "semantic_content_invented_by_engine": False,
    }
