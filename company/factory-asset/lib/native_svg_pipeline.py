from __future__ import annotations

import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

SVG_NS='{http://www.w3.org/2000/svg}'
ALLOWED_TAGS={'svg','g','path'}
FORBIDDEN_TAGS={'script','image','text','foreignObject','use','style','defs','symbol','iframe','audio','video'}
PATH_ALLOWED=re.compile(r'^[MLHVZmlhvz0-9+.,\-\s]+$')
URLISH=re.compile(r'url\s*\(|(?:https?|file|data):',re.I)
HEX=re.compile(r'^#[0-9a-fA-F]{6}$')
SHORT_HEX=re.compile(r'^#[0-9a-fA-F]{3}$')

class NativeSvgPipelineError(ValueError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def sha256_bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def sha256_value(v:Any)->str:return sha256_bytes(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())

def _local(tag:str)->str:return tag.rsplit('}',1)[-1]
def _color(v:str|None,*,default:str)->str:
    v=(v or default).strip()
    if v=='none':return v
    if SHORT_HEX.fullmatch(v):return '#'+''.join(ch*2 for ch in v[1:]).lower()
    if HEX.fullmatch(v):return v.lower()
    raise NativeSvgPipelineError('COLOR_UNSAFE',v)
def _rgb(v:str)->tuple[int,int,int]:
    if v=='none':return (0,0,0)
    return tuple(int(v[i:i+2],16) for i in (1,3,5))
def _parse_points(d:str)->list[tuple[float,float]]:
    if not d or not PATH_ALLOWED.fullmatch(d):raise NativeSvgPipelineError('PATH_COMMAND_UNSUPPORTED',d[:200])
    toks=re.findall(r'[MLHVZmlhvz]|[-+]?\d+(?:\.\d+)?',d);pts=[];i=0;cmd=None;x=y=0.0;start=None
    while i<len(toks):
        t=toks[i]
        if t.isalpha():cmd=t;i+=1
        if cmd is None:raise NativeSvgPipelineError('PATH_SYNTAX_INVALID',d[:200])
        if cmd in 'Zz':
            if start is not None and pts and pts[-1]!=start:pts.append(start)
            cmd=None;continue
        rel=cmd.islower();op=cmd.upper()
        if op in ('M','L'):
            if i+1>=len(toks):raise NativeSvgPipelineError('PATH_SYNTAX_INVALID',d[:200])
            nx=float(toks[i]);ny=float(toks[i+1]);i+=2
            if rel:nx+=x;ny+=y
            x,y=nx,ny;pts.append((x,y));start=start or (x,y)
            if op=='M':cmd='l' if rel else 'L'
        elif op=='H':
            if i>=len(toks):raise NativeSvgPipelineError('PATH_SYNTAX_INVALID',d[:200])
            nx=float(toks[i]);i+=1;x=x+nx if rel else nx;pts.append((x,y))
        elif op=='V':
            if i>=len(toks):raise NativeSvgPipelineError('PATH_SYNTAX_INVALID',d[:200])
            ny=float(toks[i]);i+=1;y=y+ny if rel else ny;pts.append((x,y))
        else:raise NativeSvgPipelineError('PATH_COMMAND_UNSUPPORTED',cmd)
    if len(pts)<2:raise NativeSvgPipelineError('PATH_EMPTY',d[:200])
    if any(not math.isfinite(a) or not math.isfinite(b) for a,b in pts):raise NativeSvgPipelineError('PATH_NONFINITE',d[:200])
    return pts

def validate_and_normalize(svg_text:str,*,max_bytes:int=1_048_576,max_paths:int=512,max_total_points:int=8192,max_path_chars:int=32768)->dict[str,Any]:
    raw=svg_text.encode('utf-8')
    if not raw or len(raw)>max_bytes:raise NativeSvgPipelineError('SVG_SIZE_INVALID',str(len(raw)))
    low=svg_text.casefold()
    if '<!doctype' in low or '<!entity' in low:raise NativeSvgPipelineError('SVG_DTD_FORBIDDEN','doctype/entity')
    try:root=ET.fromstring(svg_text)
    except ET.ParseError as e:raise NativeSvgPipelineError('SVG_XML_INVALID',str(e))
    if _local(root.tag)!='svg':raise NativeSvgPipelineError('SVG_ROOT_INVALID',root.tag)
    vb=root.attrib.get('viewBox')
    if not vb:raise NativeSvgPipelineError('VIEWBOX_REQUIRED','missing')
    try:minx,miny,w,h=[float(x) for x in vb.replace(',',' ').split()]
    except Exception as e:raise NativeSvgPipelineError('VIEWBOX_INVALID',vb) from e
    if not all(math.isfinite(x) for x in (minx,miny,w,h)) or w<=0 or h<=0 or w>100000 or h>100000:raise NativeSvgPipelineError('VIEWBOX_INVALID',vb)
    for el in root.iter():
        tag=_local(el.tag)
        if tag in FORBIDDEN_TAGS:raise NativeSvgPipelineError('SVG_FORBIDDEN_ELEMENT',tag)
        if tag not in ALLOWED_TAGS:raise NativeSvgPipelineError('SVG_ELEMENT_UNSUPPORTED',tag)
        for k,v in el.attrib.items():
            lk=_local(k).casefold(); sv=str(v)
            if lk.startswith('on'):raise NativeSvgPipelineError('SVG_EVENT_HANDLER_FORBIDDEN',lk)
            if lk in {'href','xlink:href','src','font-family','style'} or URLISH.search(sv):raise NativeSvgPipelineError('SVG_EXTERNAL_OR_STYLE_FORBIDDEN',f'{lk}={sv[:100]}')
    paths=[el for el in root.iter() if _local(el.tag)=='path']
    if not paths:raise NativeSvgPipelineError('VECTOR_PATHS_REQUIRED','none')
    if len(paths)>max_paths:raise NativeSvgPipelineError('PATH_COUNT_EXCEEDED',str(len(paths)))
    normalized=[];total_points=0
    for el in paths:
        d=(el.attrib.get('d') or '').strip()
        if len(d)>max_path_chars:raise NativeSvgPipelineError('PATH_COMPLEXITY_EXCEEDED',str(len(d)))
        pts=_parse_points(d);total_points+=len(pts)
        if total_points>max_total_points:raise NativeSvgPipelineError('PATH_COMPLEXITY_EXCEEDED',str(total_points))
        if any(px<minx or py<miny or px>minx+w or py>miny+h for px,py in pts):raise NativeSvgPipelineError('PATH_OUT_OF_BOUNDS',d[:200])
        fill=_color(el.attrib.get('fill'),default='#000000');stroke=_color(el.attrib.get('stroke'),default='none')
        try:sw=float(el.attrib.get('stroke-width','1'))
        except Exception as e:raise NativeSvgPipelineError('STROKE_WIDTH_INVALID',str(el.attrib.get('stroke-width'))) from e
        if not math.isfinite(sw) or sw<0 or sw>max(w,h):raise NativeSvgPipelineError('STROKE_WIDTH_INVALID',str(sw))
        if fill=='none' and stroke=='none':raise NativeSvgPipelineError('INVISIBLE_PATH',d[:100])
        normalized.append({'d':d,'points':pts,'fill':fill,'stroke':stroke,'stroke_width':sw})
    body=''.join(f'<path d="{x["d"]}" fill="{x["fill"]}" stroke="{x["stroke"]}" stroke-width="{x["stroke_width"]:g}"/>' for x in normalized)
    canonical=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:g} {miny:g} {w:g} {h:g}">{body}</svg>'
    result={'schema':'die.factory-asset.native-svg-safe.v1','viewbox':[minx,miny,w,h],'paths':normalized,'path_count':len(normalized),'total_points':total_points,'canonical_svg':canonical,'canonical_svg_sha256':sha256_bytes(canonical.encode()),'native_editable':True,'generated_by_native_producer':True,'conversion_from_raster':False}
    img=render_png_image(result,size=512)
    ink=sum(1 for px in img.getdata() if px[:3]!=(255,255,255))
    if ink<16:raise NativeSvgPipelineError('BLANK_OR_NEAR_BLANK_OUTPUT',str(ink))
    result['render_ink_pixels_512']=ink
    return result

