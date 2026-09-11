from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'company/factory-asset'

def _load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
adapter=_load('cwvp_adapter',BASE/'lib/claude_native_svg_adapter.py')
pipeline=_load('cwvp_pipeline',BASE/'lib/native_svg_pipeline.py')

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def atomic_bytes(path:Path,data:bytes):path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(data);tmp.replace(path)
def atomic_json(path:Path,v:dict[str,Any]):atomic_bytes(path,(json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())

def postprocess(*,request:dict[str,Any],raw_response:str,output_dir:Path)->dict[str,Any]:
 adapter.validate_request(request)
 svg=adapter.normalize_svg_payload(raw_response)
 pkg=pipeline.package_svg_master(svg_text=svg,semantic_asset_id=request['semantic_asset_id'],blueprint_sha256=request['frozen_blueprint_sha256'],provider_prompt_sha256=request['provider_prompt_sha256'])
 output_dir.mkdir(parents=True,exist_ok=True)
 files={}
 mapping={'SVG':'master.svg','EPS':'master.eps','PNG':'preview.png','JPEG':'preview.jpg'}
 for fmt,name in mapping.items():
  data=pkg['bytes'][fmt];path=output_dir/name;atomic_bytes(path,data);files[fmt]={'path':str(path),'bytes':len(data),'sha256':sha_bytes(data)}
 receipt={'schema':'die.factory-asset.claude-web-native-vector-postprocess.v1','job_id':request['job_id'],'provider_id':'claude','producer_class':'NATIVE_VECTOR','asset_type':request['asset_type'],'semantic_asset_id':request['semantic_asset_id'],'frozen_blueprint_sha256':request['frozen_blueprint_sha256'],'provider_prompt_sha256':request['provider_prompt_sha256'],'native_svg':{'source_kind':'CLAUDE_WEB_TEXT_SVG','editable':True,'conversion_from_raster':False,'embedded_raster_only':False},'qa':pkg['package']['qa'],'master':pkg['package']['master'],'derivatives':pkg['package']['derivatives'],'semantic_asset_count':1,'files':files,'package_sha256':pkg['package']['package_sha256'],'technical_result':'PASS','next_state':'DERIVATIVES_READY','submission_authorized':False,'publication_authorized':False}
 atomic_json(output_dir/'postprocess.receipt.json',receipt);return receipt

def main(argv=None):
 ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--response',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args(argv)
 r=postprocess(request=json.loads(a.request.read_text()),raw_response=a.response.read_text(),output_dir=a.output_dir);print(json.dumps(r,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
