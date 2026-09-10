from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'registries' / 'visual-rights-detector.v1.json'


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def normalize_token(value: str) -> str:
    return ' '.join(str(value).strip().split())


def ocr_consensus(rows: list[dict[str, Any]], *, min_confidence: float, min_token_chars: int, min_consensus_passes: int) -> dict[str, Any]:
    hits: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        text = normalize_token(row.get('text', ''))
        conf = float(row.get('confidence', -1))
        if conf < min_confidence:
            continue
        folded = re.sub(r'[^a-z0-9]+', '', text.casefold())
        if len(folded) < min_token_chars:
            continue
        key = folded
        hits.setdefault(key, []).append({'text': text, 'confidence': conf, 'pass_id': str(row.get('pass_id', ''))})
    consensus = []
    for key, vals in sorted(hits.items()):
        passes = sorted({x['pass_id'] for x in vals})
        if len(passes) < min_consensus_passes:
            continue
        best = max(vals, key=lambda x: x['confidence'])
        consensus.append({
            'normalized': key,
            'text': best['text'],
            'max_confidence': round(float(best['confidence']), 6),
            'pass_count': len(passes),
            'passes': passes,
        })
    return {'consensus': consensus, 'raw_qualified_hit_count': sum(len(v) for v in hits.values())}


def score_sum(scores: list[float], indices: list[int]) -> float:
    return float(sum(scores[i] for i in indices))


def classify_logo(*, full_scores: list[float], foreground_scores: list[float], cfg: dict[str, Any]) -> dict[str, Any]:
    indices = list(cfg['positive_indices'])
    full = score_sum(full_scores, indices)
    fg = score_sum(foreground_scores, indices)
    positive = max(full, fg)
    review = float(cfg['review_positive_score'])
    strong = float(cfg['strong_candidate_score'])
    if positive >= strong:
        disposition = 'STRONG_CANDIDATE'
    elif positive > review:
        disposition = 'REVIEW_CANDIDATE'
    else:
        disposition = 'CLEAR'
    return {'positive_score': round(positive, 6), 'full_positive_score': round(full, 6), 'foreground_positive_score': round(fg, 6), 'disposition': disposition}


def classify_watermark(*, full_scores: list[float], cfg: dict[str, Any]) -> dict[str, Any]:
    indices = list(cfg['positive_indices'])
    clean_index = int(cfg.get('clean_index', 0))
    clean_score = float(full_scores[clean_index])
    max_risk_score = max(float(full_scores[i]) for i in indices)
    positive = max(0.0, max_risk_score - clean_score)
    review = float(cfg['review_positive_score'])
    strong = float(cfg['strong_candidate_score'])
    if positive >= strong:
        disposition = 'STRONG_CANDIDATE'
    elif positive > review:
        disposition = 'REVIEW_CANDIDATE'
    else:
        disposition = 'CLEAR'
    return {'positive_score': round(positive, 6), 'clean_score': round(clean_score, 6), 'max_risk_score': round(max_risk_score, 6), 'scoring': 'MAX_RISK_MINUS_CLEAN', 'disposition': disposition}


def classify_safety(*, full_scores: list[float], foreground_scores: list[float], cfg: dict[str, Any]) -> dict[str, Any]:
    indices = list(cfg['unsafe_indices'])
    full = score_sum(full_scores, indices)
    fg = score_sum(foreground_scores, indices)
    unsafe = max(full, fg)
    if unsafe >= float(cfg['block_unsafe_score']):
        disposition = 'BLOCK'
    elif unsafe > float(cfg['review_unsafe_score']):
        disposition = 'REVIEW'
    else:
        disposition = 'CLEAR'
    return {'unsafe_score': round(unsafe, 6), 'full_unsafe_score': round(full, 6), 'foreground_unsafe_score': round(fg, 6), 'disposition': disposition}



