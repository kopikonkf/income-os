#!/usr/bin/env python3
from pathlib import Path
import argparse, grp, json, os

def verify(root:Path, required_group:str='die-runtime'):
 gid=grp.getgrnam(required_group).gr_gid; rows=[]; bad=[]
 for p in sorted(root.glob('*/qc/*')):
  if not p.is_file(): continue
  st=p.stat(); mode=st.st_mode & 0o777
  row={'path':str(p),'mode':format(mode,'04o'),'gid':st.st_gid,'bytes':st.st_size,'group_readable':bool(mode&0o040),'world_readable':bool(mode&0o004)}
  rows.append(row)
  if st.st_gid!=gid or not row['group_readable'] or row['world_readable']: bad.append(row)
 return {'schema':'die.factory-asset.founder-qc-delivery-verification.v1','result':'PASS' if not bad else 'FAIL','checked':len(rows),'failures':bad,'rows':rows}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--workspaces',type=Path,default=Path('/var/lib/die/workspaces'));a=ap.parse_args();r=verify(a.workspaces);print(json.dumps(r,indent=2));raise SystemExit(0 if r['result']=='PASS' else 2)
