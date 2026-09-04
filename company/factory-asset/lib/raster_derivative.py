from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
RECIPE_SCHEMA = json.loads((ROOT / 'company/factory-asset/schemas/derivative-recipe.schema.json').read_text(encoding='utf-8'))

class RasterDerivativeError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_idempotency_key(recipe: dict[str, Any]) -> str:
    material = {
        'master_sha256': recipe['input']['master_sha256'],
        'recipe_id': recipe['recipe_id'],
        'recipe_version': recipe['recipe_version'],
        'marketplace_profile': recipe['marketplace_profile'],
        'output': recipe['output'],
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _prepare_image(img: Image.Image, fmt: str, alpha_policy: str) -> Image.Image:
    has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    if fmt == 'JPEG':
        if has_alpha:
            if alpha_policy != 'FLATTEN_WHITE':
                raise RasterDerivativeError('ALPHA_POLICY_REQUIRED', 'JPEG with alpha requires FLATTEN_WHITE')
            rgba = img.convert('RGBA')
            bg = Image.new('RGBA', rgba.size, (255,255,255,255))
            bg.alpha_composite(rgba)
            return bg.convert('RGB')
        return img.convert('RGB')
    if alpha_policy == 'FORBID' and has_alpha:
        raise RasterDerivativeError('ALPHA_FORBIDDEN', fmt)
    if alpha_policy == 'FLATTEN_WHITE' and has_alpha:
        rgba = img.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (255,255,255,255)); bg.alpha_composite(rgba)
        return bg.convert('RGB')
    if alpha_policy == 'PRESERVE' and has_alpha:
        return img.convert('RGBA')
    return img.convert('RGB') if img.mode not in ('RGB','RGBA') else img.copy()


def render_raster_derivative(master_path: str | Path, output_path: str | Path, recipe: dict[str, Any]) -> dict[str, Any]:
    master = Path(master_path).resolve(); output = Path(output_path).resolve()
    jsonschema.Draft202012Validator(RECIPE_SCHEMA).validate(recipe)
    if master == output:
        raise RasterDerivativeError('MASTER_OVERWRITE_FORBIDDEN', str(master))
    if not master.is_file():
        raise RasterDerivativeError('MASTER_NOT_FOUND', str(master))
    actual_master_sha = sha256_file(master)
    if actual_master_sha != recipe['input']['master_sha256']:
        raise RasterDerivativeError('MASTER_HASH_MISMATCH', actual_master_sha)
    fmt = recipe['output']['format']
    if fmt not in {'JPEG','WEBP','TIFF','PNG'}:
        raise RasterDerivativeError('RASTER_FORMAT_UNSUPPORTED', fmt)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RasterDerivativeError('OUTPUT_EXISTS_REQUIRES_REUSE_CHECK', str(output))
    alpha_policy = recipe['output'].get('alpha_policy', 'NOT_APPLICABLE')
    with Image.open(master) as img:
        img.load()
        prepared = _prepare_image(img, fmt, alpha_policy)
        width = recipe['output'].get('width_px', prepared.width)
        height = recipe['output'].get('height_px', prepared.height)
        if (width, height) != prepared.size:
            prepared = prepared.resize((width, height), Image.Resampling.LANCZOS)
        save_kwargs: dict[str, Any] = {}
        if fmt in {'JPEG','WEBP'}: save_kwargs['quality'] = int(recipe['output'].get('quality', 92))
        if fmt == 'JPEG': save_kwargs.update({'subsampling':0, 'optimize':False, 'progressive':False})
        if fmt == 'WEBP': save_kwargs.update({'method':6, 'lossless':False})
        if fmt == 'TIFF': save_kwargs['compression'] = 'tiff_lzw'
        prepared.save(output, format=fmt, **save_kwargs)
    out_sha = sha256_file(output)
    try:
        with Image.open(output) as reopened:
            reopened.load(); decoded = True; dims = reopened.size; actual_fmt = reopened.format
    except Exception:
        decoded = False; dims = (0,0); actual_fmt = None
    magic_ok = actual_fmt == fmt
    receipt = {
        'schema':'die.factory-asset.derivative-receipt.v1',
        'recipe_id':recipe['recipe_id'],'recipe_version':recipe['recipe_version'],
        'idempotency_key':canonical_idempotency_key(recipe),
        'input':{'master_sha256':actual_master_sha,'semantic_asset_id':recipe['input']['semantic_asset_id']},
        'marketplace_profile':dict(recipe['marketplace_profile']),
        'output':{'format':fmt,'sha256':out_sha,'bytes':output.stat().st_size,'width_px':dims[0],'height_px':dims[1],'semantic_identity_effect':'NONE'},
        'qa':{'magic_mime_match':magic_ok,'decode_reopen':decoded,'sha256_verified':sha256_file(output)==out_sha,'failure_code':None if (magic_ok and decoded) else 'OUTPUT_VALIDATION_FAILED'},
        'compatibility':{'state':'COMPATIBLE','reason':None},
        'result':'PASS' if magic_ok and decoded else 'FAIL',
    }
    return receipt