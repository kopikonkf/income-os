from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]

def _load(name:str,path:Path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

vector_gate=_load('trace_vector_gate',ROOT/'company/factory-asset/lib/vectorizability.py')
native_vector=_load('trace_native_vector',ROOT/'company/factory-asset/lib/native_vector.py')

class TraceError(ValueError):
 def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def trace_raster_to_svg(path:str|Path,*,evidence:dict[str,Any],threshold:int=200,max_paths:int=128)->dict[str,Any]:
 decision=vector_gate.classify_vectorizability(evidence)
 if decision.state!='TRACE_ELIGIBLE':raise TraceError('TRACE_NOT_ELIGIBLE',','.join(decision.reason_codes))
 p=Path(path)
 if not p.is_file():raise TraceError('INPUT_NOT_FOUND',str(p))
 gray=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
 if gray is None:raise TraceError('INPUT_DECODE_FAILED',str(p))
 _,binary=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY_INV)
 contours,_=cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
 contours=[c for c in contours if cv2.contourArea(c)>=4]
 if not contours:raise TraceError('NO_TRACEABLE_SHAPE','no contour')
 if len(contours)>max_paths:raise TraceError('TRACE_PATH_COUNT_EXCEEDED',str(len(contours)))
 paths=[]
 for c in sorted(contours,key=lambda x:(cv2.boundingRect(x)[1],cv2.boundingRect(x)[0])):
  eps=max(0.5,0.01*cv2.arcLength(c,True));approx=cv2.approxPolyDP(c,eps,True)
  pts=[tuple(map(int,p[0])) for p in approx]
  if len(pts)<3:continue
  d='M '+' L '.join(f'{x} {y}' for x,y in pts)+' Z';paths.append(d)
 if not paths:raise TraceError('NO_EDITABLE_PATHS','all contours degenerate')
 h,w=gray.shape
 svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}">{}</svg>'.format(w,h,''.join(f'<path d="{d}" fill="#000000"/>' for d in paths))
 normalized=native_vector.normalize_svg(svg,max_paths=max_paths)
 preview=native_vector.render_preview(normalized,size=256)
 return {'schema':'die.factory-asset.trace-result.v1','state':'TRACE_ELIGIBLE','reason_codes':list(decision.reason_codes),'svg':normalized['canonical_svg'],'svg_sha256':normalized['sha256'],'path_count':len(normalized['paths']),'editable_paths':True,'preview_size':list(preview.size),'source_dimensions':[w,h]}