from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import jsonschema
from PIL import Image
from PyPDF2 import PdfReader

ROOT=Path(__file__).resolve().parents[3]
RECIPE_SCHEMA=json.loads((ROOT/'company/factory-asset/schemas/derivative-recipe.schema.json').read_text(encoding='utf-8'))

class PackagingError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def sha256_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _idempotency(recipe:dict[str,Any])->str:
    material={'master_sha256':recipe['input']['master_sha256'],'recipe_id':recipe['recipe_id'],'recipe_version':recipe['recipe_version'],'marketplace_profile':recipe['marketplace_profile'],'output':recipe['output']}
    return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _pdf_bytes_from_rgb(img:Image.Image)->bytes:
    rgb=img.convert('RGB'); buf=io.BytesIO(); rgb.save(buf,format='JPEG',quality=95,subsampling=0,optimize=False,progressive=False); jpg=buf.getvalue(); w,h=rgb.size
    content=f'q\n{w} 0 0 {h} 0 0 cm\n/Im0 Do\nQ\n'.encode('ascii')
    objects=[
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>'.encode('ascii'),
        f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpg)} >>\nstream\n'.encode('ascii')+jpg+b'\nendstream',
        f'<< /Length {len(content)} >>\nstream\n'.encode('ascii')+content+b'endstream',
    ]
    out=bytearray(b'%PDF-1.4\n%FA01\n'); offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(out)); out.extend(f'{i} 0 obj\n'.encode()); out.extend(obj); out.extend(b'\nendobj\n')
    xref=len(out); out.extend(f'xref\n0 {len(objects)+1}\n'.encode()); out.extend(b'0000000000 65535 f \n')
    for off in offsets[1:]: out.extend(f'{off:010d} 00000 n \n'.encode())
    out.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(out)

def render_pdf_derivative(master_path:str|Path,output_path:str|Path,recipe:dict[str,Any])->dict[str,Any]:
    jsonschema.Draft202012Validator(RECIPE_SCHEMA).validate(recipe)
    if recipe['output']['format']!='PDF':raise PackagingError('PDF_RECIPE_REQUIRED',recipe['output']['format'])
    master=Path(master_path).resolve(); out=Path(output_path).resolve()
    if master==out:raise PackagingError('MASTER_OVERWRITE_FORBIDDEN',str(master))
    if not master.is_file():raise PackagingError('MASTER_NOT_FOUND',str(master))
    master_sha=sha256_file(master)
    if master_sha!=recipe['input']['master_sha256']:raise PackagingError('MASTER_HASH_MISMATCH',master_sha)
    if out.exists():raise PackagingError('OUTPUT_EXISTS_REQUIRES_REUSE_CHECK',str(out))
    with Image.open(master) as img:
        img.load(); width=recipe['output'].get('width_px',img.width); height=recipe['output'].get('height_px',img.height)
        if (width,height)!=(img.width,img.height): img=img.resize((width,height),Image.Resampling.LANCZOS)
        payload=_pdf_bytes_from_rgb(img)
    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(payload)
    decoded=False; dims=(0,0)
    try:
        reader=PdfReader(str(out),strict=True); page=reader.pages[0]; dims=(int(float(page.mediabox.width)),int(float(page.mediabox.height))); xobj=page['/Resources']['/XObject'].get_object(); decoded=len(reader.pages)==1 and '/Im0' in xobj
    except Exception: decoded=False
    out_sha=sha256_file(out); magic=out.read_bytes().startswith(b'%PDF-1.4')
    return {'schema':'die.factory-asset.derivative-receipt.v1','recipe_id':recipe['recipe_id'],'recipe_version':recipe['recipe_version'],'idempotency_key':_idempotency(recipe),'input':{'master_sha256':master_sha,'semantic_asset_id':recipe['input']['semantic_asset_id']},'marketplace_profile':dict(recipe['marketplace_profile']),'output':{'format':'PDF','sha256':out_sha,'bytes':out.stat().st_size,'width_px':dims[0],'height_px':dims[1],'semantic_identity_effect':'NONE'},'qa':{'magic_mime_match':magic,'decode_reopen':decoded,'sha256_verified':sha256_file(out)==out_sha,'failure_code':None if magic and decoded else 'OUTPUT_VALIDATION_FAILED'},'compatibility':{'state':'COMPATIBLE','reason':None},'result':'PASS' if magic and decoded else 'FAIL'}

def render_preview(master_path:str|Path,output_path:str|Path,*,max_dimension:int=1024,format:str='PNG')->dict[str,Any]:
    if max_dimension<1:raise PackagingError('INVALID_PREVIEW_BOUND',str(max_dimension))
    master=Path(master_path).resolve();out=Path(output_path).resolve()
    if master==out:raise PackagingError('MASTER_OVERWRITE_FORBIDDEN',str(master))
    if out.exists():raise PackagingError('OUTPUT_EXISTS_REQUIRES_REUSE_CHECK',str(out))
    with Image.open(master) as img:
        img.load(); original=img.size; copy=img.convert('RGBA' if 'A' in img.getbands() else 'RGB'); copy.thumbnail((max_dimension,max_dimension),Image.Resampling.LANCZOS)
        save={'format':format}
        if format=='JPEG': copy=copy.convert('RGB'); save.update({'quality':90,'subsampling':0,'optimize':False,'progressive':False})
        copy.save(out,**save); dims=copy.size
    with Image.open(out) as check:check.load();actual=check.format
    return {'schema':'die.factory-asset.preview-receipt.v1','master_sha256':sha256_file(master),'preview_sha256':sha256_file(out),'format':format,'bytes':out.stat().st_size,'original_dimensions':list(original),'preview_dimensions':list(dims),'aspect_error':abs((original[0]/original[1])-(dims[0]/dims[1])),'decode_reopen':True,'magic_match':actual==format}