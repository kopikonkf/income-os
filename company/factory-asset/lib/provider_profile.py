from __future__ import annotations
from dataclasses import dataclass
from typing import Any

class LeaseError(RuntimeError):
    def __init__(self, code: str, message: str): super().__init__(f"{code}: {message}"); self.code=code

@dataclass(frozen=True)
class ProviderLease:
    token: str
    principal_id: str
    profile_id: str
    owner: str

class ProviderLeaseRegistry:
    def __init__(self): self._by_profile: dict[str, ProviderLease]={}; self._by_principal: dict[str, ProviderLease]={}
    def acquire(self, *, token:str, principal_id:str, profile_id:str, owner:str) -> ProviderLease:
        if not all((token,principal_id,profile_id,owner)): raise LeaseError('INVALID_LEASE_REQUEST','all fields required')
        existing=self._by_profile.get(profile_id)
        if existing:
            if existing.token==token and existing.owner==owner and existing.principal_id==principal_id: return existing
            raise LeaseError('PROFILE_ALREADY_LEASED',profile_id)
        p=self._by_principal.get(principal_id)
        if p and p.profile_id != profile_id: raise LeaseError('PRINCIPAL_CROSS_PROFILE_OWNERSHIP',f'{principal_id}:{p.profile_id}->{profile_id}')
        lease=ProviderLease(token,principal_id,profile_id,owner); self._by_profile[profile_id]=lease; self._by_principal[principal_id]=lease; return lease
    def release(self, *, token:str, profile_id:str) -> None:
        lease=self._by_profile.get(profile_id)
        if not lease: return
        if lease.token != token: raise LeaseError('LEASE_TOKEN_MISMATCH',profile_id)
        self._by_profile.pop(profile_id,None); self._by_principal.pop(lease.principal_id,None)
    def active(self, profile_id:str) -> ProviderLease|None: return self._by_profile.get(profile_id)

def sanitize_profile(profile:dict[str,Any]) -> dict[str,Any]:
    out={k:v for k,v in profile.items() if k!='credential_ref'}
    out['credential_state']='OPAQUE_REFERENCE_PRESENT' if profile.get('credential_ref',{}).get('opaque_ref') else 'MISSING'
    return out