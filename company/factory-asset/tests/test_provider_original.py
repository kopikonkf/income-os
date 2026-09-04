import hashlib
import importlib.util
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jsonschema
import pytest
from PIL import Image, ImageFile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provider_original', ROOT / 'lib/provider_original.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
FIXTURES = ROOT / 'fixtures/provider-original-v1'
MANIFEST = json.loads((FIXTURES / 'manifest.json').read_text())
SCHEMA = json.loads((ROOT / 'schemas/provider-original-intake.schema.json').read_text())


def ingest(path, root, attempt='attempt-001', **kwargs):
    return m.intake_provider_original(
        source_path=path, staging_root=root, attempt_id=attempt,
        semantic_asset_id='FASA-ORIGINAL_001', blueprint_id='FABP-ORIGINAL_001',
        provider_id=kwargs.pop('provider_id', 'synthetic-fixture-provider'), **kwargs)


@pytest.mark.parametrize('fixture', MANIFEST['fixtures'], ids=lambda row: row['filename'])
def test_four_formats_are_sniffed_hash_pinned_and_preserved(tmp_path, fixture):
    source = FIXTURES / fixture['filename']
    before = source.read_bytes()
    before_stat = source.stat()
    expected_hash = hashlib.sha256(before).hexdigest()
    assert expected_hash == fixture['sha256']
    receipt = ingest(source, tmp_path, expected_sha256=expected_hash)
    jsonschema.Draft202012Validator(SCHEMA).validate(receipt)
    observed = receipt['provider_original']['media']
    for key, expected in fixture['media'].items():
        assert observed[key] == expected, key
    assert observed['bytes'] == len(before)
    assert receipt['source_sha256'] == receipt['provider_original']['sha256'] == expected_hash
    assert receipt['state_manager_proposal']['master_sha256'] == expected_hash
    blob = Path(receipt['staged_blob_path'])
    assert blob.name == expected_hash and blob.read_bytes() == before
    assert receipt['source_bytes'] == len(before)
    assert source.read_bytes() == before and source.stat().st_mtime_ns == before_stat.st_mtime_ns
    if os.name != 'nt':
        assert blob.stat().st_mode & 0o222 == 0
    assert receipt['canonical_truth'] is False
    assert receipt['ingestion_state'] == 'STAGED_NOT_CANONICAL'
    assert receipt['state_manager_proposal']['physical_writer_required'] == 'DIE_STATE_MANAGER'


def test_provider_and_declared_mime_cannot_override_actual_encoding(tmp_path):
    receipt = ingest(FIXTURES / 'opaque.jpg', tmp_path,
                     provider_id='provider-usually-returns-png', declared_mime_type='image/png')
    assert receipt['provider_original']['declared_mime_matches'] is False
    assert receipt['provider_original']['media']['mime_type'] == 'image/jpeg'
    assert receipt['provider_original']['declared_mime_type'] == 'image/png'


def test_matching_declared_mime_is_normalized_only_for_comparison(tmp_path):
    receipt = ingest(FIXTURES / 'opaque.jpg', tmp_path, declared_mime_type='IMAGE/JPEG; charset=binary')
    assert receipt['provider_original']['declared_mime_matches'] is True


@pytest.mark.parametrize('fixture', MANIFEST['fixtures'], ids=lambda row: row['filename'])
def test_extension_content_mismatch_rejected_before_staging(tmp_path, fixture):
    source = tmp_path / ('wrong.jpg' if fixture['media']['format'] != 'JPEG' else 'wrong.png')
    source.write_bytes((FIXTURES / fixture['filename']).read_bytes())
    with pytest.raises(m.ProviderOriginalError, match='EXTENSION_CONTENT_MISMATCH'):
        ingest(source, tmp_path / 'stage')
    assert not (tmp_path / 'stage').exists()


@pytest.mark.parametrize('filename', ['opaque.jpg', 'opaque.png', 'alpha.webp', 'alpha.tiff'])
@pytest.mark.parametrize('cut', [1, 0.5])
def test_truncated_containers_fail_closed(tmp_path, filename, cut):
    original = (FIXTURES / filename).read_bytes()
    data = original[:-1] if cut == 1 else original[:int(len(original) * cut)]
    source = tmp_path / filename
    source.write_bytes(data)
    with pytest.raises(m.ProviderOriginalError, match='MEDIA_DECODE_FAILED'):
        ingest(source, tmp_path / 'stage')
    assert source.read_bytes() == data and not (tmp_path / 'stage').exists()


