from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def _load():
    path=ROOT/'company/factory-asset/lib/motion_qa.py'
    spec=importlib.util.spec_from_file_location('motion_qa_cli_impl',path)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod


def expected_from_contract(contract:dict)->dict:
    return {'container':contract['video']['container'],'codec':contract['video']['codec'],'pixel_format':contract['video']['pixel_format'],'width':contract['canvas']['width'],'height':contract['canvas']['height'],'fps':contract['fps'],'frame_count':contract['frame_count'],'duration_seconds':contract['duration_seconds'],'audio_policy':contract['audio']['policy']}

def main()->int:
    ap=argparse.ArgumentParser(description='Factory Asset motion QA inspector')
    ap.add_argument('--input',required=True); ap.add_argument('--composition-contract',required=True)
    ap.add_argument('--ffprobe',required=True); ap.add_argument('--ffmpeg',required=True)
    ap.add_argument('--marketplace'); ap.add_argument('--receipt')
    args=ap.parse_args(); m=_load()
    contract=json.loads(Path(args.composition_contract).read_text(encoding='utf-8'))
    expected=expected_from_contract(contract)
    result=m.inspect_motion(args.input,ffprobe_path=args.ffprobe,ffmpeg_path=args.ffmpeg,expected=expected)
    envelope={'schema':'die.factory-asset.motion-qa-cli.v1','input':str(Path(args.input).resolve()),'composition_id':contract['composition_id'],'expected':expected,'qa':result}
    if args.marketplace:
        registry=json.loads((ROOT/'company/factory-asset/registries/marketplace-delivery-profiles.v1.json').read_text(encoding='utf-8'))
        profile=next((p for p in registry['profiles'] if p['platform_id']==args.marketplace),None)
        if profile is None: raise SystemExit(f'unknown marketplace {args.marketplace}')
        envelope['marketplace']={'platform_id':args.marketplace,**m.marketplace_compatibility(marketplace_profile=profile,qa_result=result,expected=expected)}
    payload=json.dumps(envelope,indent=2)+'\n'
    if args.receipt: Path(args.receipt).write_text(payload,encoding='utf-8',newline='\n')
    print(payload,end='')
    return 0 if result['result']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())