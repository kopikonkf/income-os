#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,venv
from pathlib import Path

def run(argv):
    cp=subprocess.run(argv,text=True,capture_output=True,check=False)
    if cp.returncode!=0:raise RuntimeError((cp.stderr or cp.stdout)[-3000:])
    return cp

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--venv',default='/opt/die/factory-asset/venv');ap.add_argument('--requirements',default='/srv/die/company/factory-asset/requirements-runtime.txt');ap.add_argument('--check-only',action='store_true');a=ap.parse_args()
    root=Path(a.venv);req=Path(a.requirements)
    if not req.is_file():raise RuntimeError(f'RUNTIME_REQUIREMENTS_MISSING:{req}')
    if not a.check_only:
        root.parent.mkdir(parents=True,exist_ok=True)
        if not (root/'bin/python').is_file():venv.EnvBuilder(with_pip=True,clear=False).create(root)
        run([str(root/'bin/python'),'-m','pip','install','--disable-pip-version-check','--requirement',str(req)])
    py=root/'bin/python'
    if not py.is_file():raise RuntimeError(f'FACTORY_RUNTIME_PYTHON_MISSING:{py}')
    code='import PIL,jsonschema,PyPDF2;print(PIL.__version__);print(jsonschema.__version__);print(PyPDF2.__version__)'
    cp=run([str(py),'-c',code]);versions=cp.stdout.strip().splitlines()
    print(json.dumps({'schema':'die.factory-asset.runtime-env.v1','status':'PASS','python':str(py),'requirements':str(req),'versions':{'Pillow':versions[0] if len(versions)>0 else None,'jsonschema':versions[1] if len(versions)>1 else None,'PyPDF2':versions[2] if len(versions)>2 else None}},sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())