@pytest.mark.parametrize('data,code', [
    (b'', 'SOURCE_EMPTY'), (b'<html>provider error</html>', 'MEDIA_MAGIC_UNSUPPORTED'),
    (b'\xff\xd8\xffgarbage\xff\xd9', 'MEDIA_DECODE_FAILED'),
    (b'\x89PNG\r\n\x1a\ninvalid\x00\x00\x00\x00IEND\xaeB`\x82', 'MEDIA_DECODE_FAILED'),
    (b'II*\x00garbage', 'MEDIA_DECODE_FAILED'),
])
def test_malformed_or_non_media_rejected(tmp_path, data, code):
    source = tmp_path / 'download'
    source.write_bytes(data)
    with pytest.raises(m.ProviderOriginalError, match=code):
        ingest(source, tmp_path / 'stage')
    assert not (tmp_path / 'stage').exists()


def test_palette_and_rgb_transparency_are_observed_without_alpha_band(tmp_path):
    for name in ['palette.png', 'rgb-key.png']:
        media = ingest(FIXTURES / name, tmp_path, attempt=name)['provider_original']['media']
        assert media['has_transparency'] is True
        assert media['has_alpha_channel'] is False
        assert media['has_transparency_metadata'] is True


def test_opaque_rgba_is_distinct_from_actual_transparency(tmp_path):
    media = ingest(FIXTURES / 'opaque-rgba.png', tmp_path)['provider_original']['media']
    assert media['has_alpha_channel'] is True and media['has_transparency'] is False
    assert media['alpha_min'] == media['alpha_max'] == 255


def test_dedupe_across_extension_aliases_and_provider_lineages(tmp_path):
    original = (FIXTURES / 'opaque.jpg').read_bytes()
    first = tmp_path / 'first.jpg'
    second = tmp_path / 'second.JPEG'
    first.write_bytes(original)
    second.write_bytes(original)
    a = ingest(first, tmp_path / 'stage', 'a', provider_id='provider-a')
    b = ingest(second, tmp_path / 'stage', 'b', provider_id='provider-b')
    assert a['staged_blob_path'] == b['staged_blob_path']
    assert a['blob_reused'] is False and b['blob_reused'] is True
    assert b['provider_original']['source_filename'] == 'second.JPEG'
    index = m._ingestion.staged_index(tmp_path / 'stage')
    assert index['attempt_count'] == 2 and index['unique_blob_count'] == 1
    assert first.read_bytes() == second.read_bytes() == original


def test_same_attempt_retry_is_idempotent(tmp_path):
    source = FIXTURES / 'opaque.jpg'
    a = ingest(source, tmp_path)
    assert ingest(source, tmp_path) == a


def test_attempt_conflict_does_not_publish_second_blob(tmp_path):
    a = ingest(FIXTURES / 'opaque.jpg', tmp_path)
    with pytest.raises(m.MasterIngestionError, match='ATTEMPT_ID_CONFLICT'):
        ingest(FIXTURES / 'opaque.png', tmp_path)
    assert m._ingestion.staged_index(tmp_path)['unique_blob_count'] == 1
    assert ingest(FIXTURES / 'opaque.jpg', tmp_path) == a


@pytest.mark.parametrize('attempt', ['attempt-001', 'attempt-002'])
def test_tampered_blob_is_not_replaced(tmp_path, attempt):
    a = ingest(FIXTURES / 'opaque.jpg', tmp_path)
    blob = Path(a['staged_blob_path'])
    blob.chmod(0o600)
    blob.write_bytes(b'tampered')
    with pytest.raises(m.MasterIngestionError, match='CONTENT_ADDRESS_COLLISION'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path, attempt)
    assert blob.read_bytes() == b'tampered'


def test_expected_hash_failure_has_no_staging_side_effects(tmp_path):
    with pytest.raises(m.ProviderOriginalError, match='SOURCE_HASH_MISMATCH'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path / 'stage', expected_sha256='0' * 64)
    assert not (tmp_path / 'stage').exists()


def test_extensionless_original_is_preserved(tmp_path):
    source = tmp_path / 'download'
    source.write_bytes((FIXTURES / 'opaque.png').read_bytes())
    receipt = ingest(source, tmp_path / 'stage')
    assert receipt['provider_original']['media']['format'] == 'PNG'
    assert receipt['provider_original']['media']['extension'] == ''
    assert source.exists() and not source.with_suffix('.png').exists()


@pytest.mark.parametrize('attempt', ['../escape', '/escape', 'a/b', 'a\\b', '..', ''])
def test_unsafe_attempt_identity_rejected(tmp_path, attempt):
    with pytest.raises(m.MasterIngestionError, match='INGESTION_IDENTITY_INCOMPLETE'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path / 'stage', attempt)
    assert not (tmp_path / 'stage').exists()


