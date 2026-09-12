#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve();ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT/'company/factory-asset/lib'))
from rights_signal_gate import evaluate_rights_signals

def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',required=True);ns=ap.parse_args();w=Path(ns.workspace)
 det=json.loads((w/'visual-rights-detector.json').read_text());post=json.loads((w/'postproduction/postproduction.receipt.json').read_text());obs=det['observation'];master=w/'postproduction/preview.jpg';sha=next(a['sha256'] for a in post['artifacts'] if a['path']=='preview.jpg')
 rights=evaluate_rights_signals(master_path=master,expected_sha256=sha,observation=obs);source_ip=det['classification'].get('source_ip') or {};rights['source_ip']=source_ip
 if source_ip.get('disposition')=='STRONG_RISK': rights['blocking_signals'].append({'signal':'SOURCE_IP_STRONG_RISK','detector':'source_ip','detail':str(source_ip.get('risk_score'))});rights['result']='BLOCK';rights['signal_gate_pass']=False
 elif source_ip.get('disposition')=='REVIEW': rights['review_signals'].append({'signal':'SOURCE_IP_REVIEW','detector':'source_ip','detail':str(source_ip.get('risk_score'))});rights['result']='REVIEW_REQUIRED' if rights['result']=='PASS' else rights['result'];rights['signal_gate_pass']=False
 dump(w/'rights-signal.json',rights)
 rec=json.loads((w/'asset-receipt.json').read_text());rec['rights']=rights['result'];rec['rights_signal_gate']=rights['result'];rec['visual_rights_self_test']=det['runtime']['self_test_result'];rec['status']='ACCEPTED_SEMANTIC_MASTER' if rights['result'] in {'PASS','REVIEW_REQUIRED'} else 'BLOCKED_RIGHTS';rec['submission_eligible']=False;dump(w/'asset-receipt.json',rec)
 print(json.dumps({'status':rec['status'],'rights':rights['result'],'blockers':rights['blocking_signals'],'review':rights['review_signals']}))
if __name__=='__main__':main()
