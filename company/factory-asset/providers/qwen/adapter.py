"""FA-111 clean Qwen image-provider logic extracted from Windows evidence.

No credential store, browser lifecycle, private session material, Windows path, or raw
capture is embedded here. SESSION_API remains primary. BROWSER_CDP is an explicit
fallback transport owned by the external governed browser runtime (MUXIA on Linux).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PROVIDER_ID='qwen'
PRIMARY_TRANSPORT='SESSION_API'
FALLBACK_TRANSPORT='BROWSER_CDP'
ALLOWED_TRANSPORTS=(PRIMARY_TRANSPORT,FALLBACK_TRANSPORT)
DEFAULT_MODEL='qwen3.8-max'
BASE_URL='https://chat.qwen.ai'


class QwenAdapterError(ValueError):
    def __init__(self,code:str,message:str):
        super().__init__(f'{code}: {message}');self.code=code


@dataclass(frozen=True)
class SessionRequestContext:
    chat_id:str
    parent_id:str|None
    fid:str
    child_id:str
    timestamp:int
    prompt:str
    model:str=DEFAULT_MODEL


def capability()->dict[str,Any]:
    return {'schema':'die.factory-asset.image-provider.v1','kind':'CAPABILITY','provider_id':PROVIDER_ID,'contract_version':'1.0.0','transport_classes':[PRIMARY_TRANSPORT,FALLBACK_TRANSPORT],'image_generation':True,'output_formats':['PNG','JPEG','WEBP'],'supports_transparency':'UNKNOWN','supports_requested_dimensions':'UNKNOWN','capacity_state':'UNKNOWN'}


def select_transport(requested:str|None=None)->str:
    mode=(requested or PRIMARY_TRANSPORT).strip().upper()
    if mode not in ALLOWED_TRANSPORTS: raise QwenAdapterError('TRANSPORT_UNSUPPORTED',mode)
    return mode


def build_new_chat_payload(*,model:str=DEFAULT_MODEL,timestamp:int)->dict[str,Any]:
    if not model.strip(): raise QwenAdapterError('MODEL_REQUIRED','empty')
    if timestamp<=0: raise QwenAdapterError('TIMESTAMP_INVALID',str(timestamp))
    return {'chatId':'','models':[model],'project_id':'','timestamp':timestamp}


def parse_chat_id(value:dict[str,Any])->str:
    if not isinstance(value,dict): raise QwenAdapterError('NEW_CHAT_RESPONSE_INVALID','object required')
    candidates=[value.get('chat_id'),value.get('chatId')]
    data=value.get('data') if isinstance(value.get('data'),dict) else {}
    candidates += [data.get('chat_id'),data.get('chatId'),data.get('id')]
    for item in candidates:
        if isinstance(item,str) and item.strip(): return item.strip()
    raise QwenAdapterError('CHAT_ID_MISSING','no accepted chat id field')


def build_t2i_payload(ctx:SessionRequestContext)->dict[str,Any]:
    prompt=ctx.prompt.strip()
    if not prompt: raise QwenAdapterError('PROMPT_REQUIRED','empty')
    if not ctx.chat_id.strip(): raise QwenAdapterError('CHAT_ID_REQUIRED','empty')
    if ctx.timestamp<=0: raise QwenAdapterError('TIMESTAMP_INVALID',str(ctx.timestamp))
    msg={'id':None,'fid':ctx.fid,'parentId':ctx.parent_id,'childrenIds':[ctx.child_id],'role':'user','content':prompt,'user_action':'chat','files':[],'timestamp':ctx.timestamp,'models':[ctx.model],'model':'','chat_type':'t2i','feature_config':{'thinking_enabled':False,'output_schema':'phase','research_mode':'normal','auto_thinking':False,'thinking_mode':'Thinking','thinking_format':'summary','auto_search':False,'image_enabled':True,'plugin_enabled':True},'extra':{'meta':{'subChatType':'t2i'}},'sub_chat_type':'t2i','parent_id':ctx.parent_id}
    return {'stream':True,'version':'2.1','incremental_output':True,'chatId':ctx.chat_id,'parentId':ctx.parent_id,'chat_id':ctx.chat_id,'chat_mode':'normal','model':ctx.model,'parent_id':ctx.parent_id,'messages':[msg],'timestamp':ctx.timestamp}


def parse_sse(lines:Iterable[str])->dict[str,Any]:
    text=[];extra_urls=[];parent_id=None
    for line in lines:
        if not isinstance(line,str) or not line.startswith('data: '): continue
        raw=line[6:].strip()
        if raw=='[DONE]': break
        try: parsed=json.loads(raw)
        except json.JSONDecodeError:
            text.append(raw);continue
        choices=parsed.get('choices') if isinstance(parsed,dict) else None
        if not isinstance(choices,list) or not choices: continue
        choice=choices[0] if isinstance(choices[0],dict) else {}
        delta=choice.get('delta') if isinstance(choice.get('delta'),dict) else {}
        content=delta.get('content')
        if isinstance(content,str) and content: text.append(content)
        extra=delta.get('extra') if isinstance(delta.get('extra'),dict) else {}
        for key in ('tool_result','image_list'):
            rows=extra.get(key)
            if isinstance(rows,list):
                for item in rows:
                    if isinstance(item,dict) and isinstance(item.get('image'),str): extra_urls.append(item['image'])
        parent_id=choice.get('message_id') or choice.get('id') or parsed.get('response_id') or parsed.get('id') or parent_id
    return {'text':' '.join(text).strip(),'extra_image_urls':_dedupe(extra_urls),'parent_id':parent_id}


def _dedupe(items:list[str])->list[str]: return list(dict.fromkeys(x for x in items if x))


def extract_image_candidates(*,text:str,extra_image_urls:list[str]|None=None)->dict[str,list[str]]:
    text=text or '';urls=[];b64=[];s=text.strip()
    if s.startswith('https://') and re.search(r'\.(?:png|jpe?g|webp)(?:\?|$)',s,re.I): urls.append(s.split()[0].split('\n')[0])
    urls += re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)',text)
    urls += re.findall(r'https?://[^\s\"\'<>]+\.(?:png|jpg|jpeg|webp)(?:\?[^\s\"\'<>]*)?',text,re.I)
    for match in re.finditer(r'\{[^{}]*\"(?:image_url|url|b64_json|inlineData)\"[^{}]*\}',text):
        try: obj=json.loads(match.group(0))
        except json.JSONDecodeError: continue
        for key in ('image_url','url'):
            if isinstance(obj.get(key),str): urls.append(obj[key])
        for key in ('b64_json','inlineData'):
            if isinstance(obj.get(key),str): b64.append(obj[key])
    try: whole=json.loads(text)
    except Exception: whole=None
    if isinstance(whole,dict):
        for key in ('image_url','url'):
            if isinstance(whole.get(key),str): urls.append(whole[key])
        for key in ('b64_json','inlineData'):
            if isinstance(whole.get(key),str): b64.append(whole[key])
    urls += list(extra_image_urls or [])
    if not urls and not b64:
        compact=''.join(s.split())
        if len(compact)>2000 and re.fullmatch(r'[A-Za-z0-9+/=]+',compact):
            try:
                raw=base64.b64decode(compact,validate=True)
                if raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8'): b64.append(compact)
            except Exception: pass
    return {'urls':_dedupe(urls),'b64':_dedupe(b64)}


def provider_original_url(src:str)->str:
    if 'cdn.qwenlm.ai/output/' not in src: return src
    parts=urlsplit(src);query=[(k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if k.lower()!='x-oss-process']
    return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),parts.fragment))


def classify_http_failure(*,status:int,body_text:str='')->dict[str,Any]:
    body=(body_text or '').lower()
    if status in (401,403): return {'code':'AUTH_REQUIRED','retryable':False}
    if status==429: return {'code':'RATE_LIMITED','retryable':True}
    if any(x in body for x in ('captcha','verify you are human','security verification','unusual activity')): return {'code':'PROTECTION_CHALLENGE','retryable':False}
    if status>=500: return {'code':'PROVIDER_ERROR','retryable':True}
    if status>=400: return {'code':'PROVIDER_ERROR','retryable':False}
    return {'code':'UNKNOWN','retryable':False}


def browser_fallback_envelope(*,prompt:str,deadline_seconds:int)->dict[str,Any]:
    if not prompt.strip(): raise QwenAdapterError('PROMPT_REQUIRED','empty')
    if not 1<=deadline_seconds<=900: raise QwenAdapterError('DEADLINE_INVALID',str(deadline_seconds))
    return {'schema':'die.factory-asset.qwen-browser-fallback.v1','provider_id':PROVIDER_ID,'transport_class':FALLBACK_TRANSPORT,'transport_role':'FALLBACK','primary_transport':PRIMARY_TRANSPORT,'browser_runtime_owner':'MUXIA','prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'deadline_seconds':deadline_seconds,'credential_values_embedded':False,'session_material_embedded':False}
