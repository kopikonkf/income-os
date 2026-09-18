#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, fnmatch, grp, os, pwd, stat, subprocess
from pathlib import Path

ROOTS=[Path('/var/lib/die'),Path('/srv/die'),Path('/opt/die')]
DIRS=[
 Path('/var/lib/die/hermes/income-operator/pending_messages'),
 Path('/var/lib/die/hermes/.local/state/tirith/sessions'),
]
FILE_GLOBS=[
 '/var/lib/die/workspaces/*/factory-v2/postproduction-state.json',
 '/var/lib/die/workspaces/*/factory-v2/derivatives/*.metadata.*',
 '/var/lib/die/workspaces/*/muxia-proof-root/state/receipts/*.json',
 '/var/lib/die/workspaces/*/muxia-proof-root/jobs/*.json',
 '/var/lib/die/hermes/income-operator/cron/output/*/*.md',
 '/var/lib/die/hermes/income-operator/cron/ticker_heartbeat',
 '/var/lib/die/hermes/income-operator/cron/ticker_last_success',
 '/var/lib/die/state/factory-asset-canaries/**/*',
 '/var/lib/die/state/fa319-acceptance-*/workspaces/*/factory-v2/postproduction-state.json',
 '/var/lib/die/state/fa319-acceptance-*/workspaces/*/factory-v2/derivatives/*.metadata.*',
]
ROOT_EXEC_GLOB='/var/lib/die/state/*/rollback.sh'
ACTIVE_TOKENS=('production_runtime_tick.py','production_multi_cluster_dispatch.mjs','job_scoped_cluster_runtime.mjs')
BROWSER_MARKERS=(
 '/var/lib/die/executive/browser-profile',
 '/var/lib/die/division01/browser-profile',
 '/var/lib/muxia/profiles/chatgpt-linux-a/browser',
 '/var/lib/muxia/profiles/web-ai-cluster-b/browser',
)

def now():
 return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def proc_cmdlines():
 for d in Path('/proc').glob('[0-9]*'):
  try:
   parts=(d/'cmdline').read_bytes().split(b'\0')
   text=' '.join(x.decode('utf-8','replace') for x in parts if x)
  except (OSError,PermissionError):
   continue
  if text: yield int(d.name),text

def active_conflicts():
 out=[]
 me=os.getpid()
 for pid,text in proc_cmdlines():
  if pid==me: continue
  if any(t in text for t in ACTIVE_TOKENS) or any(m in text for m in BROWSER_MARKERS):
   out.append((pid,text[:500]))
 return out

def matching_files():
 seen=set()
 for root in ROOTS:
  if not root.exists(): continue
  for base,dirs,files in os.walk(root,followlinks=False):
   for name in files:
    p=Path(base)/name; s=str(p)
    if any(fnmatch.fnmatch(s,g) for g in FILE_GLOBS):
     if p not in seen: seen.add(p); yield p,0o640,'operational'
    elif fnmatch.fnmatch(s,ROOT_EXEC_GLOB):
     if p not in seen: seen.add(p); yield p,0o750,'root-executable'

def snapshot(paths,root):
 root.mkdir(parents=True,exist_ok=False)
 f=(root/'modes.tsv').open('w',encoding='utf-8')
 f.write('mode\tuid\tgid\tpath\n')
 for p in sorted(set(paths),key=str):
  if not p.exists() and not p.is_symlink(): continue
  st=p.lstat(); f.write(f'{stat.S_IMODE(st.st_mode):04o}\t{st.st_uid}\t{st.st_gid}\t{p}\n')
 f.close()

def apply():
 if os.geteuid()!=0: raise SystemExit('E_ROOT_REQUIRED')
 conflicts=active_conflicts()
 if conflicts:
  for pid,text in conflicts: print(f'E_ACTIVE_CONFLICT pid={pid} cmd={text}',file=os.sys.stderr)
  raise SystemExit(73)
 kopiko=pwd.getpwnam('kopiko'); runtime=grp.getgrnam('die-runtime')
 if runtime.gr_gid not in os.getgrouplist('kopiko',kopiko.pw_gid):
  raise SystemExit('E_KOPIKO_NOT_DIE_RUNTIME')
 files=list(matching_files()); touched=DIRS+[x[0] for x in files]
 rb=Path('/var/lib/die/rollback/FA-340')/now(); snapshot(touched,rb)
 for p in DIRS:
  if not p.exists(): continue
  st=p.stat()
  if pwd.getpwuid(st.st_uid).pw_name!='die-hermes' or grp.getgrgid(st.st_gid).gr_name!='die-runtime':
   raise SystemExit(f'E_RUNTIME_DIR_OWNER:{p}')
  os.chmod(p,0o2750)
 for p,mode,kind in files:
  if not p.exists(): continue
  st=p.stat()
  if kind=='operational':
   os.chown(p,-1,runtime.gr_gid)
  else:
   os.chown(p,-1,runtime.gr_gid)
  os.chmod(p,mode)
 print(f'FA340_APPLY=PASS rollback={rb} files={len(files)} dirs={sum(p.exists() for p in DIRS)}')

def audit():
 denied=set(); errors=[]
 for root in ROOTS:
  cp=subprocess.run(['runuser','-u','kopiko','--','find',str(root),'-xdev','-type','d','(','!','-readable','-o','!','-executable',')','-print'],text=True,capture_output=True)
  denied.update(x.strip() for x in cp.stdout.splitlines() if x.strip())
  for line in cp.stderr.splitlines():
   if 'Permission denied' in line:
    errors.append(line)
 operational_unreadable=[]
 for p,mode,kind in matching_files():
  if not p.exists(): continue
  cp=subprocess.run(['runuser','-u','kopiko','--','test','-r',str(p)])
  if cp.returncode!=0: operational_unreadable.append(str(p))
 print(f'FA340_AUDIT directory_denials={len(denied)} find_permission_errors={len(errors)} operational_unreadable={len(operational_unreadable)}')
 for x in sorted(denied)[:100]: print(x)
 for x in errors[:100]: print(x)
 for x in operational_unreadable[:100]: print(x)
 return 0 if not denied and not errors and not operational_unreadable else 4

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['audit','apply']); a=ap.parse_args()
 if a.action=='apply': apply(); return audit()
 return audit()
if __name__=='__main__': raise SystemExit(main())