def render_png_image(norm:dict[str,Any],*,size:int=1024)->Image.Image:
    minx,miny,w,h=norm['viewbox'];scale=min(size/w,size/h);ow=max(1,int(round(w*scale)));oh=max(1,int(round(h*scale)))
    img=Image.new('RGB',(ow,oh),'white');draw=ImageDraw.Draw(img)
    for path in norm['paths']:
        pts=[((x-minx)*scale,(y-miny)*scale) for x,y in path['points']]
        closed=len(pts)>=3 and pts[-1]==pts[0]
        if path['fill']!='none' and closed:draw.polygon(pts,fill=_rgb(path['fill']))
        if path['stroke']!='none':draw.line(pts,fill=_rgb(path['stroke']),width=max(1,int(round(path['stroke_width']*scale))),joint='curve')
    return img

def png_bytes(norm:dict[str,Any],*,size:int=1024)->bytes:
    b=io.BytesIO();render_png_image(norm,size=size).save(b,format='PNG',optimize=False);return b.getvalue()
def jpeg_bytes(norm:dict[str,Any],*,size:int=1024)->bytes:
    b=io.BytesIO();render_png_image(norm,size=size).save(b,format='JPEG',quality=95,subsampling=0,optimize=False,progressive=False);return b.getvalue()
