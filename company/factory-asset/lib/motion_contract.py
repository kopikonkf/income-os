from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import jsonschema

ROOT=Path(__file__).resolve().parents[3]
MOTION_SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/motion-composition.schema.json').read_text(encoding='utf-8'))
NATIVE_SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/native-producer.schema.json').read_text(encoding='utf-8'))

class MotionContractError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def canonical_bytes(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def sha256_value(value:Any)->str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def validate_motion_composition(comp:dict[str,Any])->dict[str,Any]:
    try:jsonschema.Draft202012Validator(MOTION_SCHEMA).validate(comp)
    except jsonschema.ValidationError as exc:raise MotionContractError('MOTION_SCHEMA_INVALID',exc.message) from exc
    expected=Decimal(str(comp['duration_seconds']))*Decimal(comp['fps'])
    if expected != expected.to_integral_value():
        raise MotionContractError('NON_INTEGRAL_FRAME_COUNT',str(expected))
    if int(expected)!=comp['frame_count']:
        raise MotionContractError('FRAME_COUNT_MISMATCH',f"expected {int(expected)} got {comp['frame_count']}")
    container=comp['video']['container'];codec=comp['video']['codec'];pix=comp['video']['pixel_format']
    valid={('MP4','H264','YUV420P'),('MP4','H265','YUV420P'),('MOV','H264','YUV420P'),('MOV','PRORES_422','YUV422P10LE')}
    if (container,codec,pix) not in valid:
        raise MotionContractError('VIDEO_TARGET_UNSUPPORTED',f'{container}/{codec}/{pix}')
    layer_ids=[]; temporal_change=False
    for layer in comp['layers']:
        if layer['layer_id'] in layer_ids:raise MotionContractError('DUPLICATE_LAYER_ID',layer['layer_id'])
        layer_ids.append(layer['layer_id'])
        if layer['start_frame']>layer['end_frame']:raise MotionContractError('LAYER_RANGE_INVALID',layer['layer_id'])
        if layer['end_frame']>=comp['frame_count']:raise MotionContractError('LAYER_OUT_OF_FRAME_RANGE',layer['layer_id'])
        by_property:dict[str,list[tuple[int,Any]]]={}
        for k in layer['keyframes']:
            if k['frame']<layer['start_frame'] or k['frame']>layer['end_frame']:
                raise MotionContractError('KEYFRAME_OUT_OF_LAYER_RANGE',f"{layer['layer_id']}:{k['frame']}")
            by_property.setdefault(k['property'],[]).append((k['frame'],k['value']))
        for values in by_property.values():
            frames={x[0] for x in values}; rendered={json.dumps(x[1],sort_keys=True) for x in values}
            if len(frames)>=2 and len(rendered)>=2:temporal_change=True
    if not temporal_change:
        raise MotionContractError('NO_TEMPORAL_CHANGE','animation requires at least one changing property across frames')
    return {'schema':'die.factory-asset.motion-composition-validation.v1','result':'PASS','composition_sha256':sha256_value(comp),'frame_count':comp['frame_count'],'duration_seconds':comp['duration_seconds'],'fps':comp['fps'],'dimensions':[comp['canvas']['width'],comp['canvas']['height']],'renderer':dict(comp['renderer']),'video':dict(comp['video']),'audio_policy':comp['audio']['policy'],'semantic_mode':'ANIMATION','native_representation':'TIMED_FRAMES','conversion_from_raster':False,'temporal_change':True}

def build_renderer_request(comp:dict[str,Any],*,job_id:str,cancellation_token:str)->dict[str,Any]:
    validation=validate_motion_composition(comp)
    if len(job_id)<8 or len(cancellation_token)<8:raise MotionContractError('RENDERER_REQUEST_ID_INVALID','job/cancellation token')
    params={'motion_contract_schema':comp['schema'],'composition_sha256':validation['composition_sha256'],'composition':comp,'expected_frame_count':comp['frame_count'],'expected_duration_seconds':comp['duration_seconds'],'expected_dimensions':[comp['canvas']['width'],comp['canvas']['height']],'fps':comp['fps'],'renderer':dict(comp['renderer']),'video_target':dict(comp['video']),'audio_policy':comp['audio']['policy'],'semantic_mode':'ANIMATION','native_representation':'TIMED_FRAMES','conversion_from_raster':False}
    idem=hashlib.sha256(canonical_bytes({'composition_sha256':validation['composition_sha256'],'renderer':comp['renderer'],'video':comp['video'],'audio':comp['audio']})).hexdigest()
    request={'schema':'die.factory-asset.native-producer.v1','kind':'REQUEST','job_id':job_id,'idempotency_key':idem,'blueprint_id':comp['blueprint_id'],'semantic_asset_id':comp['semantic_asset_id'],'producer_class':'MOTION_RENDERER','producer_version':comp['renderer']['renderer_version'],'parameters':params,'cancellation':{'token':cancellation_token,'poll_or_signal_supported':True}}
    jsonschema.Draft202012Validator(NATIVE_SCHEMA).validate(request)
    return request