def classify_source_ip(*, full_scores: list[float], foreground_scores: list[float], cfg: dict[str, Any], asset_type: str = 'UNKNOWN') -> dict[str, Any]:
    applicability = cfg.get('applicable_risk_indices_by_asset_type') or {}
    indices = list(applicability.get(asset_type, applicability.get('UNKNOWN', cfg['risk_indices'])))
    if not indices:
        raise ValueError(f'E_SOURCE_IP_NO_APPLICABLE_RISK_CLASSES:{asset_type}')
    clean_index = int(cfg.get('clean_index', 0))
    def margin(scores: list[float]) -> tuple[float, float, float]:
        clean = float(scores[clean_index])
        max_risk = max(float(scores[i]) for i in indices)
        return max(0.0, max_risk-clean), clean, max_risk
    full, full_clean, full_max = margin(full_scores)
    fg, fg_clean, fg_max = margin(foreground_scores)
    risk = max(full, fg)
    if risk >= float(cfg['strong_risk_score']):
        disposition = 'STRONG_RISK'
    elif risk > float(cfg['review_risk_score']):
        disposition = 'REVIEW'
    else:
        disposition = 'CLEAR'
    return {'risk_score': round(risk, 6), 'full_risk_score': round(full, 6), 'foreground_risk_score': round(fg, 6), 'full_clean_score': round(full_clean, 6), 'foreground_clean_score': round(fg_clean, 6), 'full_max_risk_score': round(full_max, 6), 'foreground_max_risk_score': round(fg_max, 6), 'applicable_risk_indices': indices, 'asset_type': asset_type, 'scoring': 'MAX_APPLICABLE_RISK_MINUS_CLEAN', 'disposition': disposition}

def build_rights_observation(*, master_sha256: str, ocr: dict[str, Any], logo: dict[str, Any], watermark: dict[str, Any], safety: dict[str, Any], stock_watermark_terms: list[str]) -> dict[str, Any]:
    detected = [x['text'] for x in ocr.get('consensus', [])]
    folded = [' '.join(x.casefold().split()) for x in detected]
    stock_terms = [x.casefold() for x in stock_watermark_terms]
    watermark_text = [txt for txt, f in zip(detected, folded) if ('watermark' in f or any(term in f for term in stock_terms))]
    unresolved = [x for x in detected if x not in watermark_text]

    logo_candidates = []
    if logo['disposition'] != 'CLEAR':
        logo_candidates.append({'label': 'CLIP_VISUAL_LOGO_OR_BRAND_MARK', 'confirmed_brand': False, 'score': logo['positive_score']})

    watermark_candidates = []
    if watermark_text:
        watermark_candidates.append({'label': 'OCR_WATERMARK_TEXT', 'confirmed': True, 'strings': watermark_text})
    elif watermark['disposition'] != 'CLEAR':
        watermark_candidates.append({'label': 'CLIP_WATERMARK_OR_OVERLAY', 'confirmed': False, 'score': watermark['positive_score']})

    safety_flags = []
    if safety['disposition'] == 'BLOCK':
        safety_flags.append({'code': 'CLIP_UNSAFE_CONTENT_STRONG', 'disposition': 'BLOCK', 'score': safety['unsafe_score']})
    elif safety['disposition'] == 'REVIEW':
        safety_flags.append({'code': 'CLIP_UNSAFE_CONTENT_UNCERTAIN', 'disposition': 'REVIEW', 'score': safety['unsafe_score']})

    return {
        'schema': 'die.factory-asset.rights-observation.v1',
        'master_sha256': master_sha256,
        'detectors': {
            'text': {
                'state': 'COMPLETE',
                'detected_strings': detected,
                'confirmed_trademark_terms': [],
                'trademark_candidates': [],
                'unresolved_strings': unresolved,
            },
            'logo': {'state': 'COMPLETE', 'candidates': logo_candidates},
            'watermark': {'state': 'COMPLETE', 'candidates': watermark_candidates},
            'safety': {'state': 'COMPLETE', 'flags': safety_flags},
        },
    }