from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

MIB=1024**2; GIB=1024**3
SAFE_CACHE_DIRS=frozenset({'Cache','Code Cache','GPUCache','DawnGraphiteCache','DawnWebGPUCache','ShaderCache','GrShaderCache','VideoDecodeStats','optimization_guide_hint_cache_store'})
PROTECTED_NAMES=frozenset({'Accounts','ClientCertificates','Cookies','Login Data','Local Storage','Session Storage','Sessions','IndexedDB','Service Worker','WebStorage','Storage','GCM Store','Preferences','Secure Preferences','Network'})

def classify_name(name:str)->str:
    if name in SAFE_CACHE_DIRS:return 'RECREATABLE_CACHE'
    if name in PROTECTED_NAMES:return 'PROTECTED_SESSION_STATE'
    return 'UNKNOWN_PRESERVE'

def cleanup_candidates(profile:Path)->list[Path]:
    out=[]
    for base in (profile,profile/'Default'):
        if not base.is_dir():continue
        for name in SAFE_CACHE_DIRS:
            p=base/name
            if p.exists():out.append(p)
    return sorted(set(out))

def planning_envelopes(*,profile_a_bytes:int,profile_b_bytes:int,shared_chromium_mib:int=656,profiles:int=100)->dict:
    if min(profile_a_bytes,profile_b_bytes,profiles,shared_chromium_mib)<=0:raise ValueError('positive values required')
    shared=shared_chromium_mib*MIB;current=max(profile_a_bytes,profile_b_bytes)
    def row(per:int):
        total=profiles*per+shared
        return {'profiles':profiles,'per_profile_bytes':per,'shared_chromium_bytes':shared,'total_bytes':total,'total_gib':round(total/GIB,3)}
    return {'conservative_current_max':row(current),'one_gib_per_profile':row(GIB),'two_gib_per_profile':row(2*GIB),'note':'Persistent profile count is storage inventory, not active browser-owner concurrency.'}
