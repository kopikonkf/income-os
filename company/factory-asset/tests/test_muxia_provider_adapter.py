import copy
import hashlib
import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path

import jsonschema

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company/factory-asset/lib/muxia_provider_adapter.py'
s=importlib.util.spec_from_file_location('fa113_muxia_adapter',P)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;assert s and s.loader;s.loader.exec_module(m)
SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/image-provider.schema.json').read_text())


def png_bytes(w=17,h=11):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+bytes([12,34,56,255])*w for _ in range(h))
    hdr=struct.pack('>IIBBBBB',w,h,8,6,0,0,0)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',hdr)+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def fixture(tmp_path,w=17,h=11):
    workspace=tmp_path/'PRODTEST113';provider=workspace/'provider';provider.mkdir(parents=True)
    source=provider/'source-original.png';data=png_bytes(w,h);source.write_bytes(data)
    digest=hashlib.sha256(data).hexdigest()
    receipt=provider/'muxia-receipt.json';receipt.write_text('{}\n')
    q={
      'schema':'die.muxia-dispatch-result.v1','task_id':'PRODTEST113','status':'SUCCEEDED','request_sha256':'a'*64,
      'dispatch':{
        'schema':'die.muxia.chatgpt-image-run.v1','job_id':'PRODTEST113-muxia','profile_id':'chatgpt-linux-a','prompt_sha256':'b'*64,
        'prompt_submitted_by_automation':True,'output_extracted_by_automation':True,'credential_values_read':False,'cookies_or_tokens_read':False,
        'submission_authorized':False,'publication_authorized':False,'status':'SUCCEEDED','generated_image_observed':{'width':w,'height':h,'src_scheme':'https'},
        'output_method':'context-request-original-src','content_type':'image/png','artifact_path':'/var/lib/muxia/artifacts/PRIVATE-MUST-NOT-BE-READ.png',
        'bytes':len(data),'sha256':digest,'export_artifact_path':str(source),'export_artifact_sha256':digest,'export_receipt_path':str(receipt),
        'private_artifact_access_by_hermes':False,
      }
    }
    return workspace,q,digest


def adapt(tmp_path,q=None,workspace=None):
    if q is None or workspace is None: workspace,q,_=fixture(tmp_path)
    return m.adapt_muxia_success(queue_result=q,workspace_root=workspace,staging_root=tmp_path/'staging',attempt_id='FA113-ATTEMPT-01',semantic_asset_id='FASA-MUXIA_TEST',blueprint_id='FABP-MUXIA_TEST')


def test_capability_conforms_and_capacity_remains_unknown():
    cap=m.capability();jsonschema.validate(cap,SCHEMA)
    assert cap['provider_id']=='chatgpt' and cap['transport_classes']==['BROWSER_CDP']
    assert cap['capacity_state']=='UNKNOWN' and cap['output_formats']==['PNG']


def test_success_adapts_export_to_factory_provider_and_master_contracts(tmp_path):
    workspace,q,digest=fixture(tmp_path);out=adapt(tmp_path,q,workspace)
    result=out['provider_result'];jsonschema.validate(result,SCHEMA)
    assert result['result']=='PASS' and result['operator_actions_after_dispatch']==0
    assert result['artifact']['sha256']==digest and result['artifact']['provider_original_bytes'] is True
    intake=out['intake_receipt'];assert intake['ingestion_state']=='STAGED_NOT_CANONICAL'
    assert Path(intake['staged_blob_path']).read_bytes()==Path(q['dispatch']['export_artifact_path']).read_bytes()
    master=out['master_facts'];assert master['schema']=='die.factory-asset.master-facts.v1' and master['source_kind']=='PROVIDER_ORIGINAL'
    assert master['provider_id']=='chatgpt' and master['sha256']==digest


def test_private_muxia_artifact_is_never_required_or_read(tmp_path):
    workspace,q,_=fixture(tmp_path)
    q['dispatch']['artifact_path']='/definitely/missing/private/muxia/artifact.png'
    out=adapt(tmp_path,q,workspace)
    assert out['ownership_boundary']['factory_reads_private_muxia_artifact'] is False
    assert out['ownership_boundary']['browser_owner']=='MUXIA'


def test_rejects_non_automated_or_secret_touching_dispatch(tmp_path):
    workspace,q,_=fixture(tmp_path)
    bad=copy.deepcopy(q);bad['dispatch']['prompt_submitted_by_automation']=False
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_AUTOMATION_INCOMPLETE'
    bad=copy.deepcopy(q);bad['dispatch']['cookies_or_tokens_read']=True
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_SECRET_BOUNDARY_VIOLATION'


def test_rejects_authority_or_private_boundary_escalation(tmp_path):
    workspace,q,_=fixture(tmp_path)
    bad=copy.deepcopy(q);bad['dispatch']['publication_authorized']=True
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_AUTHORITY_BOUNDARY_VIOLATION'
    bad=copy.deepcopy(q);bad['dispatch']['private_artifact_access_by_hermes']=True
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_PRIVATE_BOUNDARY_VIOLATION'


def test_rejects_hash_dimension_byte_and_export_path_drift(tmp_path):
    workspace,q,_=fixture(tmp_path)
    bad=copy.deepcopy(q);bad['dispatch']['export_artifact_sha256']='c'*64
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_EXPORT_HASH_UNVERIFIED'
    bad=copy.deepcopy(q);bad['dispatch']['generated_image_observed']['width']=999
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_DIMENSION_DRIFT'
    bad=copy.deepcopy(q);bad['dispatch']['bytes']+=1
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_BYTE_COUNT_DRIFT'
    bad=copy.deepcopy(q);outside=tmp_path/'outside.png';outside.write_bytes(Path(q['dispatch']['export_artifact_path']).read_bytes());bad['dispatch']['export_artifact_path']=str(outside)
    try: adapt(tmp_path,bad,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_EXPORT_PATH_UNSAFE'


def test_failed_queue_result_never_becomes_factory_success(tmp_path):
    workspace,q,_=fixture(tmp_path);q['status']='FAILED';q['error']='provider timeout'
    try: adapt(tmp_path,q,workspace);assert False
    except m.MuxiaProviderAdapterError as e: assert e.code=='MUXIA_RESULT_NOT_SUCCEEDED'


def test_adapter_has_no_browser_process_or_private_root_ownership():
    text=P.read_text()
    for forbidden in ('import subprocess','playwright','chromium.launch','connectOverCDP','/var/lib/muxia'):
        assert forbidden not in text
    assert "'browser_owner': 'MUXIA'" in text and "'session_owner': 'MUXIA'" in text
