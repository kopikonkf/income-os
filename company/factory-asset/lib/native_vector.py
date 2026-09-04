from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from PIL import Image,ImageDraw

SVG_NS='{http://www.w3.org/2000/svg}'
CMD_RE=re.compile(r'([MLHVZmlhvz])|(-?\d+(?:\.\d+)?)')
class VectorExportError(ValueError):
 def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def _parse_path(d:str)->list[tuple[float,float]]:
 toks=[a or b for a,b in CMD_RE.findall(d)];pts=[];i=0;cmd=None;x=y=0.0;start=None
 while i<len(toks):
  t=toks[i]
  if t.isalpha():cmd=t;i+=1
  if cmd is None:raise VectorExportError('PATH_SYNTAX_INVALID',d)
  if cmd in 'Zz':
   if start and pts[-1]!=start:pts.append(start)
   cmd=None;continue
  rel=cmd.islower();op=cmd.upper()
  if op in ('M','L'):
   if i+1>=len(toks):raise VectorExportError('PATH_SYNTAX_INVALID',d)
   nx=float(toks[i]);ny=float(toks[i+1]);i+=2
   if rel:nx+=x;ny+=y
   x,y=nx,ny;pts.append((x,y));start=start or (x,y)
   if op=='M':cmd='l' if rel else 'L'
  elif op=='H':
   nx=float(toks[i]);i+=1;x=x+nx if rel else nx;pts.append((x,y))
  elif op=='V':
   ny=float(toks[i]);i+=1;y=y+ny if rel else ny;pts.append((x,y))
  else:raise VectorExportError('PATH_COMMAND_UNSUPPORTED',cmd)
 if len(pts)<2:raise VectorExportError('PATH_EMPTY',d)
 return pts

def normalize_svg(svg_text:str,*,max_paths:int=512)->dict[str,Any]:
 try:root=ET.fromstring(svg_text)
 except ET.ParseError as e:raise VectorExportError('SVG_XML_INVALID',str(e))
 if root.tag not in ('svg',SVG_NS+'svg'):raise VectorExportError('SVG_ROOT_INVALID',root.tag)
 for tag in ('image','text','foreignObject'):
  if root.findall('.//'+tag) or root.findall('.//'+SVG_NS+tag):raise VectorExportError('SVG_FORBIDDEN_ELEMENT',tag)
 vb=root.attrib.get('viewBox')
 if not vb:raise VectorExportError('VIEWBOX_REQUIRED','missing')
 try:minx,miny,w,h=[float(x) for x in vb.replace(',',' ').split()]
 except Exception as e:raise VectorExportError('VIEWBOX_INVALID',vb) from e
 if w<=0 or h<=0:raise VectorExportError('VIEWBOX_INVALID',vb)
 paths=root.findall('.//path')+root.findall('.//'+SVG_NS+'path')
 if not paths:raise VectorExportError('VECTOR_PATHS_REQUIRED','none')
 if len(paths)>max_paths:raise VectorExportError('PATH_COUNT_EXCEEDED',str(len(paths)))
 normalized=[]
 for p in paths:
  d=p.attrib.get('d','').strip();pts=_parse_path(d)
  if any(px<minx or py<miny or px>minx+w or py>miny+h for px,py in pts):raise VectorExportError('PATH_OUT_OF_BOUNDS',d)
  normalized.append({'d':d,'points':pts,'fill':p.attrib.get('fill','#000000'),'stroke':p.attrib.get('stroke','none')})
 canonical='<svg xmlns="http://www.w3.org/2000/svg" viewBox="{} {} {} {}">{}</svg>'.format(minx,miny,w,h,''.join(f'<path d="{x["d"]}" fill="{x["fill"]}" stroke="{x["stroke"]}"/>' for x in normalized))
 return {'schema':'die.factory-asset.native-svg.v1','viewbox':[minx,miny,w,h],'paths':normalized,'canonical_svg':canonical,'sha256':hashlib.sha256(canonical.encode()).hexdigest()}

def export_eps(norm:dict[str,Any])->str:
 minx,miny,w,h=norm['viewbox'];lines=['%!PS-Adobe-3.0 EPSF-3.0',f'%%BoundingBox: 0 0 {int(round(w))} {int(round(h))}','1 setlinejoin','1 setlinecap']
 for path in norm['paths']:
  pts=path['points'];x0,y0=pts[0];lines+=['newpath',f'{x0-minx:.3f} {h-(y0-miny):.3f} moveto']
  for x,y in pts[1:]:lines.append(f'{x-minx:.3f} {h-(y-miny):.3f} lineto')
  if pts[-1]==pts[0]:lines.append('closepath')
  lines.append('fill' if path['fill']!='none' else 'stroke')
 lines+=['showpage','%%EOF'];return '\n'.join(lines)+'\n'

def render_preview(norm:dict[str,Any],*,size:int=256)->Image.Image:
 minx,miny,w,h=norm['viewbox'];scale=min(size/w,size/h);img=Image.new('RGB',(max(1,int(round(w*scale))),max(1,int(round(h*scale)))),'white');draw=ImageDraw.Draw(img)
 for path in norm['paths']:
  pts=[((x-minx)*scale,(y-miny)*scale) for x,y in path['points']];
  if len(pts)>=3 and pts[-1]==pts[0]:draw.polygon(pts,fill='black')
  else:draw.line(pts,fill='black',width=max(1,int(scale)))
 return img