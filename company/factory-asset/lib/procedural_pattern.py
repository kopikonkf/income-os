from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
NATIVE_SCHEMA = json.loads((ROOT / 'company/factory-asset/schemas/native-producer.schema.json').read_text(encoding='utf-8'))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

native_vector = _load('pattern_native_vector', ROOT / 'company/factory-asset/lib/native_vector.py')

class PatternProducerError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _validate_hex_color(value: str) -> None:
    if not isinstance(value, str) or len(value) != 7 or value[0] != '#':
        raise PatternProducerError('INVALID_COLOR', str(value))
    try:
        int(value[1:], 16)
    except ValueError as exc:
        raise PatternProducerError('INVALID_COLOR', value) from exc


def _validate_request(request: dict[str, Any]) -> dict[str, Any]:
    jsonschema.Draft202012Validator(NATIVE_SCHEMA).validate(request)
    if request['kind'] != 'REQUEST' or request['producer_class'] != 'PROCEDURAL_VECTOR':
        raise PatternProducerError('WRONG_PRODUCER_CLASS', str(request.get('producer_class')))
    p = request['parameters']
    allowed = {'recipe_kind','seed','tile_width','tile_height','motif_count','motif_size','background_color','motif_colors','preview_repeat'}
    unknown = sorted(set(p) - allowed)
    if unknown:
        raise PatternProducerError('UNKNOWN_PATTERN_PARAMETER', ','.join(unknown))
    required = allowed - set(p)
    if required:
        raise PatternProducerError('PATTERN_PARAMETER_MISSING', ','.join(sorted(required)))
    if p['recipe_kind'] != 'SCATTERED_DIAMONDS':
        raise PatternProducerError('PATTERN_RECIPE_UNSUPPORTED', str(p['recipe_kind']))
    for key in ('seed','tile_width','tile_height','motif_count','motif_size','preview_repeat'):
        if not isinstance(p[key], int) or isinstance(p[key], bool):
            raise PatternProducerError('PATTERN_INTEGER_REQUIRED', key)
    if not (32 <= p['tile_width'] <= 2048 and 32 <= p['tile_height'] <= 2048):
        raise PatternProducerError('PATTERN_TILE_BOUNDS', f"{p['tile_width']}x{p['tile_height']}")
    if not (1 <= p['motif_count'] <= 128):
        raise PatternProducerError('PATTERN_MOTIF_COUNT', str(p['motif_count']))
    if not (4 <= p['motif_size'] <= min(p['tile_width'], p['tile_height']) // 3):
        raise PatternProducerError('PATTERN_MOTIF_SIZE', str(p['motif_size']))
    if not (2 <= p['preview_repeat'] <= 8):
        raise PatternProducerError('PATTERN_PREVIEW_REPEAT', str(p['preview_repeat']))
    _validate_hex_color(p['background_color'])
    colors = p['motif_colors']
    if not isinstance(colors, list) or not colors or len(colors) > 16:
        raise PatternProducerError('PATTERN_COLORS_INVALID', str(colors))
    for color in colors:
        _validate_hex_color(color)
    return p


def _diamond(cx: int, cy: int, half: int) -> list[tuple[int, int]]:
    return [(cx, cy-half), (cx+half, cy), (cx, cy+half), (cx-half, cy), (cx, cy-half)]


def _path(points: list[tuple[int,int]]) -> str:
    return 'M ' + ' L '.join(f'{x} {y}' for x,y in points) + ' Z'


def _build_pattern(parameters: dict[str, Any]) -> dict[str, Any]:
    w, h = parameters['tile_width'], parameters['tile_height']
    half = parameters['motif_size'] // 2
    rng = random.Random(parameters['seed'])
    motifs: list[dict[str, Any]] = []
    margin = half + 1
    for index in range(parameters['motif_count']):
        cx = rng.randint(margin, w - margin)
        cy = rng.randint(margin, h - margin)
        color = parameters['motif_colors'][rng.randrange(len(parameters['motif_colors']))]
        motifs.append({'index': index, 'points': _diamond(cx, cy, half), 'fill': color})
    bg = [(0,0),(w,0),(w,h),(0,h),(0,0)]
    pieces = [f'<path d="{_path(bg)}" fill="{parameters["background_color"]}" stroke="none"/>']
    pieces.extend(f'<path d="{_path(m["points"])}" fill="{m["fill"]}" stroke="none"/>' for m in motifs)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">' + ''.join(pieces) + '</svg>'
    normalized = native_vector.normalize_svg(svg, max_paths=129)
    return {'normalized': normalized, 'motifs': motifs}


def _preview(parameters: dict[str, Any], motifs: list[dict[str, Any]]) -> Image.Image:
    w, h, repeat = parameters['tile_width'], parameters['tile_height'], parameters['preview_repeat']
    img = Image.new('RGB', (w * repeat, h * repeat), parameters['background_color'])
    draw = ImageDraw.Draw(img)
    for ty in range(repeat):
        for tx in range(repeat):
            ox, oy = tx*w, ty*h
            for motif in motifs:
                pts = [(x+ox,y+oy) for x,y in motif['points'][:-1]]
                draw.polygon(pts, fill=motif['fill'])
    return img


def produce_pattern(request: dict[str, Any], *, output_dir: str | Path, cancelled: bool = False) -> dict[str, Any]:
    p = _validate_request(request)
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if cancelled:
        base = {'schema':'die.factory-asset.native-producer.v1','kind':'RECEIPT','job_id':request['job_id'],'idempotency_key':request['idempotency_key'],'producer_class':'PROCEDURAL_VECTOR','producer_version':request['producer_version'],'result':'CANCELLED','failure':{'code':'CANCELLED','retryable':False,'message':'cancelled before render'}}
        base['deterministic_receipt_sha256'] = sha256_bytes(_canonical(base))
        jsonschema.Draft202012Validator(NATIVE_SCHEMA).validate(base)
        return {'native_receipt': base, 'preview': None, 'pattern': None}
    built = _build_pattern(p)
    normalized = built['normalized']
    svg_bytes = normalized['canonical_svg'].encode('utf-8')
    svg_path = out / 'master.svg'
    preview_path = out / 'preview.png'
    svg_path.write_bytes(svg_bytes)
    image = _preview(p, built['motifs'])
    image.save(preview_path, format='PNG', optimize=False)
    with Image.open(preview_path) as check:
        check.load()
        preview_dims = list(check.size)
        preview_format = check.format
    master_sha = sha256_bytes(svg_bytes)
    preview_sha = sha256_bytes(preview_path.read_bytes())
    master = {'format':'SVG','sha256':master_sha,'bytes':len(svg_bytes),'native_editable':True,'generated_by_native_producer':True,'conversion_from_raster':False,'lineage_sha256_required':True}
    receipt_base = {'schema':'die.factory-asset.native-producer.v1','kind':'RECEIPT','job_id':request['job_id'],'idempotency_key':request['idempotency_key'],'producer_class':'PROCEDURAL_VECTOR','producer_version':request['producer_version'],'result':'PASS','master':master}
    receipt_base['deterministic_receipt_sha256'] = sha256_bytes(_canonical(receipt_base))
    jsonschema.Draft202012Validator(NATIVE_SCHEMA).validate(receipt_base)
    return {
        'native_receipt': receipt_base,
        'pattern': {'schema':'die.factory-asset.procedural-pattern-result.v1','recipe_kind':p['recipe_kind'],'seed':p['seed'],'parameters':p,'master_path':str(svg_path),'master_sha256':master_sha,'path_count':len(normalized['paths']),'embedded_raster':False,'editable_vector_paths':True},
        'preview': {'schema':'die.factory-asset.pattern-preview.v1','path':str(preview_path),'format':preview_format,'sha256':preview_sha,'bytes':preview_path.stat().st_size,'dimensions':preview_dims,'repeat':[p['preview_repeat'],p['preview_repeat']],'source_master_sha256':master_sha}
    }