#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve();ROOT=HERE.parents[3];MOD=ROOT/'company/factory-asset/lib/binary_metadata.py';QA=ROOT/'company/factory-asset/lib/derivative_qa.py'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
bm=load('fa141_binary_metadata_cli',MOD);qa=load('fa141_derivative_qa_cli',QA)
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--metadata',required=True);ap.add_argument('--output',required=True);ap.add_argument('--receipt',required=True);a=ap.parse_args()
 src=Path(a.source);meta=json.loads(Path(a.metadata).read_text(encoding='utf-8'));out=Path(a.output);r=bm.inject_jpeg(source_path=src,output_path=out,metadata=meta);rb=bm.readback_jpeg(out)
 from PIL import Image
 with Image.open(src) as im:im.load();dims=im.size
 q=qa.inspect_derivative(out,expected_format='JPEG',expected_dimensions=dims,expected_alpha='ABSENT',expected_sha256=r['output_sha256'])
 if q['result']!='PASS' or rb['xmp']!=r['fields'] or rb['iptc']!=r['fields']:return 2
 rec={'schema':'factory-asset.fa141-binary-metadata-canary.v1','result':'PASS','source_sha256':r['source_sha256'],'output_sha256':r['output_sha256'],'dimensions':list(dims),'readback':{'xmp':'PASS','iptc':'PASS','fields':r['fields']},'technical_qa':q,'source_immutable':r['immutable_source_preserved'],'platform_form_ai_disclosure_still_required':True}
 Path(a.receipt).write_text(json.dumps(rec,indent=2)+'\n',encoding='utf-8');print(json.dumps(rec,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
