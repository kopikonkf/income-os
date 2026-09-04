from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image
from PyPDF2 import PdfReader

class DerivativeQAError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

MAGIC={
 'PNG':lambda b:b.startswith(b'\x89PNG\r\n\x1a\n'),
 'JPEG':lambda b:b.startswith(b'\xff\xd8\xff'),
 'WEBP':lambda b:len(b)>=12 and b[:4]==b'RIFF' and b[8:12]==b'WEBP',
 'TIFF':lambda b:b.startswith((b'II*\x00',b'MM\x00*')),
 'PDF':lambda b:b.startswith(b'%PDF-'),
}

def sha256_file(path:Path)->str:
 h=hashlib.sha256();
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def inspect_derivative(path:str|Path,*,expected_format:str,expected_dimensions:tuple[int,int]|None=None,expected_alpha:str='ANY',allowed_formats:set[str]|None=None,expected_sha256:str|None=None)->dict[str,Any]:
 p=Path(path);failures=[]
 if not p.is_file():return {'schema':'die.factory-asset.derivative-qa.v1','result':'FAIL','failures':['FILE_NOT_FOUND']}
 data=p.read_bytes();magic_ok=expected_format in MAGIC and MAGIC[expected_format](data)
 if not magic_ok:failures.append('MAGIC_FORMAT_MISMATCH')
 decoded=False;dims=None;alpha=None
 try:
  if expected_format=='PDF':
   reader=PdfReader(str(p),strict=True);page=reader.pages[0];dims=(int(float(page.mediabox.width)),int(float(page.mediabox.height)));decoded=len(reader.pages)>=1;alpha=False
  else:
   with Image.open(p) as img:
    img.load();decoded=True;dims=img.size;alpha='A' in img.getbands()
 except Exception:
  failures.append('DECODE_REOPEN_FAILED')
 if expected_dimensions is not None and dims!=expected_dimensions:failures.append('DIMENSIONS_MISMATCH')
 if expected_alpha=='PRESENT' and alpha is not True:failures.append('ALPHA_MISMATCH')
 if expected_alpha=='ABSENT' and alpha is not False:failures.append('ALPHA_MISMATCH')
 if allowed_formats is not None and expected_format not in allowed_formats:failures.append('COMPATIBILITY_FORMAT_FORBIDDEN')
 actual_sha=sha256_file(p)
 if expected_sha256 is not None and actual_sha!=expected_sha256:failures.append('SHA256_MISMATCH')
 return {'schema':'die.factory-asset.derivative-qa.v1','result':'PASS' if not failures else 'FAIL','failures':failures,'format':expected_format,'magic_mime_match':magic_ok,'decode_reopen':decoded,'dimensions':list(dims) if dims else None,'alpha_state':'PRESENT' if alpha else 'ABSENT' if alpha is False else 'UNKNOWN','sha256':actual_sha,'bytes':p.stat().st_size,'compatibility':'COMPATIBLE' if allowed_formats is None or expected_format in allowed_formats else 'INCOMPATIBLE'}