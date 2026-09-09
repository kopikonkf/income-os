from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from pypdf import PdfReader
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

SCHEMA_KP = "die.h03.knowledge-package.v1"
SCHEMA_BP = "die.h03.product-blueprint.v1"
SCHEMA_AST = "die.h03.document-ast.v1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_knowledge_package(kp: dict[str, Any]) -> None:
    if kp.get("schema_version") != SCHEMA_KP:
        raise ValueError("KNOWLEDGE_SCHEMA_INVALID")
    if kp.get("holding_id") != "H03":
        raise ValueError("HOLDING_ID_INVALID")
    if kp.get("rights_status") not in {"INTERNAL_ORIGINAL", "GOVERNED_EXTERNAL"}:
        raise ValueError("RIGHTS_STATUS_INVALID")
    source = kp.get("source_packet") or {}
    evidence = source.get("evidence_units") or []
    evidence_ids = {item.get("evidence_id") for item in evidence if item.get("evidence_id") and item.get("text")}
    if not evidence_ids:
        raise ValueError("NO_EVIDENCE_UNITS")
    claims = kp.get("claims") or []
    if not claims:
        raise ValueError("NO_CLAIMS")
    claim_ids: set[str] = set()
    for claim in claims:
        cid = claim.get("claim_id")
        refs = claim.get("evidence_refs") or []
        if not cid or not claim.get("text") or not refs:
            raise ValueError("CLAIM_INCOMPLETE")
        if cid in claim_ids:
            raise ValueError("DUPLICATE_CLAIM_ID")
        claim_ids.add(cid)
        missing = [ref for ref in refs if ref not in evidence_ids]
        if missing:
            raise ValueError(f"UNRESOLVED_EVIDENCE:{cid}:{','.join(missing)}")


