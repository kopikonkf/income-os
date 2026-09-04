from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageCms

class DerivativePolicyError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

ALLOWED_KEYS={'color_space','icc_policy','alpha_policy','dpi','metadata_policy'}

def validate_policy(policy:dict[str,Any])->dict[str,Any]:
    unknown=sorted(set(policy)-ALLOWED_KEYS)
    if unknown:raise DerivativePolicyError('UNKNOWN_POLICY_FIELD',','.join(unknown))
    required=ALLOWED_KEYS-set(policy)
    if required:raise DerivativePolicyError('POLICY_INCOMPLETE',','.join(sorted(required)))
    if policy['color_space'] not in {'SRGB'}:raise DerivativePolicyError('COLOR_SPACE_UNSUPPORTED',str(policy['color_space']))
    if policy['icc_policy'] not in {'EMBED_SRGB','PRESERVE_SOURCE','STRIP'}:raise DerivativePolicyError('ICC_POLICY_UNKNOWN',str(policy['icc_policy']))
    if policy['alpha_policy'] not in {'PRESERVE','FLATTEN_WHITE','FORBID'}:raise DerivativePolicyError('ALPHA_POLICY_UNKNOWN',str(policy['alpha_policy']))
    dpi=policy['dpi']
    if not isinstance(dpi,int) or isinstance(dpi,bool) or dpi<36 or dpi>2400:raise DerivativePolicyError('DPI_INVALID',str(dpi))
    if policy['metadata_policy'] not in {'STRIP_ALL','PRESERVE_SAFE'}:raise DerivativePolicyError('METADATA_POLICY_UNKNOWN',str(policy['metadata_policy']))
    return dict(policy)

def _srgb_icc_bytes()->bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()

def apply_policy(master_path:str|Path,output_path:str|Path,*,format:str,policy:dict[str,Any])->dict[str,Any]:
    p=validate_policy(policy);master=Path(master_path);out=Path(output_path)
    if master.resolve()==out.resolve():raise DerivativePolicyError('MASTER_OVERWRITE_FORBIDDEN',str(master))
    if out.exists():raise DerivativePolicyError('OUTPUT_EXISTS',str(out))
    with Image.open(master) as img:
        img.load();source_info=dict(img.info);has_alpha=img.mode in ('RGBA','LA') or (img.mode=='P' and 'transparency' in img.info)
        if p['alpha_policy']=='FORBID' and has_alpha:raise DerivativePolicyError('ALPHA_FORBIDDEN',format)
        if p['alpha_policy']=='FLATTEN_WHITE' and has_alpha:
            rgba=img.convert('RGBA');bg=Image.new('RGBA',rgba.size,(255,255,255,255));bg.alpha_composite(rgba);working=bg.convert('RGB')
        elif p['alpha_policy']=='PRESERVE' and has_alpha:working=img.convert('RGBA')
        else:working=img.convert('RGB') if img.mode not in ('RGB','RGBA') else img.copy()
        if format=='JPEG' and 'A' in working.getbands():raise DerivativePolicyError('JPEG_ALPHA_FORBIDDEN','use FLATTEN_WHITE')
        kwargs:dict[str,Any]={'dpi':(p['dpi'],p['dpi'])}
        if p['icc_policy']=='EMBED_SRGB':kwargs['icc_profile']=_srgb_icc_bytes()
        elif p['icc_policy']=='PRESERVE_SOURCE':
            if 'icc_profile' not in source_info:raise DerivativePolicyError('SOURCE_ICC_REQUIRED','PRESERVE_SOURCE requested but absent')
            kwargs['icc_profile']=source_info['icc_profile']
        if p['metadata_policy']=='PRESERVE_SAFE':
            safe_comment=source_info.get('comment')
            if safe_comment is not None:kwargs['comment']=safe_comment
        if format=='JPEG':kwargs.update({'quality':92,'subsampling':0,'optimize':False,'progressive':False})
        if format=='TIFF':kwargs['compression']='tiff_lzw'
        out.parent.mkdir(parents=True,exist_ok=True);working.save(out,format=format,**kwargs)
    return verify_policy(out,policy=p)

def verify_policy(path:str|Path,*,policy:dict[str,Any])->dict[str,Any]:
    p=validate_policy(policy);path=Path(path)
    with Image.open(path) as img:
        img.load();bands=img.getbands();info=dict(img.info);dpi=info.get('dpi')
        alpha_present='A' in bands
        if p['alpha_policy']=='PRESERVE':alpha_ok=alpha_present
        elif p['alpha_policy'] in {'FLATTEN_WHITE','FORBID'}:alpha_ok=not alpha_present
        else:alpha_ok=False
        icc=info.get('icc_profile')
        if p['icc_policy']=='EMBED_SRGB':icc_state='EMBEDDED' if icc else 'MISSING'
        elif p['icc_policy']=='PRESERVE_SOURCE':icc_state='PRESERVED' if icc else 'MISSING'
        else:icc_state='STRIPPED' if not icc else 'UNEXPECTED_PRESENT'
        if dpi is None:dpi_ok=False;actual_dpi=None
        else:
            actual_dpi=(round(float(dpi[0])),round(float(dpi[1])));dpi_ok=abs(actual_dpi[0]-p['dpi'])<=1 and abs(actual_dpi[1]-p['dpi'])<=1
        structural={'jfif','jfif_version','jfif_unit','jfif_density','compression','progressive','progression'}
        metadata_keys=sorted(k for k in info if k not in {'icc_profile','dpi'} and k not in structural)
        metadata_ok=(not metadata_keys) if p['metadata_policy']=='STRIP_ALL' else all(k in {'comment'} for k in metadata_keys)
        pass_state=alpha_ok and dpi_ok and metadata_ok and icc_state not in {'MISSING','UNEXPECTED_PRESENT'}
        return {'schema':'die.factory-asset.derivative-policy-verification.v1','result':'PASS' if pass_state else 'FAIL','format':img.format,'color_space':'SRGB_DECLARED_AND_VERIFIED_BY_POLICY','icc_state':icc_state,'alpha_state':'PRESENT' if alpha_present else 'ABSENT','alpha_policy':p['alpha_policy'],'alpha_ok':alpha_ok,'dpi_requested':p['dpi'],'dpi_actual':list(actual_dpi) if actual_dpi else None,'dpi_ok':dpi_ok,'metadata_policy':p['metadata_policy'],'metadata_keys':metadata_keys,'metadata_ok':metadata_ok}