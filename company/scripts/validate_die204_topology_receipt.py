#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, re
from pathlib import Path
from typing import Any

SHA=re.compile(r'^[0-9a-f]{64}$')


def validate(receipt:dict[str,Any])->list[str]:
    e=[]
    if receipt.get('schema')!='die.muxia.die204-linux-company-topology.v1': e.append('E_SCHEMA')
    if receipt.get('task_id')!='DIE-204': e.append('E_TASK')
    if receipt.get('status')!='PASS': e.append('E_STATUS')
    deps=receipt.get('dependencies',{})
    for k in ['DIE-200','DIE-201','DIE-202','DIE-203','MX-052']:
        if deps.get(k)!='DONE': e.append('E_DEP:'+k)
    atlas=receipt.get('atlas',{})
    human=atlas.get('human',{}); obj=atlas.get('object',{})
    if not SHA.fullmatch(str(human.get('sha256',''))): e.append('E_HUMAN_SHA')
    if obj.get('objects')!=475560: e.append('E_OBJECT_COUNT')
    if obj.get('classification')!='FINAL_PRODUCTION_BASELINE': e.append('E_OBJECT_CLASS')
    if not SHA.fullmatch(str(obj.get('sha256',''))): e.append('E_OBJECT_SHA')
    principals=receipt.get('principals',{})
    if principals.get('executive',{}).get('principal_id')!='chatgpt-plus-executive': e.append('E_EXEC_PRINCIPAL')
    if principals.get('executive',{}).get('tools')!=18: e.append('E_EXEC_TOOLS')
    div=principals.get('division01',{})
    if div.get('principal_id')!='division-head-division01': e.append('E_DIV_PRINCIPAL')
    if div.get('tools')!=6 or div.get('health')!='PASS': e.append('E_DIV_HEALTH')
    if div.get('semantic_invocation_performed') is not False: e.append('E_DIV_SEMANTIC_INVOCATION')
    hermes=principals.get('hermes',{})
    if hermes.get('principal_id')!='hermes-operator' or hermes.get('gateway_active') is not True or hermes.get('telegram_e2e')!='PASS': e.append('E_HERMES')
    worker=principals.get('worker',{})
    if worker.get('executor')!='opencode' or worker.get('version')!='1.18.23' or worker.get('result_status')!='done': e.append('E_WORKER')
    handoff=receipt.get('handoff',{})
    if handoff.get('network')!='none': e.append('E_NETWORK')
    if handoff.get('provider_call_performed') is not False: e.append('E_PROVIDER_CALL')
    if handoff.get('consumer_chatgpt_used') is not False: e.append('E_CONSUMER_CHATGPT')
    if handoff.get('final_status')!='SUCCEEDED': e.append('E_MUXIA_STATUS')
    ar=receipt.get('artifact_registry',{})
    if ar.get('status')!='VERIFIED' or not SHA.fullmatch(str(ar.get('sha256',''))): e.append('E_ARTIFACT_RECEIPT')
    ev=ar.get('completion_evidence',{})
    for k in ['artifactExists','receiptExists','hashMatches','bytesMatch','mimeMatches']:
        if ev.get(k) is not True: e.append('E_COMPLETION:'+k)
    topo=receipt.get('company_topology',{})
    required={'company/architect','company/executive','company/atlas','company/muxia','company/division','company/die-agents','company/workers','company/next-subprojects'}
    if set(topo.get('required_logical_roots',[]))!=required: e.append('E_LOGICAL_ROOTS')
    if topo.get('architect_status')!='DEFERRED_SOURCE_IMPORT' or topo.get('architect_windows_control_preserved') is not True: e.append('E_ARCHITECT_BOUNDARY')
    if topo.get('division002_to_100_materialization')!='ON_DEMAND_NO_EMPTY_SOURCE_TREES': e.append('E_DIVISION_MATERIALIZATION')
    ab=receipt.get('aether_boundary',{})
    if ab.get('active_lineage_text_hits')!=0 or ab.get('protected_symlink_hits')!=0 or ab.get('absorbed') is not False: e.append('E_AETHER_ABSORPTION')
    auth=receipt.get('authority',{})
    if auth.get('production_authority_granted') is not False or auth.get('submission_performed') is not False or auth.get('publication_performed') is not False or auth.get('spend_usd')!=0: e.append('E_AUTHORITY')
    acc=receipt.get('acceptance',{})
    for k in ['principal_lineage','data_lineage','worker_boundary','muxia_artifact_lineage','no_aether_dependency_absorption','linux_company_topology']:
        if acc.get(k)!='PASS': e.append('E_ACCEPTANCE:'+k)
    return e


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('receipt'); args=ap.parse_args()
    d=json.loads(Path(args.receipt).read_text(encoding='utf-8')); errors=validate(d)
    print(json.dumps({'schema':'die.die204-topology-validation.v1','status':'PASS' if not errors else 'FAIL','errors':errors},indent=2))
    return 0 if not errors else 2

if __name__=='__main__': raise SystemExit(main())