def compile_document_ast(kp: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    validate_knowledge_package(kp)
    if blueprint.get("schema_version") != SCHEMA_BP:
        raise ValueError("BLUEPRINT_SCHEMA_INVALID")
    if blueprint.get("knowledge_package_id") != kp.get("knowledge_package_id"):
        raise ValueError("BLUEPRINT_KNOWLEDGE_MISMATCH")
    claims = {c["claim_id"]: c for c in kp["claims"]}
    blocks: list[dict[str, Any]] = []
    for section in blueprint.get("sections") or []:
        heading = section.get("heading")
        if not heading:
            raise ValueError("SECTION_HEADING_MISSING")
        blocks.append({"type": "heading", "text": heading})
        for cid in section.get("claim_ids") or []:
            if cid not in claims:
                raise ValueError(f"UNKNOWN_CLAIM:{cid}")
            blocks.append({"type": "paragraph", "claim_id": cid, "text": claims[cid]["text"]})
    if not blocks:
        raise ValueError("NO_DOCUMENT_BLOCKS")
    metadata = dict(blueprint.get("metadata") or {})
    metadata.update({"title": blueprint["title"], "subtitle": blueprint.get("subtitle", "")})
    return {
        "schema_version": SCHEMA_AST,
        "product_id": blueprint["product_id"],
        "knowledge_package_id": kp["knowledge_package_id"],
        "metadata": metadata,
        "blocks": blocks,
    }


def _wrap(text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_pdf(ast: dict[str, Any], out_path: Path) -> dict[str, Any]:
    if ast.get("schema_version") != SCHEMA_AST:
        raise ValueError("AST_SCHEMA_INVALID")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    c = canvas.Canvas(str(out_path), pagesize=A4, invariant=1, pageCompression=0)
    meta = ast.get("metadata") or {}
    c.setTitle(meta.get("title", "H03 Knowledge Product"))
    c.setAuthor(meta.get("author", "Digital Income Empire - H03"))
    c.setSubject(meta.get("subject", "H03 deterministic knowledge product"))
    c.setCreator("DIE H03 PDF Factory v1")
    margin = 54
    usable = width - margin * 2
    page_no = 1

    def footer() -> None:
        c.setFont("Helvetica", 8)
        c.drawRightString(width - margin, 28, f"H03 internal proof | page {page_no}")

    # Cover
    c.setFont("Helvetica-Bold", 20)
    y = height - 120
    for line in _wrap(meta.get("title", "H03 Knowledge Product"), "Helvetica-Bold", 20, usable):
        c.drawString(margin, y, line)
        y -= 27
    subtitle = meta.get("subtitle", "")
    if subtitle:
        y -= 8
        c.setFont("Helvetica", 11)
        for line in _wrap(subtitle, "Helvetica", 11, usable):
            c.drawString(margin, y, line)
            y -= 16
    y -= 28
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Product: {ast['product_id']}")
    c.drawString(margin, y - 14, f"Knowledge package: {ast['knowledge_package_id']}")
    footer()
    c.showPage()
    page_no += 1
    y = height - margin

    for block in ast["blocks"]:
        if block["type"] == "heading":
            font, size, leading, gap = "Helvetica-Bold", 13, 17, 10
        else:
            font, size, leading, gap = "Helvetica", 10, 14, 8
        lines = _wrap(block["text"], font, size, usable)
        needed = len(lines) * leading + gap
        if y - needed < 48:
            footer()
            c.showPage()
            page_no += 1
            y = height - margin
        c.setFont(font, size)
        for line in lines:
            c.drawString(margin, y, line)
            y -= leading
        y -= gap

    footer()
    c.save()
    return {"page_count": page_no, "path": str(out_path)}


def validate_pdf(pdf_path: Path, expected_title: str, render_dir: Path) -> dict[str, Any]:
    reader = PdfReader(str(pdf_path))
    pages = len(reader.pages)
    if pages < 1:
        raise ValueError("PDF_PAGE_COUNT_INVALID")
    title = (reader.metadata.title or "") if reader.metadata else ""
    if title != expected_title:
        raise ValueError(f"PDF_TITLE_MISMATCH:{title}")
    extracted = "\n".join((p.extract_text() or "") for p in reader.pages)
    normalized_text = " ".join(extracted.split())
    normalized_title = " ".join(expected_title.split())
    if normalized_title not in normalized_text:
        raise ValueError("PDF_TEXT_REOPEN_FAILED")

    render_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    visual = []
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=1.25)
        image = bitmap.to_pil().convert("L")
        out = render_dir / f"page-{i+1}.png"
        image.save(out)
        histogram = image.histogram()
        nonwhite = sum(histogram[:245])
        ratio = nonwhite / max(1, image.width * image.height)
        if ratio < 0.001:
            raise ValueError(f"VISUAL_PAGE_BLANK:{i+1}")
        mask = image.point(lambda px: 255 if px < 245 else 0)
        bbox = mask.getbbox()
        if bbox is None:
            raise ValueError(f"VISUAL_PAGE_BLANK:{i+1}")
        left, top, right, bottom = bbox
        if left <= 2 or top <= 2 or right >= image.width - 2 or bottom >= image.height - 2:
            raise ValueError(f"VISUAL_CONTENT_TOUCHES_EDGE:{i+1}:{bbox}")
        visual.append({"page": i + 1, "width": image.width, "height": image.height, "nonwhite_ratio": round(ratio, 6), "content_bbox": [left, top, right, bottom], "png_sha256": sha256_file(out)})
        page.close()
    doc.close()
    stream = getattr(reader, "stream", None)
    if hasattr(stream, "close"):
        stream.close()
    return {"page_count": pages, "metadata_title": title, "text_chars": len(extracted), "visual_pages": visual}


def build_mvp(repo_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    base = repo_root / "company" / "h03" / "examples" / "mvp"
    evidence_dir = repo_root / "company" / "h03" / "evidence" / "H03-MVP-001"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    kp = load_json(base / "knowledge-package.json")
    blueprint = load_json(base / "product-blueprint.json")
    ast = compile_document_ast(kp, blueprint)
    ast_path = evidence_dir / "document-ast.json"
    write_json(ast_path, ast)
    pdf_path = evidence_dir / "portable-knowledge-product-build-verification-guide.pdf"
    render_pdf(ast, pdf_path)
    validation = validate_pdf(pdf_path, blueprint["title"], evidence_dir / "renders")
    validation_path = evidence_dir / "validation.json"
    write_json(validation_path, validation)

    lineage_paths = [
        base / "source-packet.json",
        base / "knowledge-package.json",
        base / "product-blueprint.json",
        ast_path,
        pdf_path,
        validation_path,
    ]
    manifest = {str(p.relative_to(repo_root)).replace("\\", "/"): {"sha256": sha256_file(p), "bytes": p.stat().st_size} for p in lineage_paths}
    manifest_path = evidence_dir / "manifest.json"
    write_json(manifest_path, {"schema_version": "die.h03.artifact-manifest.v1", "files": manifest})
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    receipt = {
        "schema_version": "die.h03.build-receipt.v1",
        "status": "PASS",
        "holding_id": "H03",
        "task_id": "H03-MVP-001",
        "work_card_id": "H03-MVP-001",
        "economic_trace_id": "H03-ECO-TRACE-MVP-001",
        "product_id": blueprint["product_id"],
        "knowledge_package_id": kp["knowledge_package_id"],
        "build_job_id": "H03-BUILD-MVP-001",
        "source_id": kp["source_packet"]["source_id"],
        "rights_status": kp["rights_status"],
        "founder_active_minutes": "UNKNOWN",
        "cash_direct_cost": "UNKNOWN",
        "shared_cost_attribution_status": "UNKNOWN",
        "revenue_state": "UNPROVEN",
        "future_commercial_identity": {
            "listing_id": "UNPROVEN",
            "order_id": "UNPROVEN",
            "revenue_event_id": "UNPROVEN",
        },
        "canonical_economics_write": False,
        "state_manager_boundary": "die-state-manager",
        "resource_observation": {"build_elapsed_ms": elapsed_ms, "pdf_bytes": pdf_path.stat().st_size, "pdf_pages": validation["page_count"]},
        "artifact_manifest": str(manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "pdf_sha256": sha256_file(pdf_path),
        "acceptance": {"knowledge_validated": True, "ast_compiled": True, "pdf_reopened": True, "raster_visual_qa": True, "metadata_validated": True, "hash_lineage_recorded": True},
    }
    receipt_path = evidence_dir / "build-receipt.json"
    write_json(receipt_path, receipt)
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--build-mvp", action="store_true")
    args = ap.parse_args()
    if args.build_mvp:
        receipt = build_mvp(Path(args.repo_root).resolve())
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
