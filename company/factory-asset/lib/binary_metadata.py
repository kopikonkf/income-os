from __future__ import annotations

import hashlib
import os
import struct
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr
from PIL import Image

XMP_HEADER=b'http://ns.adobe.com/xap/1.0/\x00'
PS_HEADER=b'Photoshop 3.0\x00'
IPTC_RESOURCE_ID=0x0404

class BinaryMetadataError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def sha256_file(path:str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def _fields(metadata:dict[str,Any])->dict[str,Any]:
    title=str(metadata.get('title','')).strip();description=str(metadata.get('description','')).strip();keywords=metadata.get('keywords');ai=str(metadata.get('ai_disclosure','')).strip()
    if not title or not description:raise BinaryMetadataError('METADATA_TEXT_REQUIRED','title/description')
    if not isinstance(keywords,list) or not keywords or any(not isinstance(x,str) or not x.strip() for x in keywords):raise BinaryMetadataError('METADATA_KEYWORDS_REQUIRED','keywords')
    if ai not in {'GENERATIVE_AI','NOT_AI_GENERATED'}:raise BinaryMetadataError('AI_DISCLOSURE_INVALID',ai)
    return {'title':title,'description':description,'keywords':[x.strip() for x in keywords],'ai_disclosure':ai}

def _segment(marker:int,payload:bytes)->bytes:
    if len(payload)+2>65535:raise BinaryMetadataError('JPEG_METADATA_SEGMENT_TOO_LARGE',str(len(payload)))
    return b'\xff'+bytes([marker])+struct.pack('>H',len(payload)+2)+payload

def _iptc_dataset(record:int,dataset:int,value:bytes)->bytes:
    if len(value)>32767:raise BinaryMetadataError('IPTC_VALUE_TOO_LARGE',f'{record}:{dataset}')
    return b'\x1c'+bytes([record,dataset])+struct.pack('>H',len(value))+value

def _iptc_payload(fields:dict[str,Any])->bytes:
    rows=[_iptc_dataset(1,90,b'\x1b%G'),_iptc_dataset(2,5,fields['title'].encode('utf-8')), _iptc_dataset(2,120,fields['description'].encode('utf-8'))]
    rows.extend(_iptc_dataset(2,25,k.encode('utf-8')) for k in fields['keywords'])
    rows.append(_iptc_dataset(2,40,('AI_DISCLOSURE='+fields['ai_disclosure']).encode('utf-8')))
    return b''.join(rows)

def _photoshop_iptc(fields:dict[str,Any])->bytes:
    data=_iptc_payload(fields);name=b'\x00\x00';resource=b'8BIM'+struct.pack('>H',IPTC_RESOURCE_ID)+name+struct.pack('>I',len(data))+data
    if len(data)%2:resource+=b'\x00'
    return PS_HEADER+resource

def _xmp_payload(fields:dict[str,Any])->bytes:
    items=''.join(f'<rdf:li>{escape(k)}</rdf:li>' for k in fields['keywords'])
    xml=(f'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
         f'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
         f'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
         f'<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" xmlns:die="https://digital-income-empire.invalid/ns/factory-asset/1.0/" die:factoryAssetMetadataVersion="1" die:aiDisclosure={quoteattr(fields["ai_disclosure"])}>'
         f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{escape(fields["title"])}</rdf:li></rdf:Alt></dc:title>'
         f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{escape(fields["description"])}</rdf:li></rdf:Alt></dc:description>'
         f'<dc:subject><rdf:Bag>{items}</rdf:Bag></dc:subject>'
         f'<photoshop:Instructions>{escape("AI_DISCLOSURE="+fields["ai_disclosure"])}</photoshop:Instructions>'
         f'</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>')
    return XMP_HEADER+xml.encode('utf-8')

def _jpeg_segments(data:bytes)->list[tuple[int,bytes]]:
    if not data.startswith(b'\xff\xd8'):raise BinaryMetadataError('JPEG_MAGIC_INVALID','SOI')
    pos=2;rows=[]
    while pos<len(data):
        if data[pos]!=0xff:raise BinaryMetadataError('JPEG_SEGMENT_INVALID',str(pos))
        start=pos
        while pos<len(data) and data[pos]==0xff:pos+=1
        if pos>=len(data):raise BinaryMetadataError('JPEG_TRUNCATED','marker')
        marker=data[pos];pos+=1
        if marker in {0xd8}:continue
        if marker in {0xd9}:rows.append((marker,data[start:pos]));break
        if marker==0xda:
            if pos+2>len(data):raise BinaryMetadataError('JPEG_TRUNCATED','SOS length')
            length=struct.unpack('>H',data[pos:pos+2])[0]
            if length<2 or pos+length>len(data):raise BinaryMetadataError('JPEG_TRUNCATED','SOS body')
            rows.append((marker,data[start:]));break
        if marker==0x01 or 0xd0<=marker<=0xd7:
            rows.append((marker,data[start:pos]));continue
        if pos+2>len(data):raise BinaryMetadataError('JPEG_TRUNCATED','segment length')
        length=struct.unpack('>H',data[pos:pos+2])[0]
        if length<2 or pos+length>len(data):raise BinaryMetadataError('JPEG_TRUNCATED',f'marker {marker:02x}')
        end=pos+length;rows.append((marker,data[start:end]));pos=end
    if not rows or rows[-1][0] not in {0xda,0xd9}:raise BinaryMetadataError('JPEG_NO_SCAN','missing SOS/EOI')
    return rows

def _payload(raw:bytes)->bytes:
    return raw[4:] if len(raw)>=4 else b''

def _parse_iptc(data:bytes)->dict[str,Any]:
    pos=0;title=None;description=None;keywords=[];ai=None
    while pos<len(data):
        if pos+5>len(data) or data[pos]!=0x1c:raise BinaryMetadataError('IPTC_PARSE_ERROR',str(pos))
        record,dataset=data[pos+1],data[pos+2];length=struct.unpack('>H',data[pos+3:pos+5])[0];pos+=5
        if pos+length>len(data):raise BinaryMetadataError('IPTC_TRUNCATED',f'{record}:{dataset}')
        value=data[pos:pos+length];pos+=length
        if (record,dataset)==(2,5):title=value.decode('utf-8')
        elif (record,dataset)==(2,120):description=value.decode('utf-8')
        elif (record,dataset)==(2,25):keywords.append(value.decode('utf-8'))
        elif (record,dataset)==(2,40):
            text=value.decode('utf-8')
            if text.startswith('AI_DISCLOSURE='):ai=text.split('=',1)[1]
    return {'title':title,'description':description,'keywords':keywords,'ai_disclosure':ai}

def _iptc_from_app13(payload:bytes)->bytes|None:
    if not payload.startswith(PS_HEADER):return None
    pos=len(PS_HEADER)
    while pos+8<=len(payload):
        if payload[pos:pos+4]!=b'8BIM':raise BinaryMetadataError('PHOTOSHOP_RESOURCE_INVALID',str(pos))
        rid=struct.unpack('>H',payload[pos+4:pos+6])[0];pos+=6
        nlen=payload[pos];pos+=1+nlen
        if (1+nlen)%2:pos+=1
        if pos+4>len(payload):raise BinaryMetadataError('PHOTOSHOP_RESOURCE_TRUNCATED','size')
        size=struct.unpack('>I',payload[pos:pos+4])[0];pos+=4
        if pos+size>len(payload):raise BinaryMetadataError('PHOTOSHOP_RESOURCE_TRUNCATED','data')
        value=payload[pos:pos+size];pos+=size+(size%2)
        if rid==IPTC_RESOURCE_ID:return value
    return None

def readback_jpeg(path:str|Path)->dict[str,Any]:
    p=Path(path);data=p.read_bytes();segments=_jpeg_segments(data);xmp=None;iptc=None
    for marker,raw in segments:
        payload=_payload(raw)
        if marker==0xe1 and payload.startswith(XMP_HEADER):
            if xmp is not None:raise BinaryMetadataError('DUPLICATE_XMP','multiple APP1 XMP')
            xmp=payload[len(XMP_HEADER):]
        if marker==0xed and payload.startswith(PS_HEADER):
            found=_iptc_from_app13(payload)
            if found is not None:
                if iptc is not None:raise BinaryMetadataError('DUPLICATE_IPTC','multiple APP13 IPTC')
                iptc=found
    if xmp is None:raise BinaryMetadataError('XMP_NOT_FOUND',str(p))
    if iptc is None:raise BinaryMetadataError('IPTC_NOT_FOUND',str(p))
    try:root=ET.fromstring(xmp.decode('utf-8'))
    except Exception as exc:raise BinaryMetadataError('XMP_PARSE_ERROR',type(exc).__name__) from exc
    ns={'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#','dc':'http://purl.org/dc/elements/1.1/','photoshop':'http://ns.adobe.com/photoshop/1.0/','die':'https://digital-income-empire.invalid/ns/factory-asset/1.0/'}
    desc=root.find('.//rdf:Description',ns)
    if desc is None:raise BinaryMetadataError('XMP_DESCRIPTION_MISSING','rdf:Description')
    def text(path):
        node=root.find(path,ns);return node.text if node is not None else None
    xfields={'title':text('.//dc:title/rdf:Alt/rdf:li'),'description':text('.//dc:description/rdf:Alt/rdf:li'),'keywords':[n.text or '' for n in root.findall('.//dc:subject/rdf:Bag/rdf:li',ns)],'ai_disclosure':desc.attrib.get('{https://digital-income-empire.invalid/ns/factory-asset/1.0/}aiDisclosure')}
    if text('.//photoshop:Instructions')!=('AI_DISCLOSURE='+str(xfields['ai_disclosure'])):raise BinaryMetadataError('XMP_AI_INSTRUCTIONS_MISMATCH','photoshop:Instructions')
    return {'schema':'die.factory-asset.binary-metadata-readback.v1','format':'JPEG','sha256':sha256_file(p),'xmp':xfields,'iptc':_parse_iptc(iptc)}

def inject_jpeg(*,source_path:str|Path,output_path:str|Path,metadata:dict[str,Any])->dict[str,Any]:
    src=Path(source_path).resolve();out=Path(output_path).resolve();fields=_fields(metadata)
    if src==out:raise BinaryMetadataError('IMMUTABLE_SOURCE_OVERWRITE_FORBIDDEN',str(src))
    if not src.is_file():raise BinaryMetadataError('SOURCE_NOT_FOUND',str(src))
    data=src.read_bytes();segments=_jpeg_segments(data)
    for marker,raw in segments:
        payload=_payload(raw)
        if marker==0xe1 and payload.startswith(XMP_HEADER):raise BinaryMetadataError('EXISTING_XMP_UNSUPPORTED',str(src))
        if marker==0xed and payload.startswith(PS_HEADER) and _iptc_from_app13(payload) is not None:raise BinaryMetadataError('EXISTING_IPTC_UNSUPPORTED',str(src))
    source_sha=sha256_file(src)
    with Image.open(src) as im:im.load();dims=im.size
    encoded=data[:2]+_segment(0xe1,_xmp_payload(fields))+_segment(0xed,_photoshop_iptc(fields))+data[2:]
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=out.name+'.',suffix='.tmp',dir=str(out.parent));os.close(fd);tp=Path(tmp)
    try:
        tp.write_bytes(encoded);readback=readback_jpeg(tp)
        with Image.open(tp) as im:im.load();out_dims=im.size
        if out_dims!=dims:raise BinaryMetadataError('PIXEL_DIMENSIONS_CHANGED',f'{dims}->{out_dims}')
        if readback['xmp']!=fields:raise BinaryMetadataError('XMP_READBACK_MISMATCH',str(readback['xmp']))
        if readback['iptc']!=fields:raise BinaryMetadataError('IPTC_READBACK_MISMATCH',str(readback['iptc']))
        os.replace(tp,out)
    finally:
        if tp.exists():tp.unlink()
    output_sha=sha256_file(out)
    if output_sha==source_sha:raise BinaryMetadataError('OUTPUT_HASH_NOT_CHANGED',output_sha)
    return {'schema':'die.factory-asset.binary-metadata-injection.v1','result':'PASS','format':'JPEG','source_path':str(src),'source_sha256':source_sha,'output_path':str(out),'output_sha256':output_sha,'dimensions':[dims[0],dims[1]],'xmp_readback':'PASS','iptc_readback':'PASS','fields':fields,'immutable_source_preserved':sha256_file(src)==source_sha,'semantic_identity_effect':'NONE','platform_form_ai_disclosure_still_required':True}

def inject_or_sidecar(*,source_path:str|Path,output_path:str|Path,format:str,metadata:dict[str,Any])->dict[str,Any]:
    fmt=str(format).upper()
    if fmt!='JPEG':
        p=Path(source_path);return {'schema':'die.factory-asset.binary-metadata-injection.v1','result':'SIDECAR_ONLY','format':fmt,'source_path':str(p.resolve()),'source_sha256':sha256_file(p),'output_path':None,'output_sha256':None,'reason':'FORMAT_NOT_SUPPORTED_V1','semantic_identity_effect':'NONE','platform_form_ai_disclosure_still_required':True}
    return inject_jpeg(source_path=source_path,output_path=output_path,metadata=metadata)