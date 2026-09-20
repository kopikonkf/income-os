#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
def read_done(root:Path):
 p=root/"state"/"vault-done.jsonl"; names=set()
 if not p.is_file(): return names
 for line in p.read_text(encoding="utf-8").splitlines():
  try:
   x=json.loads(line)
   if x.get("status")=="BACKUP_VERIFIED" and x.get("archive_path"): names.add(Path(x["archive_path"]).name)
  except Exception: pass
 return names
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",required=True,type=Path);ap.add_argument("--apply",action="store_true");ap.add_argument("--tmp-age-hours",type=int,default=24);a=ap.parse_args()
 root=a.root; now=time.time(); verified=read_done(root); victims=[]
 arch=root/"vault"/"archives"
 if arch.is_dir():
  for p in arch.glob("*.zip"):
   if p.name in verified: victims.append(("verified_archive_zip",p))
 for d in [root/"vault"/"restores",root/"state"]:
  if d.is_dir():
   for p in d.rglob("*"):
    if not p.is_file(): continue
    n=p.name.lower()
    if (".tmp-" in n or n.endswith(".tmp") or n.endswith(".partial")) and now-p.stat().st_mtime>=a.tmp_age_hours*3600: victims.append(("stale_temp",p))
 for p in (root/"state").glob("*browser*.log") if (root/"state").is_dir() else []:
  if p.is_file() and p.stat().st_size>20*1024*1024: victims.append(("rotate_browser_log",p))
 freed=0; actions=[]
 for kind,p in victims:
  size=p.stat().st_size if p.exists() else 0; actions.append({"kind":kind,"path":str(p),"bytes":size})
  if a.apply and p.exists():
   if kind=="rotate_browser_log":
    bak=p.with_suffix(p.suffix+".1")
    try: bak.unlink()
    except FileNotFoundError: pass
    os.replace(p,bak);p.touch()
   else: p.unlink()
   freed+=size
 print(json.dumps({"status":"APPLIED" if a.apply else "DRY_RUN","root":str(root),"actions":actions,"bytes_freed":freed,"workspace_master_retention":"PRESERVE","raw_source_retention":"PRESERVE"}))
if __name__=="__main__":main()
