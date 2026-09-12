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
REQUEST_SCHEMA = H01 / 'contracts/h01-native-svg-request-v1.schema.json'
RECEIPT_SCHEMA = H01 / 'contracts/h01-native-svg-receipt-v1.schema.json'
CONTRACT_REVISION = '1.0.0'

class NativeSvgContractError(ValueError):
    def __init__(self, code: str, detail: str = ''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))

def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def sha256_value(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def _validate_schema(value: Any, path: Path, code: str) -> None:
    errors=sorted(jsonschema.Draft202012Validator(_load(path)).iter_errors(value), key=lambda e:list(e.absolute_path))
    if errors:
        e=errors[0]; where='.'.join(str(x) for x in e.absolute_path) or '$'
        raise NativeSvgContractError(code,f'{where}: {e.message}')

def _assert_sha(name: str, value: str) -> None:
    if not re.fullmatch(r'[0-9a-f]{64}', str(value)):
        raise NativeSvgContractError('HASH_INVALID',name)

def normalize_svg_payload(payload: str) -> str:
    text=str(payload).strip()
    fence=re.fullmatch(r'```(?:svg|xml)?\s*(.*?)\s*```',text,flags=re.I|re.S)
    if fence: text=fence.group(1).strip()
    start=text.find('<svg'); end=text.rfind('</svg>')
    if start<0 or end<0: raise NativeSvgContractError('OUTPUT_NOT_SVG','missing svg root')
    if text[:start].strip() or text[end+len('</svg>'):].strip():
        raise NativeSvgContractError('PROVIDER_RESPONSE_INVALID','non-SVG prose outside root')
    return text[start:end+len('</svg>')]

def _request_idempotency_material(req: dict[str, Any]) -> dict[str, Any]:
    return {
        'schema':'die.h01.native-svg-idempotency-material.v1',
        'queue_item_id':req['queue_item_id'],
        'source_candidate_id':req['source_candidate_id'],
        'semantic_asset_id':req['semantic_asset_id'],
        'provider_id':req['provider_target']['provider_id'],
        'provider_profile':req['provider_target']['provider_profile'],
        'blueprint_sha256':req['blueprint']['sha256'],
        'master_instruction_sha256':req['master_instruction_sha256'],
        'prompt_sha256':req['prompt']['sha256'],
        'output_contract':req['output_contract'],
    }

def validate_request(req: dict[str, Any]) -> None:
    _validate_schema(req,REQUEST_SCHEMA,'REQUEST_SCHEMA_INVALID')
    if req['prompt']['chars'] != len(req['prompt']['text']):
        raise NativeSvgContractError('PROMPT_CHAR_COUNT_MISMATCH',req['request_id'])
    if req['prompt']['sha256'] != sha256_text(req['prompt']['text']):
        raise NativeSvgContractError('PROMPT_HASH_MISMATCH',req['request_id'])
    expected=sha256_value(_request_idempotency_material(req))
    if req['idempotency_key'] != expected:
        raise NativeSvgContractError('IDEMPOTENCY_KEY_MISMATCH',req['request_id'])

def build_request(*, request_id: str, queue_item_id: str, source_candidate_id: str, semantic_asset_id: str, provider_id: str, provider_profile: str, blueprint_id: str, blueprint_sha256: str, master_instruction_sha256: str, provider_prompt: str, provider_prompt_sha256: str | None = None) -> dict[str, Any]:
    provider_prompt=provider_prompt.strip()
    if not provider_prompt: raise NativeSvgContractError('PROMPT_EMPTY',request_id)
    actual_prompt_sha=sha256_text(provider_prompt)
    if provider_prompt_sha256 is not None and provider_prompt_sha256 != actual_prompt_sha:
        raise NativeSvgContractError('PROMPT_HASH_MISMATCH',request_id)
    _assert_sha('blueprint_sha256',blueprint_sha256); _assert_sha('master_instruction_sha256',master_instruction_sha256)
    req={
        'schema':'die.h01.native-svg-request.v1','contract_revision':CONTRACT_REVISION,'request_id':request_id,'idempotency_key':'0'*64,
        'queue_item_id':queue_item_id,'source_candidate_id':source_candidate_id,'semantic_asset_id':semantic_asset_id,
        'provider_target':{'provider_id':provider_id,'provider_profile':provider_profile},
        'ingress_policy':{'preferred':'WEB_AI_ADAPTER','allowed':['WEB_AI_ADAPTER','NATIVE_MCP'],'native_mcp_required':False},
        'blueprint':{'blueprint_id':blueprint_id,'sha256':blueprint_sha256},'master_instruction_sha256':master_instruction_sha256,
        'prompt':{'text':provider_prompt,'sha256':actual_prompt_sha,'chars':len(provider_prompt)},
        'output_contract':{'payload_kind':'SVG_SOURCE_TEXT','master_format':'SVG','native_editable_required':True,'conversion_from_raster_allowed':False,'embedded_raster_allowed':False,'h01_103_validation_required':True},
        'authority':{'dispatch_semantics':'EXACTLY_ONCE','dispatch_commit_required':True,'submission_authorized':False,'publication_authorized':False},
    }
    req['idempotency_key']=sha256_value(_request_idempotency_material(req)); validate_request(req); return req

def _lineage(req: dict[str, Any]) -> dict[str, str]:
    return {'blueprint_sha256':req['blueprint']['sha256'],'master_instruction_sha256':req['master_instruction_sha256'],'prompt_sha256':req['prompt']['sha256']}

def validate_receipt(receipt: dict[str, Any], *, request: dict[str, Any] | None = None) -> None:
    _validate_schema(receipt,RECEIPT_SCHEMA,'RECEIPT_SCHEMA_INVALID')
    if request is not None:
        validate_request(request)
        pairs=[('request_id','request_id'),('idempotency_key','idempotency_key'),('queue_item_id','queue_item_id'),('semantic_asset_id','semantic_asset_id')]
        for rk,qk in pairs:
            if receipt[rk] != request[qk]: raise NativeSvgContractError('RECEIPT_REQUEST_MISMATCH',rk)
        if receipt['provider_id'] != request['provider_target']['provider_id']:
            raise NativeSvgContractError('RECEIPT_REQUEST_MISMATCH','provider_id')
        if receipt['ingress'] not in request['ingress_policy']['allowed']:
            raise NativeSvgContractError('INGRESS_NOT_ALLOWED',receipt['ingress'])
        if receipt['lineage'] != _lineage(request):
            raise NativeSvgContractError('RECEIPT_LINEAGE_MISMATCH',receipt['request_id'])
    claim=receipt['native_svg_claim']; validation=receipt['validation']; result=receipt['provider_result']
    if receipt['status']=='SUCCEEDED':
        if result['payload_kind']!='SVG_SOURCE_TEXT' or result['candidate_svg_sha256'] is None or result['provider_response_sha256'] is None:
            raise NativeSvgContractError('SUCCESS_PROVIDER_RESULT_INCOMPLETE',receipt['request_id'])
        if claim != {'source_kind':'DIRECT_PROVIDER_SVG_SOURCE','native_editable':True,'conversion_from_raster':False,'embedded_raster':False,'success_claim_allowed':True}:
            raise NativeSvgContractError('RASTER_TRACE_SUCCESS_FORBIDDEN',receipt['request_id'])
        if validation['engine']!='H01-103' or validation['status']!='PASS' or validation['canonical_svg_sha256'] is None:
            raise NativeSvgContractError('H01_103_PASS_REQUIRED',receipt['request_id'])
        if result['error_code'] is not None or result['error_detail'] is not None:
            raise NativeSvgContractError('SUCCESS_ERROR_FIELDS_FORBIDDEN',receipt['request_id'])
    else:
        if claim['success_claim_allowed']:
            raise NativeSvgContractError('NON_SUCCESS_CLAIM_FORBIDDEN',receipt['request_id'])
        if validation['status']=='PASS':
            raise NativeSvgContractError('NON_SUCCESS_VALIDATION_PASS_FORBIDDEN',receipt['request_id'])

def build_success_receipt(*, request: dict[str, Any], ingress: str, dispatch_commit_id: str, provider_status: str, provider_response_text: str, h01_103_canonical_svg_sha256: str, provider_request_id: str | None = None, finish_reason: str | None = None, candidate_svg_text: str | None = None) -> dict[str, Any]:
    validate_request(request)
    if ingress not in request['ingress_policy']['allowed']: raise NativeSvgContractError('INGRESS_NOT_ALLOWED',ingress)
    _assert_sha('h01_103_canonical_svg_sha256',h01_103_canonical_svg_sha256)
    candidate=normalize_svg_payload(candidate_svg_text if candidate_svg_text is not None else provider_response_text)
    if candidate_svg_text is not None and candidate not in provider_response_text:
        raise NativeSvgContractError('CANDIDATE_NOT_IN_PROVIDER_RESPONSE',request['request_id'])
    receipt={
        'schema':'die.h01.native-svg-receipt.v1','contract_revision':CONTRACT_REVISION,
        'request_id':request['request_id'],'idempotency_key':request['idempotency_key'],'queue_item_id':request['queue_item_id'],'semantic_asset_id':request['semantic_asset_id'],'provider_id':request['provider_target']['provider_id'],'ingress':ingress,'status':'SUCCEEDED',
        'lineage':_lineage(request),
        'provider_result':{'provider_status':provider_status,'provider_request_id':provider_request_id,'finish_reason':finish_reason,'error_code':None,'error_detail':None,'provider_response_sha256':sha256_text(provider_response_text),'payload_kind':'SVG_SOURCE_TEXT','candidate_svg_sha256':sha256_text(candidate)},
        'native_svg_claim':{'source_kind':'DIRECT_PROVIDER_SVG_SOURCE','native_editable':True,'conversion_from_raster':False,'embedded_raster':False,'success_claim_allowed':True},
        'validation':{'engine':'H01-103','status':'PASS','canonical_svg_sha256':h01_103_canonical_svg_sha256},
        'authority':{'dispatch_semantics':'EXACTLY_ONCE','dispatch_commit_id':dispatch_commit_id,'submission_authorized':False,'publication_authorized':False},
    }
    validate_receipt(receipt,request=request); return receipt

def build_failure_receipt(*, request: dict[str, Any], ingress: str, dispatch_commit_id: str, status: str, provider_status: str, error_code: str | None, error_detail: str | None, provider_request_id: str | None = None, finish_reason: str | None = None, provider_response_text: str | None = None) -> dict[str, Any]:
    validate_request(request)
    if status not in {'FAILED','BLOCKED','TIMEOUT','CANCELLED'}: raise NativeSvgContractError('FAILURE_STATUS_INVALID',status)
    if ingress not in request['ingress_policy']['allowed']: raise NativeSvgContractError('INGRESS_NOT_ALLOWED',ingress)
    receipt={
        'schema':'die.h01.native-svg-receipt.v1','contract_revision':CONTRACT_REVISION,
        'request_id':request['request_id'],'idempotency_key':request['idempotency_key'],'queue_item_id':request['queue_item_id'],'semantic_asset_id':request['semantic_asset_id'],'provider_id':request['provider_target']['provider_id'],'ingress':ingress,'status':status,
        'lineage':_lineage(request),
        'provider_result':{'provider_status':provider_status,'provider_request_id':provider_request_id,'finish_reason':finish_reason,'error_code':error_code,'error_detail':error_detail,'provider_response_sha256':sha256_text(provider_response_text) if provider_response_text is not None else None,'payload_kind':None,'candidate_svg_sha256':None},
        'native_svg_claim':{'source_kind':'NONE','native_editable':False,'conversion_from_raster':False,'embedded_raster':False,'success_claim_allowed':False},
        'validation':{'engine':'H01-103','status':'NOT_RUN','canonical_svg_sha256':None},
        'authority':{'dispatch_semantics':'EXACTLY_ONCE','dispatch_commit_id':dispatch_commit_id,'submission_authorized':False,'publication_authorized':False},
    }
    validate_receipt(receipt,request=request); return receipt

def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    fd,tmp=tempfile.mkstemp(prefix=f'.{path.name}.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as h:
            h.write(data); h.flush(); os.fsync(h.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

class ExactlyOnceLedger:
    """Durable local dispatch guard. It never selects work, providers, retries or routes."""
    def __init__(self, root: str | Path): self.root=Path(root)
    def _path(self, request: dict[str, Any]) -> Path: return self.root/f"{request['idempotency_key']}.json"
    def read(self, request: dict[str, Any]) -> dict[str, Any] | None:
        path=self._path(request); return json.loads(path.read_text()) if path.exists() else None
    def reserve(self, request: dict[str, Any]) -> tuple[str,dict[str,Any]]:
        validate_request(request); path=self._path(request)
        request_sha=sha256_value({k:v for k,v in request.items() if k not in {'request_id','idempotency_key'}})
        if path.exists():
            row=json.loads(path.read_text())
            if row.get('request_sha256')!=request_sha: raise NativeSvgContractError('IDEMPOTENCY_CONFLICT',request['idempotency_key'])
            return 'UNCHANGED',row
        row={'schema':'die.h01.native-svg-dispatch-journal.v1','idempotency_key':request['idempotency_key'],'request_id':request['request_id'],'request_sha256':request_sha,'state':'RESERVED','dispatch':None,'terminal_receipt_sha256':None}
        _atomic_json(path,row); return 'CREATED',row
    def commit_dispatch(self, request: dict[str, Any], *, ingress: str, dispatch_commit_id: str) -> tuple[str,dict[str,Any]]:
        validate_request(request)
        if ingress not in request['ingress_policy']['allowed']: raise NativeSvgContractError('INGRESS_NOT_ALLOWED',ingress)
        status,row=self.reserve(request); path=self._path(request)
        wanted={'ingress':ingress,'dispatch_commit_id':dispatch_commit_id}
        if row['state']=='RESERVED':
            row['state']='DISPATCH_COMMITTED'; row['dispatch']=wanted; _atomic_json(path,row); return 'COMMITTED',row
        if row['state'] in {'DISPATCH_COMMITTED','TERMINAL'}:
            if row.get('dispatch')==wanted: return 'UNCHANGED',row
            raise NativeSvgContractError('E_ALREADY_DISPATCHED',request['idempotency_key'])
        raise NativeSvgContractError('JOURNAL_STATE_INVALID',str(row.get('state')))
    def commit_terminal(self, request: dict[str, Any], receipt: dict[str, Any]) -> tuple[str,dict[str,Any]]:
        validate_request(request); validate_receipt(receipt,request=request); path=self._path(request)
        if not path.exists(): raise NativeSvgContractError('DISPATCH_COMMIT_REQUIRED',request['idempotency_key'])
        row=json.loads(path.read_text())
        if row.get('state') not in {'DISPATCH_COMMITTED','TERMINAL'}: raise NativeSvgContractError('DISPATCH_COMMIT_REQUIRED',request['idempotency_key'])
        expected_dispatch=row.get('dispatch') or {}
        if receipt['ingress']!=expected_dispatch.get('ingress') or receipt['authority']['dispatch_commit_id']!=expected_dispatch.get('dispatch_commit_id'):
            raise NativeSvgContractError('RECEIPT_DISPATCH_MISMATCH',request['idempotency_key'])
        digest=sha256_value(receipt)
        if row['state']=='TERMINAL':
            if row.get('terminal_receipt_sha256')==digest: return 'UNCHANGED',row
            raise NativeSvgContractError('TERMINAL_RECEIPT_CONFLICT',request['idempotency_key'])
        row['state']='TERMINAL'; row['terminal_receipt_sha256']=digest; _atomic_json(path,row); return 'COMMITTED',row
