#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve(); H01=HERE.parents[1]
sys.path.insert(0,str(H01/'lib')); sys.path.insert(0,str(H01/'engineering'))
from commercial_blueprint_v3 import build_blueprint_v3,sha256_value
from svg_prompt_composer_v2 import compile_master_instruction


def write_immutable(path:Path,value):
    body=json.dumps(value,indent=2,sort_keys=True)+'\n'; path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text()!=body: raise RuntimeError(f'E_IMMUTABLE_COLLISION:{path}')
    if not path.exists(): path.write_text(body)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--intent-manifest',required=True); ap.add_argument('--out-root',default='/var/lib/die/h01/blueprints/v3'); ns=ap.parse_args()
    mp=Path(ns.intent_manifest); manifest=json.loads(mp.read_text())
    if manifest.get('status')!='FROZEN' or manifest.get('schema')!='die.h01.phase0-production-intent-manifest.v1': raise SystemExit('E_INTENT_MANIFEST')
    root=Path(ns.out_root)/manifest['day_key']/manifest['cycle_id']; refs=[]
    for ref in sorted(manifest['intents'],key=lambda x:x['batch_position']):
        ip=Path(ref['path']); intent=json.loads(ip.read_text())
        if intent['intent_id']!=ref['intent_id'] or sha256_value(intent)!=ref['intent_sha256']: raise RuntimeError(f"E_INTENT_HASH:{ref['intent_id']}")
        bp=build_blueprint_v3(intent); master=compile_master_instruction(bp)
        bp_path=root/'blueprints'/f"{bp['blueprint_id']}.json"; mi_path=root/'masters'/f"{bp['blueprint_id']}.json"
        write_immutable(bp_path,bp); write_immutable(mi_path,master)
        refs.append({'batch_position':ref['batch_position'],'queue_item_id':ref['queue_item_id'],'canonical_name':ref['canonical_name'],'selection_reason':ref['selection_reason'],'intent_id':intent['intent_id'],'intent_sha256':sha256_value(intent),'blueprint_id':bp['blueprint_id'],'blueprint_sha256':sha256_value(bp),'master_instruction_sha256':master['master_instruction_sha256'],'blueprint_path':str(bp_path),'master_path':str(mi_path)})
    identity={'policy_version':'H01-102A-V1','intent_manifest_id':manifest['manifest_id'],'refs':[(x['blueprint_id'],x['blueprint_sha256'],x['master_instruction_sha256']) for x in refs]}
    out={'schema':'die.h01.commercial-blueprint-v3-manifest.v1','status':'FROZEN','policy_version':'H01-102A-V1','manifest_id':'H01-BP3MAN-'+hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24].upper(),'day_key':manifest['day_key'],'cycle_id':manifest['cycle_id'],'intent_manifest_id':manifest['manifest_id'],'selected_count':len(refs),'evidence_ranked_count':sum(1 for x in refs if x['selection_reason']=='EVIDENCE_RANKED'),'fallback_count':sum(1 for x in refs if x['selection_reason']=='SOURCE_ORDER_FALLBACK'),'blueprints':refs,'authority':{'provider_call_authorized':False,'production_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}
    write_immutable(root/'manifest.json',out)
    print(json.dumps({'status':'PASS','manifest_id':out['manifest_id'],'selected_count':out['selected_count'],'evidence_ranked_count':out['evidence_ranked_count'],'fallback_count':out['fallback_count'],'manifest_path':str(root/'manifest.json')},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
