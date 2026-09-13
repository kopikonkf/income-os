from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[4]
H01 = ROOT / 'company/company-os/die-h01'
SCHEMA = H01 / 'contracts/h01-provider-output-acquisition-v1.schema.json'
REVISION = '1.1.0'
SVG_RE = re.compile(r'<svg\b[\s\S]*?</svg>', re.IGNORECASE)
FENCE_RE = re.compile(r'^```(?:svg|xml)?\s*([\s\S]*?)\s*```$', re.IGNORECASE)
NUMBER_RE = re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')
GEOMETRY_TAGS = {'path','polygon','polyline','rect','circle','ellipse','line'}
ALLOWED_FRAGMENT_TAGS = GEOMETRY_TAGS | {'g'}
GEOMETRY_NUMERIC_ATTRS = {'d','points','x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','width','height','transform'}

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


def _unwrap_surface_text(text: str) -> str:
    stripped = text.strip()
    fence = FENCE_RE.fullmatch(stripped)
    return fence.group(1).strip() if fence else stripped

def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag

def _normalize_alpha_hex(root: ET.Element) -> int:
    count = 0
    for el in root.iter():
        for attr, opacity_attr in (('fill','fill-opacity'),('stroke','stroke-opacity')):
            value = el.attrib.get(attr)
            if not value or not value.startswith('#'):
                continue
            h = value[1:]
            if len(h) == 8 and re.fullmatch(r'[0-9a-fA-F]{8}', h):
                rgb, alpha = h[:6], int(h[6:8], 16) / 255.0
            elif len(h) == 4 and re.fullmatch(r'[0-9a-fA-F]{4}', h):
                rgb, alpha = ''.join(ch*2 for ch in h[:3]), int(h[3]*2, 16) / 255.0
            else:
                continue
            try:
                previous = float(el.attrib.get(opacity_attr, '1'))
            except ValueError as exc:
                raise ProviderOutputError('SVG_FRAGMENT_OPACITY_INVALID', el.attrib.get(opacity_attr, '')) from exc
            el.set(attr, '#'+rgb.lower())
            el.set(opacity_attr, format(previous * alpha, '.12g'))
            count += 1
    return count

def _derive_fragment_viewbox(root: ET.Element) -> tuple[float,float,float,float]:
    nums: list[float] = []
    allowed = ALLOWED_FRAGMENT_TAGS | {'svg'}
    for el in root.iter():
        local = _local_name(el.tag)
        if local not in allowed:
            raise ProviderOutputError('SVG_FRAGMENT_UNSUPPORTED_ELEMENT', local)
        for key, value in el.attrib.items():
            if _local_name(key) not in GEOMETRY_NUMERIC_ATTRS:
                continue
            for token in NUMBER_RE.findall(value):
                number = float(token)
                if math.isfinite(number):
                    nums.append(number)
    if len(nums) < 2:
        raise ProviderOutputError('SVG_FRAGMENT_BOUNDS_MISSING')
    lo, hi = min(nums), max(nums)
    span = max(1.0, hi - lo)
    margin = max(8.0, span * 0.10)
    return lo - margin, lo - margin, span + 2*margin, span + 2*margin

def _normalize_geometry_fragment(provider_response_text: str) -> tuple[str, dict[str, Any]]:
    fragment = _unwrap_surface_text(provider_response_text)
    if '<svg' in fragment.lower() or '</svg>' in fragment.lower():
        raise ProviderOutputError('OUTPUT_NOT_SVG', 'incomplete SVG root is not a geometry fragment')
    geometry_count = sum(len(re.findall(fr'<{tag}\b', fragment, re.I)) for tag in GEOMETRY_TAGS)
    if geometry_count < 1:
        raise ProviderOutputError('OUTPUT_NOT_SVG', 'no complete SVG rocument or SVG geometry fragment')
    for pat in FORBIDDEN_SVG:
        if pat.search(fragment):
            raise ProviderOutputError('SVG_FORBIDDEN_FEATURE', pat.pattern)
    try:
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{fragment}</svg>')
    except ET.ParseError as exc:
        raise ProviderOutputError('SVG_FRAGMENT_XML_INVALID', str(exc)) from exc
    alpha_count = _normalize_alpha_hex(root)
    x, y, w, h = _derive_fragment_viewbox(root)
    root.set('viewBox', f'{x:.12g} {y:.12g} {w:.12g} {h:.12g}')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    candidate = ET.tostring(root, encoding='unicode')
    if len(candidate.encode('utf-8')) > 1_048_576:
        raise ProviderOutputError('SVG_TOO_LARGE')
    normalization = {
        'method': 'SVG_GEOMETRY_FRAGMENT_ENVELOPE_V1',
        'provider_reprompted': False,
        'geometry_preserved': True,
        'raw_surface_sha256': sha256_text(provider_response_text),
        'geometry_fragment_sha256': sha256_text(fragment),
        'normalized_candidate_sha256': sha256_text(candidate),
        'geometry_tag_count': geometry_count,
        'alpha_hex_normalizations': alpha_count,
        'derived_viewbox': [x, y, w, h],
    }
    return candidate, normalization

def extract_svg_surface(provider_response_text: str) -> dict[str, Any]:
    if not isinstance(provider_response_text, str) or not provider_response_text.strip():
        raise ProviderOutputError('EMPTY_PROVIDER_OUTPUT')
    matches = [m.group(0).strip() for m in SVG_RE.finditer(provider_response_text)]
    if len(matches) > 1:
        raise ProviderOutputError('AMBIGUOUS_PROVIDER_OUTPUT', f'{len(matches)} SVG candidates')
    if len(matches) == 1:
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
        return {'candidate_svg': svg, 'source_kind': _source_method(provider_response_text, svg), 'normalization': None}
    candidate, normalization = _normalize_geometry_fragment(provider_response_text)
    return {'candidate_svg': candidate, 'source_kind': 'SVG_GEOMETRY_FRAGMENT', 'normalization': normalization}


def extract_single_svg(provider_response_text: str) -> tuple[str, str]:
    surface = extract_svg_surface(provider_response_text)
    return surface['candidate_svg'], surface['source_kind']


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
    provider_surface_path: Path | None = None,
    normalization: dict[str, Any] | None = None,
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
    if provider_surface_path is not None:
        raw = provider_response_text.encode('utf-8')
        receipt['provider_surface'] = {
            'path': str(provider_surface_path),
            'sha256': sha256_bytes(raw),
            'bytes': len(raw),
            'immutable_raw_provider_surface': True,
        }
    if normalization is not None:
        receipt['normalization'] = normalization
        receipt['artifact']['immutable_provider_original'] = False
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
    surface = extract_svg_surface(provider_response_text)
    candidate = surface['candidate_svg']
    method = surface['source_kind']
    normalization = surface['normalization']
    out = Path(output_dir)
    raw_surface = out / 'provider-surface.raw.txt'
    raw_state = _atomic_bytes(raw_surface, provider_response_text.encode('utf-8'))
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
        provider_surface_path=raw_surface,
        normalization=normalization,
    )
    receipt_state = _atomic_json(out / 'provider-output-acquisition.receipt.json', receipt)
    return receipt, f'{raw_state}/{artifact_state}/{receipt_state}'


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
