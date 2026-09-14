#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve(); H01=HERE.parents[1]
sys.path.insert(0,str(H01/"lib"))
from phase0_production_intent import build_intents,file_sha256,load_queue,persist_intents
DEFAULT_QUEUE=Path("/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl")
DEFAULT_OUTPUT=Path("/var/lib/die/h01/production-intent/phase0")
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--selector",required=True); ap.add_argument("--demand",required=True); ap.add_argument("--queue",default=str(DEFAULT_QUEUE)); ap.add_argument("--cycle-id",default=""); ap.add_argument("--output-root",default=str(DEFAULT_OUTPUT)); ns=ap.parse_args()
 sp,dp,qp=Path(ns.selector),Path(ns.demand),Path(ns.queue)
 selector=json.loads(sp.read_text()); demand=json.loads(dp.read_text()); queue=load_queue(qp); cycle_id=ns.cycle_id or sp.parent.name
 intents=build_intents(selector=selector,materialization=demand,queue_rows=queue,cycle_id=cycle_id,selector_manifest_sha256=file_sha256(sp),demand_materialization_sha256=file_sha256(dp))
 persisted=persist_intents(intents=intents,output_root=Path(ns.output_root),queue_sha256=file_sha256(qp)); m=persisted["manifest"]
 print(json.dumps({"status":"PASS","manifest_id":m["manifest_id"],"cycle_id":m["cycle_id"],"selected_count":m["selected_count"],"evidence_ranked_count":m["evidence_ranked_count"],"fallback_count":m["fallback_count"],"manifest_path":persisted["manifest_path"]},sort_keys=True))
 return 0
if __name__=="__main__": raise SystemExit(main())
