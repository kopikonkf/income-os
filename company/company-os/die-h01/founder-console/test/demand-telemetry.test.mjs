import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {buildDemandTelemetry} from '../demand_telemetry.mjs';

async function writeJson(file,value){await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,JSON.stringify(value));}

async function fixture({zero=false}={}){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'h01-141a-demand-'));
 const day='2026-09-14',cycleId=zero?'H01-DCYCLE-ZERO':'H01-DCYCLE-LIVE';
 const dayRoot=path.join(root,'demand-intelligence','daily',day),cycleRoot=path.join(dayRoot,cycleId);
 const materializationPath=path.join(cycleRoot,'demand-signal-ranking.v1.json');
 const selectorPath=path.join(cycleRoot,'daily-selector.frozen.json');
 const cyclePath=path.join(cycleRoot,'cycle.receipt.json');
 const refreshPath=path.join(dayRoot,'refresh-attempts','H01-DREFRESH-TEST.json');
 const records=zero?[
  {queue_item_id:'Q1',rank_state:'UNRANKED',rank_score:null,confidence:'NONE',signal_state:'NO_EVIDENCE',evidence_refs:[]},
  {queue_item_id:'Q2',rank_state:'UNRANKED',rank_score:null,confidence:'NONE',signal_state:'NO_EVIDENCE',evidence_refs:[]}
 ]:[
  {queue_item_id:'Q1',rank_state:'RANKED',rank_score:.8,confidence:'MEDIUM',signal_state:'PARTIAL',evidence_refs:[{evidence_id:'E1'}]},
  {queue_item_id:'Q2',rank_state:'RANKED',rank_score:.2,confidence:'LOW',signal_state:'PARTIAL',evidence_refs:[{evidence_id:'E2'}]},
  {queue_item_id:'Q3',rank_state:'UNRANKED',rank_score:null,confidence:'NONE',signal_state:'NO_EVIDENCE',evidence_refs:[]}
 ];
 await writeJson(materializationPath,{records,explanations:records.map((r,i)=>({queue_item_id:r.queue_item_id,canonical_name:['food','cat','pie'][i]}))});
 const items=zero?[{selection_reason:'SOURCE_ORDER_FALLBACK'},{selection_reason:'SOURCE_ORDER_FALLBACK'}]:[{selection_reason:'EVIDENCE_RANKED',queue_item_id:'Q1',canonical_name:'food',priority_rank:1,priority_score:.9,priority_components:{confidence:.6,evidence_ids:['E1']}},{selection_reason:'SOURCE_ORDER_FALLBACK',queue_item_id:'Q3',canonical_name:'pie'}];
 await writeJson(selectorPath,{items,evidence:{no_evidence_policy:'SOURCE_ORDER_FALLBACK'}});
 const ranked=zero?0:2,unranked=zero?2:1,evidenceCount=zero?0:2,fallback=zero?2:1;
 await writeJson(cyclePath,{day_key:day,cycle_id:cycleId,evidence:{record_count:evidenceCount,refs:zero?[]:[{connector_id:'123rf_trending_search_v1'},{connector_id:'wikimedia_pageviews_v1'}]},queue:{row_count:records.length},materialization:{ranked_count:ranked,unranked_count:unranked,path:materializationPath},selector:{selected:2,ranked_selected:zero?0:1,fallback_selected:fallback,path:selectorPath,selection_id:'SEL-1'},policy:{no_evidence_selector_policy:'SOURCE_ORDER_FALLBACK'},authority:{production_authorized:false,submission_authorized:false,publication_authorized:false,spend_authorized:false}});
 const sourceResults=zero?[]:[
  {source:'123rf_trending_search_v1',status:'CACHE_HIT_FRESH',acquisition_id:'H01-ACQ-AAAAAAAAAAAAAAAAAAAAAAAA',evidence_ids:['E1'],error:null},
  {source:'google_ads_keyword_historical_v1',status:'DEGRADED_AUTH_REQUIRED',acquisition_id:'H01-ACQ-BBBBBBBBBBBBBBBBBBBBBBBB',evidence_ids:[],error:{code:'E_AUTH_CONTEXT_REQUIRED'}}
 ];
 await writeJson(refreshPath,{attempt_id:'H01-DREFRESH-TEST',status:zero?'PASS':'PASS_WITH_DEGRADED_SOURCES',source_results:sourceResults});
 await writeJson(path.join(dayRoot,'latest.json'),{day_key:day,cycle_id:cycleId,cycle_receipt:cyclePath,refresh_attempt_receipt:refreshPath,selection_id:'SEL-1'});
 if(!zero){
  await writeJson(path.join(root,'demand-intelligence','signals','sources','123rf_trending_search_v1','queries','q1','acquisitions','H01-ACQ-AAAAAAAAAAAAAAAAAAAAAAAA.json'),{acquisition_id:'H01-ACQ-AAAAAAAAAAAAAAAAAAAAAAAA',source_id:'123rf_trending_search_v1',effective_freshness:'FRESH',retrieved_at:'2026-09-14T10:00:00Z'});
  await writeJson(path.join(root,'demand-intelligence','signals','sources','google_ads_keyword_historical_v1','queries','q2','acquisitions','H01-ACQ-BBBBBBBBBBBBBBBBBBBBBBBB.json'),{acquisition_id:'H01-ACQ-BBBBBBBBBBBBBBBBBBBBBBBB',source_id:'google_ads_keyword_historical_v1',effective_freshness:'UNKNOWN',retrieved_at:'2026-09-14T10:01:00Z'});
 }
 return root;
}