def test_snapshot_prevents_source_mutation_between_validation_and_copy(tmp_path, monkeypatch):
    source = tmp_path / 'input.png'
    original = (FIXTURES / 'opaque.png').read_bytes()
    source.write_bytes(original)
    stage = m._ingestion.stage_master_snapshot
    def mutate_then_stage(**kwargs):
        source.write_bytes(b'external mutation after read')
        return stage(**kwargs)
    monkeypatch.setattr(m._ingestion, 'stage_master_snapshot', mutate_then_stage)
    receipt = ingest(source, tmp_path / 'stage')
    assert Path(receipt['staged_blob_path']).read_bytes() == original
    assert receipt['source_bytes'] == len(original)
    assert source.read_bytes() == b'external mutation after read'


def test_concurrent_identical_attempts_publish_one_receipt_and_blob(tmp_path):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: ingest(FIXTURES / 'opaque.png', tmp_path), range(8)))
    assert all(receipt == results[0] for receipt in results)
    index = m._ingestion.staged_index(tmp_path)
    assert index['unique_blob_count'] == index['attempt_count'] == 1
    assert not list(tmp_path.rglob('.intake-*'))


def test_permissive_global_decoder_setting_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(ImageFile, 'LOAD_TRUNCATED_IMAGES', True)
    with pytest.raises(m.ProviderOriginalError, match='UNSAFE_DECODER_CONFIGURATION'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path / 'stage')


def test_byte_and_pixel_limits_apply_before_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'MAX_SOURCE_BYTES', 10)
    with pytest.raises(m.ProviderOriginalError, match='SOURCE_TOO_LARGE'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path / 'stage')
    monkeypatch.setattr(m, 'MAX_SOURCE_BYTES', 100000)
    monkeypatch.setattr(m, 'MAX_PIXELS', 1)
    with pytest.raises(m.ProviderOriginalError, match='MEDIA_PIXEL_LIMIT'):
        ingest(FIXTURES / 'opaque.jpg', tmp_path / 'stage')
    assert not (tmp_path / 'stage').exists()


def test_multiframe_tiff_is_rejected_instead_of_reporting_first_frame(tmp_path):
    source = tmp_path / 'pages.tiff'
    image = Image.new('RGB', (4, 4))
    image.save(source, save_all=True, append_images=[image])
    with pytest.raises(m.ProviderOriginalError, match='MULTIFRAME_UNSUPPORTED'):
        ingest(source, tmp_path / 'stage')


def test_missing_source_is_typed(tmp_path):
    with pytest.raises(m.ProviderOriginalError, match='SOURCE_UNREADABLE'):
        ingest(tmp_path / 'missing.png', tmp_path / 'stage')


@pytest.mark.skipif(os.name == 'nt', reason='Linux lane symlink safety')
def test_source_symlink_cannot_hide_misleading_extension(tmp_path):
    source = tmp_path / 'wrong.jpg'
    source.symlink_to(FIXTURES / 'opaque.png')
    with pytest.raises(m.ProviderOriginalError, match='EXTENSION_CONTENT_MISMATCH'):
        ingest(source, tmp_path / 'stage')


@pytest.mark.skipif(os.name == 'nt', reason='Linux lane symlink safety')
def test_staging_subdirectory_symlink_cannot_write_outside_root(tmp_path):
    root = tmp_path / 'stage'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / 'blobs').symlink_to(outside, target_is_directory=True)
    with pytest.raises(m.MasterIngestionError, match='STAGING_PATH_UNSAFE'):
        ingest(FIXTURES / 'opaque.png', root)
    assert not list(outside.iterdir())


def test_missing_pinned_blob_is_evidence_corruption_not_silent_repair(tmp_path):
    receipt = ingest(FIXTURES / 'opaque.png', tmp_path)
    blob = Path(receipt['staged_blob_path'])
    blob.chmod(0o600)
    blob.unlink()
    with pytest.raises(m.MasterIngestionError, match='CONTENT_ADDRESS_COLLISION'):
        ingest(FIXTURES / 'opaque.png', tmp_path)
    assert not blob.exists()


def test_png_crc_corruption_fails_even_with_valid_magic_and_end_chunk(tmp_path):
    data = bytearray((FIXTURES / 'opaque.png').read_bytes())
    index = data.index(b'IDAT') + 4
    data[index] ^= 1
    source = tmp_path / 'corrupt.png'
    source.write_bytes(data)
    with pytest.raises(m.ProviderOriginalError, match='MEDIA_DECODE_FAILED'):
        ingest(source, tmp_path / 'stage')


@pytest.mark.parametrize('contents', ['[]', 'null', '{broken-json'])
def test_corrupt_attempt_receipt_fails_with_typed_conflict(tmp_path, contents):
    receipt = ingest(FIXTURES / 'opaque.png', tmp_path)
    path = Path(receipt['state_manager_proposal']['attempt_receipt_path'])
    path.chmod(0o600)
    path.write_text(contents)
    with pytest.raises(m.MasterIngestionError, match='ATTEMPT_ID_CONFLICT'):
        ingest(FIXTURES / 'opaque.png', tmp_path)
    assert path.read_text() == contents
