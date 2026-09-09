from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import sys
_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import h03_factory

RECEIPT_SCHEMA = "die.h03.local-product-package.v1"


def _claim_index(kp: dict[str, Any]) -> dict[str, dict[str, Any]]:
    h03_factory.validate_knowledge_package(kp)
    return {c["claim_id"]: c for c in kp["claims"]}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def _slug(text: str) -> str:
    value=re.sub(r'[^a-zA-Z0-9]+','-',text.strip().lower()).strip('-')
    return value[:120] or 'h03-product'


def validate_content_batches(*, blueprint: dict[str, Any], knowledge_package: dict[str, Any], content_batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims=_claim_index(knowledge_package)
    if blueprint.get('schema_version')!='die.h03.product-blueprint.v1' or blueprint.get('knowledge_package_id')!=knowledge_package.get('knowledge_package_id'):
        raise ValueError('PRODUCT_PACKAGE_BLUEPRINT_INVALID')
    sections=blueprint.get('sections') or []
    if not isinstance(content_batches,list) or len(content_batches)!=len(sections):
        raise ValueError('PRODUCT_PACKAGE_SECTION_BATCH_COUNT_MISMATCH')
    by_section={b.get('section_id'):b for b in content_batches if isinstance(b,dict)}
    if len(by_section)!=len(content_batches):
        raise ValueError('PRODUCT_PACKAGE_DUPLICATE_SECTION_BATCH')
    ordered=[]
    for idx,section in enumerate(sections,start=1):
        sid=f'SEC-{idx:03d}'
        batch=by_section.get(sid)
        if not batch:
            raise ValueError(f'PRODUCT_PACKAGE_SECTION_BATCH_MISSING:{sid}')
        if batch.get('schema_version')!='die.h03.content-block-batch.v1' or batch.get('truth_status')!='DERIVED_SEMANTIC_CONTENT':
            raise ValueError('PRODUCT_PACKAGE_CONTENT_BATCH_INVALID')
        if batch.get('product_id')!=blueprint.get('product_id') or batch.get('knowledge_package_id')!=knowledge_package.get('knowledge_package_id'):
            raise ValueError('PRODUCT_PACKAGE_CONTENT_LINEAGE_MISMATCH')
        if batch.get('section_heading')!=section.get('heading'):
            raise ValueError('PRODUCT_PACKAGE_SECTION_HEADING_MISMATCH')
        allowed=set(section.get('claim_ids') or [])
        covered:set[str]=set()
        for block in batch.get('blocks') or []:
            ids=block.get('claim_ids') or []
            if not ids or not set(ids).issubset(allowed):
                raise ValueError('PRODUCT_PACKAGE_BLOCK_CLAIM_SCOPE_INVALID')
            covered.update(ids)
            expected=[]
            for cid in ids:
                if cid not in claims:
                    raise ValueError(f'PRODUCT_PACKAGE_UNKNOWN_CLAIM:{cid}')
                for ref in claims[cid]['evidence_refs']:
                    if ref not in expected:
                        expected.append(ref)
            if block.get('evidence_refs')!=expected:
                raise ValueError('PRODUCT_PACKAGE_BLOCK_EVIDENCE_MISMATCH')
        if covered!=allowed:
            missing=sorted(allowed-covered)
            raise ValueError('PRODUCT_PACKAGE_SECTION_CLAIM_COVERAGE_MISSING:'+','.join(missing))
        ordered.append(batch)
    return ordered


def assemble_document_ast(*, blueprint: dict[str, Any], knowledge_package: dict[str, Any], content_batches: list[dict[str, Any]]) -> dict[str, Any]:
    ordered=validate_content_batches(blueprint=blueprint,knowledge_package=knowledge_package,content_batches=content_batches)
    blocks=[]
    lineage=[]
    for batch in ordered:
        blocks.append({'type':'heading','text':batch['section_heading']})
        step_no=0
        for block in batch['blocks']:
            kind=block['kind']; text=block['text']
            if kind=='STEP':
                step_no+=1; ast_type='bullet'; rendered=f'{step_no}. {text}'
            elif kind=='BULLET':
                ast_type='bullet'; rendered=f'- {text}'
            elif kind=='CHECKLIST_ITEM':
                ast_type='bullet'; rendered=f'[ ] {text}'
            elif kind=='CALLOUT':
                ast_type='paragraph'; rendered=f'Note: {text}'
            elif kind=='INPUT_PROMPT':
                ast_type='paragraph'; rendered=f'Input: {text} ____________________'
            else:
                ast_type='paragraph'; rendered=text
            ast_block={'type':ast_type,'text':rendered}
            if len(block['claim_ids'])==1:
                ast_block['claim_id']=block['claim_ids'][0]
            blocks.append(ast_block)
            lineage.append({'block_id':block['block_id'],'section_id':batch['section_id'],'claim_ids':list(block['claim_ids']),'evidence_refs':list(block['evidence_refs'])})
    metadata=dict(blueprint.get('metadata') or {})
    metadata.update({'title':blueprint['title'],'subtitle':blueprint.get('subtitle',''),'form':blueprint['form'],'content_lineage':lineage,'content_batch_ids':[b['content_batch_id'] for b in ordered]})
    return {'schema_version':'die.h03.document-ast.v1','product_id':blueprint['product_id'],'knowledge_package_id':knowledge_package['knowledge_package_id'],'metadata':metadata,'blocks':blocks}


def _deterministic_zip(zip_path: Path, files: list[tuple[str,Path]]) -> None:
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for arcname,path in sorted(files,key=lambda x:x[0]):
            info=zipfile.ZipInfo(arcname,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644 << 16
            zf.writestr(info,path.read_bytes())


def build_local_product_package(*, output_root: Path, blueprint: dict[str, Any], knowledge_package: dict[str, Any], content_batches: list[dict[str, Any]]) -> dict[str, Any]:
    ast=assemble_document_ast(blueprint=blueprint,knowledge_package=knowledge_package,content_batches=content_batches)
    slug=_slug(blueprint['title'])
    package_dir=output_root / blueprint['product_id']
    qa_dir=package_dir/'qa-renders'
    package_dir.mkdir(parents=True,exist_ok=True)
    ast_path=package_dir/'document-ast.json'
    blueprint_path=package_dir/'product-blueprint.json'
    content_path=package_dir/'content-block-batches.json'
    pdf_path=package_dir/f'{slug}.pdf'
    validation_path=package_dir/'validation.json'
    manifest_path=package_dir/'manifest.json'
    receipt_path=package_dir/'package-receipt.json'
    zip_path=package_dir/f'{slug}.zip'
    _write_json(ast_path,ast)
    _write_json(blueprint_path,blueprint)
    _write_json(content_path,content_batches)
    h03_factory.render_pdf(ast,pdf_path,template_id=(blueprint.get('metadata') or {}).get('template_id'))
    validation=h03_factory.validate_pdf(pdf_path,blueprint['title'],qa_dir)
    _write_json(validation_path,validation)
    manifest_files=[('document-ast.json',ast_path),('product-blueprint.json',blueprint_path),('content-block-batches.json',content_path),(pdf_path.name,pdf_path),('validation.json',validation_path)]
    manifest={'schema_version':'die.h03.local-product-manifest.v1','product_id':blueprint['product_id'],'files':{name:{'sha256':_sha256(path),'bytes':path.stat().st_size} for name,path in manifest_files}}
    _write_json(manifest_path,manifest)
    zip_files=manifest_files+[('manifest.json',manifest_path)]
    _deterministic_zip(zip_path,zip_files)
    receipt={'schema_version':RECEIPT_SCHEMA,'holding_id':'H03','product_id':blueprint['product_id'],'knowledge_package_id':knowledge_package['knowledge_package_id'],'form':blueprint['form'],'title':blueprint['title'],'pdf_file':pdf_path.name,'zip_file':zip_path.name,'manifest_file':manifest_path.name,'validation_file':validation_path.name,'content_batch_ids':[b['content_batch_id'] for b in validate_content_batches(blueprint=blueprint,knowledge_package=knowledge_package,content_batches=content_batches)],'external_publication':False,'status':'LOCAL_SALE_READY_UNREVIEWED','pdf_sha256':_sha256(pdf_path),'zip_sha256':_sha256(zip_path),'page_count':validation['page_count']}
    _write_json(receipt_path,receipt)
    return receipt