test('live daily state projects all H01-141A telemetry without mutation',async()=>{const root=await fixture();try{const d=await buildDemandTelemetry({dataRoot:root});assert.equal(d.available,true);assert.equal(d.state,'EVIDENCE_PRESENT');assert.equal(d.read_only,true);assert.equal(d.mutation,false);assert.deepEqual(d.queue_coverage,{queue_items:3,materialized_records:3,materialized_pct:100,ranked_count:2,unranked_count:1,ranked_pct:66.6667});assert.deepEqual(d.confidence_distribution,{MEDIUM:1,LOW:1,NONE:1});assert.equal(d.top_ranked_nouns[0].canonical_name,'food');assert.equal(d.top_ranked_nouns.length,1);assert.equal(d.top_ranked_nouns[0].rank,1);assert.equal(d.top_ranked_nouns[0].priority_score,.9);assert.deepEqual(d.daily_selection.reason_distribution,{EVIDENCE_RANKED:1,SOURCE_ORDER_FALLBACK:1});assert.equal(d.fallback.state,'ACTIVE');assert.equal(d.zero_evidence,false);assert.equal(d.source_health[0].freshness,'FRESH');assert.equal(d.source_health[1].health,'DEGRADED');assert.equal(d.last_refresh.observed_at,'2026-09-14T10:01:00Z');assert.equal(d.last_refresh.basis,'SOURCE_ACQUISITION_RECEIPT');assert.equal(d.evidence.record_count,2)}finally{await fs.rm(root,{recursive:true,force:true})}});

test('zero evidence state is explicit and fallback remains visible',async()=>{const root=await fixture({zero:true});try{const d=await buildDemandTelemetry({dataRoot:root});assert.equal(d.available,true);assert.equal(d.state,'ZERO_EVIDENCE');assert.equal(d.zero_evidence,true);assert.equal(d.queue_coverage.ranked_count,0);assert.equal(d.queue_coverage.unranked_count,2);assert.deepEqual(d.confidence_distribution,{NONE:2});assert.equal(d.fallback.state,'ACTIVE');assert.equal(d.fallback.selected,2);assert.equal(d.fallback.explicit_reason,'SOURCE_ORDER_FALLBACK');assert.deepEqual(d.daily_selection.reason_distribution,{SOURCE_ORDER_FALLBACK:2})}finally{await fs.rm(root,{recursive:true,force:true})}});

test('missing daily state fails soft as a read model',async()=>{const root=await fs.mkdtemp(path.join(os.tmpdir(),'h01-141a-empty-'));try{const d=await buildDemandTelemetry({dataRoot:root});assert.equal(d.available,false);assert.equal(d.state,'NO_DAILY_STATE');assert.equal(d.zero_evidence,true);assert.equal(d.read_only,true);assert.equal(d.mutation,false)}finally{await fs.rm(root,{recursive:true,force:true})}});
