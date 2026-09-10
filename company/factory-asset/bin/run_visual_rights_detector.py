#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / 'company' / 'factory-asset' / 'lib'
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import visual_rights_detector as core


def _load_runtime():
    import clip
    import numpy as np
    import torch
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    return clip, np, torch, Image, ImageDraw, ImageFont, ImageOps


def _run_tesseract(image_path: Path, *, pass_id: str, psm: int, timeout: int = 45) -> list[dict[str, Any]]:
    cp = subprocess.run(
        ['/usr/bin/tesseract', str(image_path), 'stdout', '--psm', str(psm), 'tsv'],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f'E_TESSERACT:{pass_id}:{cp.stderr[-400:]}')
    rows = []
    for r in csv.DictReader(io.StringIO(cp.stdout), delimiter='\t'):
        text = (r.get('text') or '').strip()
        if not text:
            continue
        try:
            conf = float(r.get('conf') or -1)
        except Exception:
            conf = -1
        rows.append({'pass_id': pass_id, 'text': text, 'confidence': conf})
    return rows


def _ocr_rows(master: Path, cfg: dict[str, Any], scratch: Path) -> list[dict[str, Any]]:
    _, _, _, Image, _, _, ImageOps = _load_runtime()
    im = Image.open(master).convert('L')
    auto = ImageOps.autocontrast(im)
    variants = [('autocontrast', auto)]
    for t in (140, 160, 200):
        variants.append((f'threshold_{t}', auto.point(lambda v, tt=t: 0 if v < tt else 255)))
    out = []
    scratch.mkdir(parents=True, exist_ok=True)
    for pass_id, image in variants:
        p = scratch / f'{pass_id}.png'
        image.save(p)
        out.extend(_run_tesseract(p, pass_id=pass_id, psm=int(cfg['ocr']['psm'])))
    return out


def _foreground_crop(im, cfg: dict[str, Any]):
    _, np, _, _, _, _, _ = _load_runtime()
    a = np.array(im.convert('RGB'))
    threshold = int(cfg['foreground']['white_distance_threshold'])
    mask = (255 - a).max(axis=2) > threshold
    if not mask.any():
        return im.convert('RGB'), [0, 0, im.width, im.height]
    ys, xs = np.where(mask)
    pad = int(cfg['foreground']['padding_px'])
    box = [
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(im.width, int(xs.max()) + 1 + pad),
        min(im.height, int(ys.max()) + 1 + pad),
    ]
    return im.crop(tuple(box)).convert('RGB'), box


def _clip_scores(master: Path, cfg: dict[str, Any], model, preprocess, clip, torch) -> dict[str, Any]:
    from PIL import Image
    im = Image.open(master).convert('RGB')
    fg, box = _foreground_crop(im, cfg)
    x = torch.stack([preprocess(im), preprocess(fg)])
    scores: dict[str, Any] = {'foreground_box': box}
    with torch.inference_mode():
        for key in ('logo', 'watermark', 'safety', 'source_ip'):
            prompts = cfg[key]['prompts']
            tokens = clip.tokenize(prompts)
            logits, _ = model(x, tokens)
            probs = logits.softmax(dim=-1).tolist()
            scores[key] = {
                'prompts': prompts,
                'full': [round(float(v), 8) for v in probs[0]],
                'foreground': [round(float(v), 8) for v in probs[1]],
            }
    return scores


def _evaluate_image(master: Path, cfg: dict[str, Any], *, model, preprocess, clip, torch, scratch: Path, stock_terms: list[str], asset_type: str = 'UNKNOWN') -> dict[str, Any]:
    sha = core.sha256_file(master)
    rows = _ocr_rows(master, cfg, scratch / 'ocr')
    ocr = core.ocr_consensus(
        rows,
        min_confidence=float(cfg['ocr']['min_confidence']),
        min_token_chars=int(cfg['ocr']['min_token_chars']),
        min_consensus_passes=int(cfg['ocr']['min_consensus_passes']),
    )
    cs = _clip_scores(master, cfg, model, preprocess, clip, torch)
    logo = core.classify_logo(full_scores=cs['logo']['full'], foreground_scores=cs['logo']['foreground'], cfg=cfg['logo'])
    watermark = core.classify_watermark(full_scores=cs['watermark']['full'], cfg=cfg['watermark'])
    safety = core.classify_safety(full_scores=cs['safety']['full'], foreground_scores=cs['safety']['foreground'], cfg=cfg['safety'])
    source_ip = core.classify_source_ip(full_scores=cs['source_ip']['full'], foreground_scores=cs['source_ip']['foreground'], cfg=cfg['source_ip'], asset_type=asset_type)
    obs = core.build_rights_observation(master_sha256=sha, ocr=ocr, logo=logo, watermark=watermark, safety=safety, stock_watermark_terms=stock_terms)
    return {
        'schema': 'die.factory-asset.visual-rights-detector-run.v1',
        'master_path': str(master),
        'master_sha256': sha,
        'ocr': ocr,
        'clip_scores': cs,
        'classification': {'logo': logo, 'watermark': watermark, 'safety': safety, 'source_ip': source_ip},
        'observation': obs,
    }


