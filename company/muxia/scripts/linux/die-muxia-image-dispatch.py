#!/usr/bin/env python3
from __future__ import annotations
import json,os,pwd,re,subprocess,sys
from pathlib import Path
TASK_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$')
ROOT=Path('/var/lib/die/workspaces').resolve();NODE='/usr/local/bin/node';RUNNER=Path('/srv/die/company/factory-asset/bin/production_multi_cluster_dispatch.mjs');MUXIA_USER='kopiko'
def main()->int:
 if len(sys.argv)!=2 or not TASK_RE.fullmatch(sys.argv[1]):print('E_TASK_ID',file=sys.stderr);return 2
 if os.geteuid()!=pwd.getpwnam(MUXIA_USER).pw_uid:print('E_SERVICE_IDENTITY',file=sys.stderr);return 2
 task=sys.argv[1];w=(ROOT/task).resolve()
 try:w.relative_to(ROOT)
 except ValueError:print('E_WORKSPACE_ESCAPE',file=sys.stderr);return 2
 if not w.is_dir():print('E_WORKSPACE',file=sys.stderr);return 2
 cp=subprocess.run([NODE,str(RUNNER),'--task-id',task],text=True,capture_output=True,timeout=720,check=False)
 if cp.returncode!=0:
  print((cp.stderr or cp.stdout)[-2400:],file=sys.stderr);return cp.returncode or 2
 try:out=json.loads(cp.stdout.strip().splitlines()[-1])
 except Exception as e:print(f'E_MULTI_CLUSTER_RESULT:{type(e).__name__}',file=sys.stderr);return 2
 if out.get('status')!='SUCCEEDED' or out.get('export_artifact_sha256')!=out.get('sha256'):print('E_MULTI_CLUSTER_VERIFICATION',file=sys.stderr);return 2
 print(json.dumps(out));return 0
if __name__=='__main__':raise SystemExit(main())