def eps_bytes(norm:dict[str,Any])->bytes:
    minx,miny,w,h=norm['viewbox'];lines=['%!PS-Adobe-3.0 EPSF-3.0',f'%%BoundingBox: 0 0 {int(math.ceil(w))} {int(math.ceil(h))}','1 setlinejoin','1 setlinecap']
    for p in norm['paths']:
        pts=p['points'];x0,y0=pts[0];lines+=['newpath',f'{x0-minx:.3f} {h-(y0-miny):.3f} moveto']
        for x,y in pts[1:]:lines.append(f'{x-minx:.3f} {h-(y-miny):.3f} lineto')
        if len(pts)>=3 and pts[-1]==pts[0]:lines.append('closepath')
        if p['fill']!='none':
            r,g,b=_rgb(p['fill']);lines.append(f'{r/255:.6f} {g/255:.6f} {b/255:.6f} setrgbcolor');lines.append('fill')
        elif p['stroke']!='none':
            r,g,b=_rgb(p['stroke']);lines.append(f'{p["stroke_width"]:.3f} setlinewidth');lines.append(f'{r/255:.6f} {g/255:.6f} {b/255:.6f} setrgbcolor');lines.append('stroke')
    lines+=['showpage','%%EOF'];return ('\n'.join(lines)+'\n').encode('ascii')

def package_svg_master(*,svg_text:str,semantic_asset_id:str,blueprint_sha256:str,provider_prompt_sha256:str)->dict[str,Any]:
    norm=validate_and_normalize(svg_text); svg=norm['canonical_svg'].encode(); eps=eps_bytes(norm); png=png_bytes(norm); jpg=jpeg_bytes(norm)
    master={'format':'SVG','bytes':len(svg),'sha256':sha256_bytes(svg),'native_editable':True,'generated_by_native_producer':True,'conversion_from_raster':False,'lineage_sha256_required':True}
    deriv=[]
    for did,fmt,purpose,data in [('ADOBE_EPS','EPS','MARKETPLACE_DELIVERY',eps),('PNG_PREVIEW','PNG','PREVIEW',png),('JPEG_PREVIEW','JPEG','PREVIEW',jpg)]:
        deriv.append({'derivative_id':did,'format':fmt,'purpose':purpose,'bytes':len(data),'sha256':sha256_bytes(data),'semantic_identity_effect':'NONE'})
    package={'schema':'die.factory-asset.native-svg-package.v1','semantic_asset_id':semantic_asset_id,'blueprint_sha256':blueprint_sha256,'provider_prompt_sha256':provider_prompt_sha256,'master':master,'derivatives':deriv,'semantic_asset_count':1,'derivatives_create_new_semantic_asset':False,'qa':{'path_count':norm['path_count'],'total_points':norm['total_points'],'render_ink_pixels_512':norm['render_ink_pixels_512'],'independent_render':'PIL_FROM_PARSED_VECTOR_GEOMETRY'}}
    package['package_sha256']=sha256_value(package)
    return {'package':package,'normalized':norm,'bytes':{'SVG':svg,'EPS':eps,'PNG':png,'JPEG':jpg}}
