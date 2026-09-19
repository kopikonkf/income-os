from __future__ import annotations
import hashlib,json,mimetypes,os,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from typing import Any

SCHEMA="die.factory-asset.media-rights-handoff.v1"
AUTH_SCHEMA="die.factory-asset.rights-authorization.v1"
class MediaRightsHandoffError(ValueError):
 def __init__(self,code:str,message:str): super().__init__(f"{code}: {message}"); self.code=code

def canon(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()

def load_auth(path:Path|None,expected:str)->dict[str,Any]|None:
 if path is None or not path.is_file():return None
 d=json.loads(path.read_text())
 req={"schema","artifact_sha256","basis","publish_allowed","commercial_use_allowed","derivatives_allowed","attribution_required","attribution_text","evidence_refs","authorized_by","state"}
 if not isinstance(d,dict) or set(d)!=req:raise MediaRightsHandoffError("RIGHTS_AUTH_SHAPE",str(path))
 if d["schema"]!=AUTH_SCHEMA or d["state"]!="APPROVED":raise MediaRightsHandoffError("RIGHTS_AUTH_STATE",str(d.get("state")))
 if d["artifact_sha256"]!=expected:raise MediaRightsHandoffError("RIGHTS_AUTH_HASH_MISMATCH",str(d["artifact_sha256"]))
 if d["basis"] not in {"owned_original","licensed","public_domain","user_provided","other"}:raise MediaRightsHandoffError("RIGHTS_AUTH_BASIS",str(d["basis"]))
 for k in ("publish_allowed","commercial_use_allowed","derivatives_allowed","attribution_required"):
  if type(d[k]) is not bool:raise MediaRightsHandoffError("RIGHTS_AUTH_BOOLEAN",k)
 if d["attribution_required"] and not str(d["attribution_text"] or "").strip():raise MediaRightsHandoffError("RIGHTS_AUTH_ATTRIBUTION","missing")
 if not isinstance(d["evidence_refs"],list) or any(not isinstance(x,str) or not x.strip() for x in d["evidence_refs"]):raise MediaRightsHandoffError("RIGHTS_AUTH_EVIDENCE","invalid")
 return d

def build_handoff(*,workspace:str|Path,package_readiness:dict[str,Any],rights_signal:dict[str,Any],final_manifest:dict[str,Any],delivery_evidence:dict[str,Any],rights_authorization_path:str|Path|None=None)->dict[str,Any]:
 root=Path(workspace).resolve()
 if package_readiness.get("result")!="PACKAGE_READY":raise MediaRightsHandoffError("PACKAGE_NOT_READY",str(package_readiness.get("result")))
 if rights_signal.get("result")!="PASS":raise MediaRightsHandoffError("RIGHTS_SIGNAL_NOT_PASS",str(rights_signal.get("result")))
 p=Path(final_manifest["listing_path"]).resolve()
 if not p.is_file():raise MediaRightsHandoffError("ARTIFACT_NOT_FOUND",str(p))
 try:p.relative_to(root)
 except ValueError as e:raise MediaRightsHandoffError("ARTIFACT_OUTSIDE_WORKSPACE",str(p)) from e
 actual=sha_file(p)
 if actual!=final_manifest.get("listing_sha256") or actual!=delivery_evidence.get("sha256"):raise MediaRightsHandoffError("DELIVERY_HASH_MISMATCH",actual)
 if delivery_evidence.get("qa_result")!="PASS":raise MediaRightsHandoffError("DELIVERY_QA_NOT_PASS",str(delivery_evidence.get("qa_result")))
 did=str(delivery_evidence.get("derivative_id") or "MARKETPLACE_DELIVERY")
 sid=str(final_manifest["semantic_asset_id"])
 aref="h01:"+hashlib.sha256(f"{sid}:{did}:{actual}".encode()).hexdigest()[:40]
 base=os.environ.get("DIE_MEDIA_PUBLIC_BASE_URL","").strip().rstrip("/")
 if base and not base.startswith("https://"):raise MediaRightsHandoffError("PUBLIC_BASE_URL_INVALID",base)
 source_uri=f"{base}/{urllib.parse.quote(p.name)}" if base else None
 auth=load_auth(Path(rights_authorization_path).resolve() if rights_authorization_path else None,actual)
 if auth:
  rref="h01-rights:"+hashlib.sha256(canon({"artifact_ref":aref,"authorization":auth})).hexdigest()[:40]
  rights={"state":"ATTESTED","rights_ref":rref,"basis":auth["basis"],"publish_allowed":auth["publish_allowed"],"commercial_use_allowed":auth["commercial_use_allowed"],"derivatives_allowed":auth["derivatives_allowed"],"attribution_required":auth["attribution_required"],"attribution_text":auth["attribution_text"],"evidence_refs":auth["evidence_refs"],"attested_by":auth["authorized_by"]}
 else:
  rights={"state":"REVIEW_REQUIRED","rights_ref":None,"basis":None,"publish_allowed":False,"commercial_use_allowed":False,"derivatives_allowed":False,"attribution_required":False,"attribution_text":None,"evidence_refs":[f"rights-signal:{hashlib.sha256(canon(rights_signal)).hexdigest()}",f"package-plan:{package_readiness['package_plan']['package_plan_sha256']}"],"attested_by":None}
 m={"schema":SCHEMA,"handoff_id":"","source":{"system":"H01_FACTORY_ASSET","workspace":str(root),"task_id":final_manifest["task_id"],"semantic_asset_id":sid,"blueprint_id":final_manifest["blueprint_id"],"package_plan_sha256":package_readiness["package_plan"]["package_plan_sha256"]},"artifact":{"artifact_ref":aref,"sha256":actual,"mime_type":mimetypes.guess_type(p.name)[0] or "application/octet-stream","size_bytes":p.stat().st_size,"source_uri":source_uri,"delivery_state":"READY" if source_uri else "DELIVERY_URL_PENDING","filename":p.name,"derivative_id":did,"qa_receipt_ref":str(delivery_evidence.get("receipt_ref") or "")},"rights":rights,"authority":{"publication_authorized":False,"submission_authorized":False,"founder_qc_required":True,"human_rights_clearance_claimed":False}}
 m["handoff_id"]="h01-media:"+hashlib.sha256(canon({k:v for k,v in m.items() if k!="handoff_id"})).hexdigest()[:40]
 return m

def emit_outbox(*,workspace:str|Path,manifest:dict[str,Any])->dict[str,Any]:
 out=Path(workspace).resolve()/"handoff";out.mkdir(parents=True,exist_ok=True);p=out/"media-rights-handoff.json"
 payload=json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+"\n";tmp=p.with_suffix(".tmp");tmp.write_text(payload);tmp.replace(p)
 return {"schema":"die.factory-asset.media-rights-handoff-outbox.v1","handoff_id":manifest["handoff_id"],"path":str(p),"sha256":hashlib.sha256(payload.encode()).hexdigest(),"state":"PENDING"}

def deliver_outbox(manifest:dict[str,Any])->dict[str,Any]:
 endpoint=os.environ.get("DIE_AGENTS_H01_HANDOFF_URL","").strip();token=os.environ.get("DIE_AGENTS_H01_HANDOFF_TOKEN","").strip()
 if not endpoint or not token:return {"state":"DEFERRED_NOT_CONFIGURED","handoff_id":manifest["handoff_id"]}
 if not(endpoint.startswith("https://") or endpoint.startswith("http://127.0.0.1")):raise MediaRightsHandoffError("HANDOFF_URL_INVALID",endpoint)
 req=urllib.request.Request(endpoint,data=canon(manifest),method="POST",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json","User-Agent":"DIE-H01-Media-Handoff/1.0"})
 try:
  with urllib.request.urlopen(req,timeout=5) as resp:return {"state":"DELIVERED","handoff_id":manifest["handoff_id"],"http_status":resp.status,"response":json.loads(resp.read().decode())}
 except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc:return {"state":"DEFERRED_DELIVERY_ERROR","handoff_id":manifest["handoff_id"],"error":type(exc).__name__}
