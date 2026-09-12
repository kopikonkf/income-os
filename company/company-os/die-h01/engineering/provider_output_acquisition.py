from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[4]
H01 = ROOT / 'company/company-os/die-h01'
SCHEMA = H01 / 'contracts/h01-provider-output-acquisition-v1.schema.json'
REVISION = '1.0.0'
SVG_RE = re.compile(r'<svg\b[\s\S]*?</svg>', re.IGNORECASE)
FENCE_RE = re.compile(r'^```(?:svg|xml)?\s*([\s\S]*?)\s*```$', re.IGNORECASE)
FORBIDDEN_SVG = (
    re.compile(r'<\s*script\b', re.I),
    re.compile(r'<\s*foreignObject\b', re.I),
    re.compile(r'<\s*image\b', re.I),
    re.compile(r'<\s*text\b', re.I),
    re.compile(r'<\s*style\b', re.I),
)


class ProviderOutputError(ValueError):
    def __init__(self, code: str, detail: str = ''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code
        self.detail = detail


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode('utf-8'))


def _validate_schema(value: Any) -> None:
    errors = sorted(
        jsonschema.Draft202012Validator(_load(SCHEMA)).iter_errors(value),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        e = errors[0]
        where = '.'.join(str(x) for x in e.absolute_path) or '$'
        raise ProviderOutputError('RECEIPT_SCHEMA_INVALID', f'{where}: {e.message}')


def _source_method(text: str, svg: str) -> str:
    stripped = text.strip()
    fence = FENCE_RE.fullmatch(stripped)
    if fence and fence.group(1).strip() == svg:
        return 'CODE_BLOCK'
    if stripped == svg:
        return 'ASSISTANT_DOM'
    return 'ASSISTANT_DOM'


def extract_single_svg(provider_response_text: str) -> tuple[str, str]:
    """Extract exactly one complete SVG candidate from a final provider response.

    Prose/Markdown outside one SVG is tolerated by acquisition because provider UIs
    are inconsistent. Ambiguous multi-SVG output fails closed. H01-103 remains the
    authoritative SVG safety/editability/geometry validator downstream.
    """
    if not isinstance(provider_response_text, str) or not provider_response_text.strip():
        raise ProviderOutputError('EMPTY_PROVIDER_OUTPUT')
    matches = [m.group(0).strip() for m in SVG_RE.finditer(provider_response_text)]
    if not matches:
        raise ProviderOutputError('OUTPUT_NOT_SVG', 'no complete <svg>...</svg> payload')
    if len(matches) != 1:
        raise ProviderOutputError('AMBIGUOUS_PROVIDER_OUTPUT', f'{len(matches)} SVG candidates')
    svg = matches[0]
    root = re.match(r'<svg\b([^>]*)>', svg, re.I)
    if not root:
        raise ProviderOutputError('SVG_ROOT_INVALID')
    attrs = root.group(1)
    has_viewbox = bool(re.search(r'\bviewBox\s*=\s*["\'][^"\']+["\']', attrs, re.I))
    has_width_height = bool(re.search(r'\bwidth\s*=\s*["\'][^"\']+["\']', attrs, re.I) and re.search(r'\bheight\s*=\s*["\'][^"\']+["\']', attrs, re.I))
    if not (has_viewbox or has_width_height):
        raise ProviderOutputError('SVG_DIMENSIONS_MISSING')
    for pat in FORBIDDEN_SVG:
        if pat.search(svg):
            raise ProviderOutputError('SVG_FORBIDDEN_FEATURE', pat.pattern)
    if len(svg.encode('utf-8')) > 1_048_576:
        raise ProviderOutputError('SVG_TOO_LARGE')
    return svg, _source_method(provider_response_text, svg)


def _atomic_bytes(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(data)
    if path.exists():
        current = path.read_bytes()
        if sha256_bytes(current) == digest:
            return 'UNCHANGED'
        raise ProviderOutputError('ARTIFACT_CONFLICT', str(path))
    fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as h:
            h.write(data)
            h.flush()
            os.fsync(h.fileno())
        os.chmod(tmp, 0o640)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return 'CREATED'


def _atomic_json(path: Path, value: dict[str, Any]) -> str:
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    return _atomic_bytes(path, data)


def build_svg_receipt(
    *,
    job_id: str,
    request_id: str,
    provider_id: str,
    profile_id: str,
    provider_status: str,
    provider_response_text: str,
    candidate_svg: str,
    extraction_method: str,
    artifact_path: Path,
    completion_signal: str,
    completed_at: str,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    data = candidate_svg.encode('utf-8')
    receipt = {
        'schema': 'die.h01.provider-output-acquisition.v1',
        'revision': REVISION,
        'job_id': job_id,
        'request_id': request_id,
        'provider_id': provider_id,
        'profile_id': profile_id,
        'terminal_state': 'SUCCEEDED',
        'output_kind': 'SVG_SOURCE_TEXT',
        'source_kind': extraction_method,
        'provider_result': {
            'provider_status': provider_status,
            'finish_reason': finish_reason,
            'provider_response_sha256': sha256_text(provider_response_text),
            'payload_sha256': sha256_bytes(data),
            'payload_bytes': len(data),
            'mime': 'image/svg+xml',
            'native_svg_source_kind': 'DIRECT_PROVIDER_SVG_SOURCE',
        },
        'artifact': {
            'path': str(artifact_path),
            'sha256': sha256_bytes(data),
            'bytes': len(data),
            'immutable_provider_original': True,
        },
        'completion': {
            'signal': completion_signal,
            'completed_at': completed_at,
        },
        'safety': {
            'cookies_read': False,
            'tokens_read': False,
            'session_bytes_read': False,
            'browser_profile_copied': False,
        },
        'downstream': {
            'h01_103_validation_required': True,
            'h01_104_receipt_compatible': True,
            'h01_105_postproduction_after_validation': True,
        },
    }
    _validate_schema(receipt)
    return receipt


def acquire_svg_text(
    *,
    job_id: str,
    request_id: str,
    provider_id: str,
    profile_id: str,
    provider_status: str,
    provider_response_text: str,
    output_dir: str | Path,
    completion_signal: str,
    completed_at: str,
    finish_reason: str | None = None,
) -> tuple[dict[str, Any], str]:
    candidate, method = extract_single_svg(provider_response_text)
    out = Path(output_dir)
    artifact = out / 'provider-original.svg'
    artifact_state = _atomic_bytes(artifact, candidate.encode('utf-8'))
    receipt = build_svg_receipt(
        job_id=job_id,
        request_id=request_id,
        provider_id=provider_id,
        profile_id=profile_id,
        provider_status=provider_status,
        provider_response_text=provider_response_text,
        candidate_svg=candidate,
        extraction_method=method,
        artifact_path=artifact,
        completion_signal=completion_signal,
        completed_at=completed_at,
        finish_reason=finish_reason,
    )
    receipt_state = _atomic_json(out / 'provider-output-acquisition.receipt.json', receipt)
    return receipt, f'{artifact_state}/{receipt_state}'


def validate_receipt(receipt: dict[str, Any]) -> None:
    _validate_schema(receipt)
    if receipt['terminal_state'] == 'SUCCEEDED':
        if receipt['output_kind'] == 'SVG_SOURCE_TEXT':
            r = receipt['provider_result']
            a = receipt['artifact']
            if r['payload_sha256'] != a['sha256'] or r['payload_bytes'] != a['bytes']:
                raise ProviderOutputError('ARTIFACT_RECEIPT_MISMATCH')
            if r['native_svg_source_kind'] != 'DIRECT_PROVIDER_SVG_SOURCE':
                raise ProviderOutputError('NATIVE_SOURCE_KIND_INVALID')
        if any(receipt['safety'].values()):
            raise ProviderOutputError('SECRET_OR_PROFILE_EXTRACTION_FORBIDDEN')
