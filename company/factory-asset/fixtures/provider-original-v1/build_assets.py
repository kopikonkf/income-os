"""Build FA-131 synthetic acceptance fixtures and strict evidence schema."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / 'fixtures/provider-original-v1'
FIX.mkdir(parents=True, exist_ok=True)
rgb = Image.new('RGB', (12, 8), (20, 40, 80))
rgba = rgb.convert('RGBA')
rgba.putpixel((0, 0), (20, 40, 80, 0))
rgba.putpixel((1, 0), (20, 40, 80, 128))
rgb.save(FIX / 'opaque.jpg', format='JPEG', quality=90)
rgb.save(FIX / 'opaque.png', format='PNG')
rgb.convert('RGBA').save(FIX / 'opaque-rgba.png', format='PNG')
rgba.save(FIX / 'alpha.png', format='PNG')
rgba.save(FIX / 'alpha.webp', format='WEBP', lossless=True)
rgba.save(FIX / 'alpha.tiff', format='TIFF', compression='raw')
palette = Image.new('P', (12, 8), 1)
palette.putpalette([0, 0, 0, 20, 40, 80] + [0] * 762)
palette.putpixel((0, 0), 0)
palette.save(FIX / 'palette.png', transparency=0)
rgb.save(FIX / 'rgb-key.png', transparency=(20, 40, 80))
fixtures = []
for filename, fmt, alpha, metadata, transparency, amin, amax in [
    ('opaque.jpg', 'JPEG', False, False, False, 255, 255),
    ('opaque.png', 'PNG', False, False, False, 255, 255),
    ('opaque-rgba.png', 'PNG', True, False, False, 255, 255),
    ('alpha.png', 'PNG', True, False, True, 0, 255),
    ('alpha.webp', 'WEBP', True, False, True, 0, 255),
    ('alpha.tiff', 'TIFF', True, False, True, 0, 255),
    ('palette.png', 'PNG', False, True, True, 0, 255),
    ('rgb-key.png', 'PNG', False, True, True, 0, 0),
]:
    fixtures.append({'filename': filename, 'sha256': hashlib.sha256((FIX / filename).read_bytes()).hexdigest(),
                     'media': {'format': fmt, 'mime_type': 'image/' + fmt.lower(),
                               'width_px': 12, 'height_px': 8, 'frame_count': 1,
                               'has_alpha_channel': alpha, 'has_transparency_metadata': metadata,
                               'has_transparency': transparency, 'alpha_min': amin, 'alpha_max': amax}})
(FIX / 'manifest.json').write_text(json.dumps({'schema': 'die.factory-asset.provider-original-fixtures.v1',
    'synthetic': True, 'provider_calls': 0, 'fixtures': fixtures}, indent=2) + '\n')

def obj(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}
string = {'type': 'string', 'minLength': 1}
hash_schema = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
positive = {'type': 'integer', 'minimum': 1}
boolean = {'type': 'boolean'}
media = obj({
    'format': {'enum': ['JPEG', 'PNG', 'WEBP', 'TIFF']},
    'mime_type': {'enum': ['image/jpeg', 'image/png', 'image/webp', 'image/tiff']},
    'magic_hex': {'type': 'string', 'pattern': '^[0-9a-f]{24}$'},
    'bytes': positive, 'width_px': positive, 'height_px': positive,
    'mode': string, 'frame_count': {'const': 1},
    'has_alpha_channel': boolean, 'has_transparency_metadata': boolean,
    'has_transparency': boolean,
    'alpha_min': {'type': 'integer', 'minimum': 0, 'maximum': 255},
    'alpha_max': {'type': 'integer', 'minimum': 0, 'maximum': 255},
    'extension': {'type': 'string'}, 'extension_content_match': {'const': True},
    'decode_verified': {'const': True},
})
evidence = obj({
    'schema': {'const': 'die.factory-asset.provider-original.v1'},
    'provider_id': string, 'source_filename': string,
    'declared_mime_type': {'type': ['string', 'null']},
    'declared_mime_matches': {'type': ['boolean', 'null']},
    'sha256': hash_schema, 'media': media,
    'byte_preservation': {'const': 'EXACT_COPY'}, 'transformation': {'const': 'NONE'},
    'semantic_identity_effect': {'const': 'NONE'},
})
schema = obj({
    'schema': {'const': 'die.factory-asset.master-ingestion-attempt.v1'},
    'attempt_id': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$'},
    'semantic_asset_id': string, 'blueprint_id': string, 'source_path': string,
    'source_sha256': hash_schema, 'source_bytes': positive, 'staged_blob_path': string,
    'blob_reused': boolean, 'provider_original': evidence,
    'ingestion_state': {'const': 'STAGED_NOT_CANONICAL'}, 'canonical_truth': {'const': False},
    'state_manager_commit_required': {'const': True},
    'state_manager_proposal': obj({
        'schema': {'const': 'die.factory-asset.master-ingestion-proposal.v1'},
        'action': {'const': 'FACTORY_MASTER_INGEST'}, 'semantic_asset_id': string,
        'blueprint_id': string, 'master_sha256': hash_schema, 'staged_blob_path': string,
        'attempt_receipt_path': string, 'physical_writer_required': {'const': 'DIE_STATE_MANAGER'},
    }),
})
schema.update({'$schema': 'https://json-schema.org/draft/2020-12/schema',
               'title': 'FA-131 provider-original master intake evidence'})
(ROOT / 'schemas/provider-original-intake.schema.json').write_text(json.dumps(schema, indent=2) + '\n')
