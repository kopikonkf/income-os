#!/usr/bin/env python3
from __future__ import annotations

import argparse, datetime as dt, hashlib, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
REGISTRY=ROOT/'INTELLIGENCE_PREREQUISITE_REGISTRY_V1.json'
SCHEMA=ROOT/'die.operator-v2.receipt-snapshot.v1.schema.json'
INSTANCE_MODULE=ROOT/'company_instance.py'

class ReceiptRegistryError(RuntimeError): pass

def _load_instance_module():
    import importlib.util
    spec=importlib.util.spec_from_file_location('operator_v2_company_instance',INSTANCE_MODULE)
    if spec is None or spec.loader is None: raise ReceiptRegistryError('E_INSTANCE_MODULE_LOAD')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

INSTANCE=_load_instance_module()

def parse_time(value:str)->dt.datetime:
    x=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if x.tzinfo is None: raise ReceiptRegistryError('E_TIME_TZ')
    return x.astimezone(dt.timezone.utc)

def sha(payload:Any)->str:
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def validate(snapshot:dict[str,Any])->dict[str,Any]:
    schema=json.loads(SCHEMA.read_text(encoding='utf-8')); registry=json.loads(REGISTRY.read_text(encoding='utf-8')); errors=[]; warnings=[]
    for e in sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(snapshot),key=lambda e:list(e.absolute_path)):
        errors.append('E_SCHEMA:'+e.message)
    if errors:
        return {'schema':'die.operator-v2.receipt-registry-validation.v1','status':'FAIL','errors':errors,'warnings':warnings,'active_receipts':{},'missing_receipt_types':[x['receipt_type'] for x in registry['stages']],'kanban_cognition_proof_used':False}
    instance_id=INSTANCE.resolve_instance_id(snapshot)
    now=parse_time(snapshot['as_of']); by_type={}; review_directives={}
    known={x['receipt_type']:x for x in registry['stages']}
    for receipt in snapshot['receipts']:
        rtype=receipt['receipt_type']; stage=known[rtype]
        if receipt['status']=='SUPERSEDED': continue
        if receipt['status']!='VALID':
            warnings.append('W_INVALID_RECEIPT:'+rtype+':'+receipt['artifact_id']); continue
        if receipt['issuer_kind']!=stage['issuer_kind']: errors.append('E_ISSUER_KIND:'+rtype)
        if receipt['issuer_id'] not in stage['allowed_issuer_ids']: errors.append('E_ISSUER_ID:'+rtype+':'+receipt['issuer_id'])
        role=stage.get('semantic_role')
        if role and receipt['issuer_id']!=INSTANCE.principal_for(instance_id,role): errors.append('E_CROSS_INSTANCE_ISSUER:'+rtype+':'+receipt['issuer_id'])
        if receipt['artifact_schema']!=stage['artifact_schema']: errors.append('E_ARTIFACT_SCHEMA:'+rtype)
        if receipt['validation']['status']!='PASS': errors.append('E_VALIDATION_PROOF:'+rtype)
        recorded=parse_time(receipt['recorded_at'])
        if recorded>now: errors.append('E_FRESHNESS:FROM_FUTURE:'+rtype)
        if stage.get('freshness_required'):
            if receipt['expires_at'] is None: errors.append('E_FRESHNESS:MISSING_EXPIRY:'+rtype)
            elif now>=parse_time(receipt['expires_at']): warnings.append('W_STALE_RECEIPT:'+rtype+':'+receipt['artifact_id']); continue
        fixed=stage.get('required_claims',{})
        review_outcome = receipt['claims'].get('outcome') if rtype in {'WORTH_MAKING_EXEC_REVIEW','BLUEPRINT_EXEC_REVIEW'} else None
        if review_outcome in {'REVISE','VETO_PENDING_EVIDENCE','ESCALATE_FOUNDER'}:
            review_directives[rtype] = {
                'outcome': review_outcome,
                'artifact_id': receipt['artifact_id'],
                'artifact_sha256': receipt['artifact_sha256'],
                'source_ref': receipt['source_ref'],
            }
        else:
            for key,value in fixed.items():
                if receipt['claims'].get(key)!=value: errors.append('E_REQUIRED_CLAIM:'+rtype+':'+key)
        for key in stage.get('required_claim_keys',[]):
            if key not in receipt['claims'] or receipt['claims'].get(key) in (None,''): errors.append('E_REQUIRED_CLAIM_KEY:'+rtype+':'+key)
        by_type.setdefault(rtype,[]).append(receipt)
    active={}
    for rtype,rows in by_type.items():
        identities={(r['artifact_id'],r['artifact_sha256']) for r in rows}
        if len(identities)>1:
            errors.append('E_CONFLICTING_ACTIVE_RECEIPTS:'+rtype)
        elif rows:
            active[rtype]=rows[0]
    # Cross-receipt exact compiled-hash authorization binding.
    lock=active.get('BLUEPRINT_COMPILE_HASH_LOCK'); auth=active.get('FOUNDER_PRODUCTION_AUTHORIZATION')
    if auth is not None and lock is None:
        errors.append('E_AUTH_WITHOUT_COMPILE_LOCK')
    if lock is not None and auth is not None:
        target=lock['claims'].get('exact_compiled_blueprint_sha256'); authorized=auth['claims'].get('authorized_compiled_blueprint_sha256')
        if not isinstance(target,str) or len(target)!=64: errors.append('E_COMPILE_LOCK_EXACT_HASH')
        if authorized!=target: errors.append('E_AUTH_COMPILED_HASH_MISMATCH')
    missing=[x['receipt_type'] for x in registry['stages'] if x['receipt_type'] not in active]
    return {'schema':'die.operator-v2.receipt-registry-validation.v1','status':'PASS' if not errors else 'FAIL','errors':sorted(set(errors)),'warnings':sorted(set(warnings)),'active_receipts':active,'missing_receipt_types':missing,'review_directives':review_directives,'snapshot_sha256':sha(snapshot),'kanban_cognition_proof_used':False}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('snapshot'); args=ap.parse_args(); d=json.loads(Path(args.snapshot).read_text(encoding='utf-8')); out=validate(d); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0 if out['status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())