def _make_controls(master: Path, target: Path):
    _, _, _, Image, ImageDraw, ImageFont, _ = _load_runtime()
    target.mkdir(parents=True, exist_ok=True)
    base = Image.open(master).convert('RGB')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 220)
    wm = base.copy(); d = ImageDraw.Draw(wm, 'RGBA'); text = 'STOCK WATERMARK'; bb = d.textbbox((0, 0), text, font=font); tw, th = bb[2]-bb[0], bb[3]-bb[1]
    d.text(((base.width-tw)//2, (base.height-th)//2), text, font=font, fill=(80,80,80,120)); wm.save(target/'watermark.png')
    logo = base.copy(); d = ImageDraw.Draw(logo); d.ellipse((1680,1700,2416,2436), fill=(190,25,35), outline=(20,20,20), width=30)
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 170); d.text((1745,1920), 'ACME', font=font2, fill='white'); logo.save(target/'logo_text.png')
    emblem = base.copy(); d = ImageDraw.Draw(emblem); w,h=emblem.size; cx,cy=w//2,h//2; r=max(120,min(w,h)//14)
    d.ellipse((cx-r,cy-r,cx+r,cy+r), fill=(20,20,20), outline=(245,245,245), width=max(8,r//16))
    d.polygon([(cx-int(r*.54),cy+int(r*.43)),(cx-int(r*.14),cy-int(r*.54)),(cx+int(r*.07),cy+int(r*.43))], fill=(245,245,245))
    d.polygon([(cx-int(r*.07),cy+int(r*.43)),(cx+int(r*.32),cy-int(r*.54)),(cx+int(r*.54),cy+int(r*.43))], fill=(180,180,180))
    emblem.save(target/'logo_emblem.png')
    knife = Image.new('RGB', base.size, 'white'); d = ImageDraw.Draw(knife); d.polygon([(650,2050),(2800,1450),(3300,1850),(1250,2350)], fill=(120,120,120), outline='black'); d.rounded_rectangle((900,2200,1800,2550), radius=80, fill=(60,35,20), outline='black', width=20); knife.save(target/'unsafe_knife.png')
    branded = Image.new('RGB', base.size, 'white'); d = ImageDraw.Draw(branded); d.rounded_rectangle((1500,700,2600,3400), radius=300, fill=(190,20,30), outline=(20,20,20), width=30); font3 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 190); d.text((1580,1800), 'FAMOUS', font=font3, fill='white'); d.text((1620,2080), 'BRAND', font=font3, fill='white'); branded.save(target/'branded_trade_dress.png')
    character = Image.new('RGB', base.size, 'white'); d = ImageDraw.Draw(character); d.ellipse((1450,1200,2650,2400), fill='black'); d.ellipse((1150,900,1650,1400), fill='black'); d.ellipse((2450,900,2950,1400), fill='black'); font4 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 160); d.text((1120,2750), 'FICTIONAL CHARACTER', font=font4, fill='black'); character.save(target/'fictional_character.png')
    return {'watermark': target/'watermark.png', 'logo_text': target/'logo_text.png', 'logo_emblem': target/'logo_emblem.png', 'unsafe_knife': target/'unsafe_knife.png', 'branded_trade_dress': target/'branded_trade_dress.png', 'fictional_character': target/'fictional_character.png'}


def _self_test(master: Path, cfg: dict[str, Any], *, model, preprocess, clip, torch, scratch: Path, stock_terms: list[str], asset_type: str = 'UNKNOWN') -> dict[str, Any]:
    controls = _make_controls(master, scratch/'controls')
    results = {name: _evaluate_image(path, cfg, model=model, preprocess=preprocess, clip=clip, torch=torch, scratch=scratch/f'control-{name}', stock_terms=stock_terms, asset_type=asset_type) for name, path in controls.items()}
    failures = []
    wm = results['watermark']
    if not wm['observation']['detectors']['watermark']['candidates']:
        failures.append('WATERMARK_CONTROL_NOT_DETECTED')
    lt = results['logo_text']
    if not lt['observation']['detectors']['logo']['candidates'] or not lt['observation']['detectors']['text']['detected_strings']:
        failures.append('TEXT_LOGO_CONTROL_NOT_DETECTED')
    le = results['logo_emblem']
    if not le['observation']['detectors']['logo']['candidates']:
        failures.append('GRAPHIC_LOGO_CONTROL_NOT_DETECTED')
    unsafe = results['unsafe_knife']
    flags = unsafe['observation']['detectors']['safety']['flags']
    if not flags or flags[0].get('disposition') != 'BLOCK':
        failures.append('UNSAFE_CONTROL_NOT_BLOCKED')
    branded = results['branded_trade_dress']['classification']['source_ip']
    if branded.get('disposition') != 'STRONG_RISK':
        failures.append('TRADE_DRESS_CONTROL_NOT_FLAGGED')
    character = results['fictional_character']['classification']['source_ip']
    if character.get('disposition') != 'STRONG_RISK':
        failures.append('FICTIONAL_CHARACTER_CONTROL_NOT_FLAGGED')
    return {'schema': 'die.factory-asset.visual-rights-detector-self-test.v1', 'result': 'PASS' if not failures else 'FAIL', 'failures': failures, 'controls': results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', type=Path, required=True)
    ap.add_argument('--expected-sha256', required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--self-test-output', type=Path)
    ap.add_argument('--scratch', type=Path, required=True)
    ap.add_argument('--asset-type', choices=['PHOTO','ISOLATED_OBJECT','ICON','OUTLINE','PATTERN','ANIMATION','UNKNOWN'], default='UNKNOWN')
    args = ap.parse_args()
    cfg = core.load_config()
    master = args.master.resolve()
    if not master.is_file() or core.sha256_file(master) != args.expected_sha256:
        raise RuntimeError('E_MASTER_HASH')
    checkpoint = Path(cfg['clip']['checkpoint_path'])
    if not checkpoint.is_file() or core.sha256_file(checkpoint) != cfg['clip']['checkpoint_sha256']:
        raise RuntimeError('E_CLIP_CHECKPOINT_HASH')
    ver = subprocess.check_output([cfg['runtime']['tesseract'], '--version'], text=True).splitlines()[0]
    if not ver.startswith(cfg['runtime']['tesseract_version_prefix']):
        raise RuntimeError(f'E_TESSERACT_VERSION:{ver}')
    clip, _, torch, _, _, _, _ = _load_runtime()
    if '+cpu' not in torch.__version__:
        raise RuntimeError(f'E_TORCH_NOT_CPU:{torch.__version__}')
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    model, preprocess = clip.load(str(checkpoint), device='cpu', jit=False)
    model.eval()
    rights_policy = json.loads((ROOT/'company/factory-asset/registries/rights-signal-policy.v1.json').read_text())
    self_test = _self_test(master, cfg, model=model, preprocess=preprocess, clip=clip, torch=torch, scratch=args.scratch/'self-test', stock_terms=rights_policy['stock_watermark_terms'], asset_type=args.asset_type)
    if self_test['result'] != 'PASS':
        raise RuntimeError('E_VISUAL_RIGHTS_SELF_TEST:'+','.join(self_test['failures']))
    actual = _evaluate_image(master, cfg, model=model, preprocess=preprocess, clip=clip, torch=torch, scratch=args.scratch/'actual', stock_terms=rights_policy['stock_watermark_terms'], asset_type=args.asset_type)
    actual['runtime'] = {
        'tesseract_version': ver,
        'clip_model': cfg['clip']['model'],
        'clip_checkpoint_sha256': cfg['clip']['checkpoint_sha256'],
        'torch_version': torch.__version__,
        'cpu_only': True,
        'self_test_result': self_test['result'],
        'asset_type': args.asset_type,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(actual, indent=2)+'\n')
    if args.self_test_output:
        args.self_test_output.parent.mkdir(parents=True, exist_ok=True)
        args.self_test_output.write_text(json.dumps(self_test, indent=2)+'\n')
    print(json.dumps({'result':'PASS','output':str(args.output),'self_test':self_test['result'],'observation':actual['observation'],'classification':actual['classification']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())