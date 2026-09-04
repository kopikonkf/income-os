"""FA-131: inspect local provider artifacts and pin exact bytes for master intake."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import struct
import warnings
from pathlib import Path
from typing import Any

from PIL import Image, ImageFile

_spec = importlib.util.spec_from_file_location(
    'factory_asset_master_ingestion', Path(__file__).with_name('master_ingestion.py'))
_ingestion = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ingestion)
MasterIngestionError = _ingestion.MasterIngestionError

FORMATS = {
    'JPEG': ('image/jpeg', {'.jpg', '.jpeg', '.jpe'}),
    'PNG': ('image/png', {'.png'}),
    'WEBP': ('image/webp', {'.webp'}),
    'TIFF': ('image/tiff', {'.tif', '.tiff'}),
}
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_PIXELS = 40_000_000


class ProviderOriginalError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def _magic_format(data: bytes) -> str:
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'
    if data.startswith(b'\xff\xd8\xff'):
        return 'JPEG'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'WEBP'
    if data[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        return 'TIFF'
    raise ProviderOriginalError('MEDIA_MAGIC_UNSUPPORTED', 'expected JPEG, PNG, WebP or TIFF')


def sniff_media(data: bytes, *, filename: str) -> dict[str, Any]:
    """Derive facts from fully decoded bytes, never filename/provider claims.

    v0.1 is a single-frame raster contract. Animation/multipage containers are
    rejected so first-frame facts cannot masquerade as complete master evidence.
    """
    if not data:
        raise ProviderOriginalError('SOURCE_EMPTY', filename)
    if len(data) > MAX_SOURCE_BYTES:
        raise ProviderOriginalError('SOURCE_TOO_LARGE', str(len(data)))
    fmt = _magic_format(data)
    extension = Path(filename).suffix.lower()
    if extension and extension not in FORMATS[fmt][1]:
        raise ProviderOriginalError('EXTENSION_CONTENT_MISMATCH', f'{extension} contains {fmt}')
    # Pillow can accept some missing terminators or altered global decoder policy.
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ProviderOriginalError('UNSAFE_DECODER_CONFIGURATION', 'strict decoding required')
    if fmt == 'JPEG' and not data.endswith(b'\xff\xd9'):
        raise ProviderOriginalError('MEDIA_DECODE_FAILED', 'JPEG end marker missing')
    if fmt == 'PNG' and not data.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82'):
        raise ProviderOriginalError('MEDIA_DECODE_FAILED', 'PNG end chunk missing')
    if fmt == 'WEBP' and (len(data) < 12 or struct.unpack('<I', data[4:8])[0] + 8 != len(data)):
        raise ProviderOriginalError('MEDIA_DECODE_FAILED', 'WebP RIFF length mismatch')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format != fmt:
                    raise ProviderOriginalError('MAGIC_DECODER_MISMATCH', fmt)
                if probe.width * probe.height > MAX_PIXELS:
                    raise ProviderOriginalError('MEDIA_PIXEL_LIMIT', str(probe.size))
                if getattr(probe, 'n_frames', 1) != 1:
                    raise ProviderOriginalError('MULTIFRAME_UNSUPPORTED', fmt)
                probe.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
                alpha_channel = 'A' in decoded.getbands()
                alpha_metadata = 'transparency' in decoded.info
                alpha_min, alpha_max = (255, 255)
                if alpha_channel or alpha_metadata:
                    alpha_min, alpha_max = decoded.convert('RGBA').getchannel('A').getextrema()
                return {
                    'format': fmt, 'mime_type': FORMATS[fmt][0],
                    'magic_hex': data[:12].hex(), 'bytes': len(data),
                    'width_px': decoded.width, 'height_px': decoded.height,
                    'mode': decoded.mode, 'frame_count': 1,
                    'has_alpha_channel': alpha_channel,
                    'has_transparency_metadata': alpha_metadata,
                    'has_transparency': alpha_min < 255,
                    'alpha_min': alpha_min, 'alpha_max': alpha_max,
                    'extension': extension, 'extension_content_match': True,
                    'decode_verified': True,
                }
    except ProviderOriginalError:
        raise
    except Exception as exc:
        raise ProviderOriginalError('MEDIA_DECODE_FAILED', str(exc)) from exc


def intake_provider_original(*, source_path: str | Path, staging_root: str | Path,
                             attempt_id: str, semantic_asset_id: str,
                             blueprint_id: str, provider_id: str,
                             expected_sha256: str | None = None,
                             declared_mime_type: str | None = None) -> dict[str, Any]:
    """Read once, strictly validate, then stage the same immutable byte snapshot.

    provider_id is supplied lineage, not proof that this file came from a provider.
    A declared MIME is retained as an untrusted claim alongside derived facts.
    """
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ProviderOriginalError('PROVIDER_ID_REQUIRED', 'provider lineage required')
    if declared_mime_type is not None and not isinstance(declared_mime_type, str):
        raise ProviderOriginalError('DECLARED_MIME_INVALID', 'expected string or null')
    source_name = Path(source_path).name
    source = Path(source_path).resolve()
    try:
        with source.open('rb') as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise ProviderOriginalError('SOURCE_UNREADABLE', str(source)) from exc
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ProviderOriginalError('SOURCE_HASH_MISMATCH', digest)
    media = sniff_media(data, filename=source_name)
    evidence = {
        'schema': 'die.factory-asset.provider-original.v1',
        'provider_id': provider_id, 'source_filename': source_name,
        'declared_mime_type': declared_mime_type,
        'declared_mime_matches': None if declared_mime_type is None else
            declared_mime_type.split(';', 1)[0].strip().lower() == media['mime_type'],
        'sha256': digest, 'media': media,
        'byte_preservation': 'EXACT_COPY', 'transformation': 'NONE',
        'semantic_identity_effect': 'NONE',
    }
    return _ingestion.stage_master_snapshot(
        source_bytes=data, source_path=source, staging_root=staging_root,
        attempt_id=attempt_id, semantic_asset_id=semantic_asset_id,
        blueprint_id=blueprint_id, expected_sha256=digest,
        provider_original=evidence)
