#!/usr/bin/env python3
from __future__ import annotations
import grp, hashlib, json, os, pwd, re, shutil, subprocess, sys
from pathlib import Path
TASK_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$')
ROOT=Path('/var/lib/die/workspaces').resolve()
MUXIA_ROOT=Path('/var/lib/muxia').resolve()
RUNNER=Path('/srv/die/company/muxia/scripts/linux/muxia-chatgpt-image.mjs')
NODE='/usr/local/bin/node'; XVFB='/usr/bin/xvfb-run'; RUNUSER='/usr/sbin/runuser'

def sha(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def inside(root:Path,p:Path)->bool:
 try:p.resolve().relative_to(root);return True
 except ValueError:return False

def existing(task:str):
 rp=MUXIA_ROOT/'state'/'receipts'/f'{task}-muxia.json'
 if not rp.is_file():return None
 try:r=json.loads(rp.read_text())
 except Exception:return None
 if r.get('status')!='SUCCEEDED':return None
 ap=Path(str(r.get('artifact_path','')))
 if not ap.is_file() or not inside(MUXIA_ROOT/'artifacts',ap):return None
 if sha(ap)!=r.get('sha256'):return None
 return r


DIE_USER='die-hermes'; DIE_GROUP='die-runtime'

def export_verified(task:str,r:dict)->dict:
 w=(ROOT/task).resolve(); src=Path(str(r['artifact_path'])).resolve()
 if not src.is_file() or not inside(MUXIA_ROOT/'artifacts',src): raise RuntimeError('E_PRIVATE_ARTIFACT')
 expected=str(r.get('sha256',''))
 if sha(src)!=expected: raise RuntimeError('E_PRIVATE_ARTIFACT_HASH')
 provider=w/'provider'; provider.mkdir(parents=True,exist_ok=True)
 uid=pwd.getpwnam(DIE_USER).pw_uid; gid=grp.getgrnam(DIE_GROUP).gr_gid
 os.chown(provider,uid,gid); os.chmod(provider,0o2770)
 ext=src.suffix.lower() or '.png'; dst=provider/('source-original'+ext); tmp=provider/(dst.name+f'.tmp-{os.getpid()}')
 with src.open('rb') as i, tmp.open('wb') as o: shutil.copyfileobj(i,o,1024*1024)
 if sha(tmp)!=expected: tmp.unlink(missing_ok=True); raise RuntimeError('E_EXPORT_HASH')
 os.chown(tmp,uid,gid); os.chmod(tmp,0o640); os.replace(tmp,dst)
 rp=MUXIA_ROOT/'state'/'receipts'/f'{task}-muxia.json'; rd=provider/'muxia-receipt.json'; rt=provider/(rd.name+f'.tmp-{os.getpid()}')
 shutil.copyfile(rp,rt); os.chown(rt,uid,gid); os.chmod(rt,0o640); os.replace(rt,rd)
 out=dict(r); out['export_artifact_path']=str(dst); out['export_artifact_sha256']=sha(dst); out['export_receipt_path']=str(rd); out['private_artifact_access_by_hermes']=False
 return out

def main()->int:
 if len(sys.argv)!=2 or not TASK_RE.fullmatch(sys.argv[1]):
  print('E_TASK_ID',file=sys.stderr);return 2
 task=sys.argv[1];w=(ROOT/task).resolve()
 if not w.is_dir() or not inside(ROOT,w):print('E_WORKSPACE',file=sys.stderr);return 2
 bp=w/'blueprint.json'; lock=w/'blueprint.lock.json'
 if not bp.is_file() or not lock.is_file():print('E_BLUEPRINT',file=sys.stderr);return 2
 v=json.loads(bp.read_text()); prod=v.get('production') if isinstance(v,dict) else None
 if not isinstance(prod,dict) or prod.get('engine')!='MUXIA/chatgpt-linux-a':print('E_ENGINE',file=sys.stderr);return 2
 prompt=str(prod.get('master_prompt','')).strip()
 if not (10<=len(prompt)<=12000):print('E_PROMPT',file=sys.stderr);return 2
 old=existing(task)
 if old is not None:
  try: out=export_verified(task,old)
  except Exception as e: print(f'E_EXPORT:{type(e).__name__}:{e}',file=sys.stderr);return 2
  print(json.dumps(out));return 0
 cmd=[RUNUSER,'-u','kopiko','--',XVFB,'-a',NODE,str(RUNNER),'--job-id',f'{task}-muxia','--profile','chatgpt-linux-a','--prompt',prompt,'--timeout-ms','600000']
 cp=subprocess.run(cmd,text=True,capture_output=True,timeout=720,check=False)
 if cp.returncode!=0:
  print((cp.stderr or cp.stdout)[-1600:],file=sys.stderr);return cp.returncode or 2
 cur=existing(task)
 if cur is None:print('E_RECEIPT_OR_ARTIFACT',file=sys.stderr);return 2
 try: out=export_verified(task,cur)
 except Exception as e: print(f'E_EXPORT:{type(e).__name__}:{e}',file=sys.stderr);return 2
 print(json.dumps(out));return 0
if __name__=='__main__':raise SystemExit(main())
