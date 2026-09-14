import {readFile,readdir,stat} from 'node:fs/promises';
import path from 'node:path';

const DAY=/^\d{4}-\d{2}-\d{2}$/;
const SOURCE=/^[a-z0-9._-]+$/;
const ACQ=/^H01-ACQ-[0-9A-F]{24}$/;
const derivedCache=new Map();

async function jsonFile(file){try{return JSON.parse(await readFile(file,'utf8'))}catch{return null}}
async function dirs(root){try{return (await readdir(root,{withFileTypes:true})).filter(x=>x.isDirectory()).map(x=>x.name)}catch{return []}}
function inside(root,candidate){const r=path.resolve(root),c=path.resolve(candidate);return c===r||c.startsWith(r+path.sep)}
function pct(n,d){return d>0?Number(((n/d)*100).toFixed(4)):0}
function freshnessFromStatus(status){if(status==='ACQUIRED'||status==='CACHE_HIT_FRESH')return 'FRESH';if(status==='DEGRADED_STALE_CACHE')return 'STALE';return 'UNKNOWN'}
function healthFromStatus(status){return String(status||'UNKNOWN').startsWith('DEGRADED_')?'DEGRADED':(['ACQUIRED','CACHE_HIT_FRESH'].includes(status)?'HEALTHY':'UNKNOWN')}
function countBy(rows,key){const out={};for(const row of rows||[]){const value=String(row?.[key]??'UNKNOWN');out[value]=(out[value]||0)+1}return out}

async function latestDaily(dataRoot){
 const dailyRoot=path.join(dataRoot,'demand-intelligence','daily');
 const days=(await dirs(dailyRoot)).filter(x=>DAY.test(x)).sort().reverse();
 for(const day of days){const latestPath=path.join(dailyRoot,day,'latest.json');const latest=await jsonFile(latestPath);if(latest?.cycle_receipt&&latest?.refresh_attempt_receipt)return {dailyRoot,dayRoot:path.join(dailyRoot,day),latestPath,latest}}
 return null;
}

async function acquisition(dataRoot,source,id){
 if(!SOURCE.test(source||'')||!ACQ.test(id||''))return null;
 const root=path.join(dataRoot,'demand-intelligence','signals','sources',source,'queries');
 for(const query of (await dirs(root)).slice(0,256)){
  const p=path.join(root,query,'acquisitions',`${id}.json`);const row=await jsonFile(p);if(row?.acquisition_id===id&&row?.source_id===source)return row;
 }
 return null;
}

async function deriveMaterialization(file){
 if(derivedCache.has(file))return derivedCache.get(file);
 const data=await jsonFile(file);if(!data)return null;
 const records=Array.isArray(data.records)?data.records:[];
 const confidence_distribution=countBy(records,'confidence');
 const result={confidence_distribution,record_count:records.length,signal_state_distribution:countBy(records,'signal_state')};
 derivedCache.set(file,result);return result;
}

export async function buildDemandTelemetry({dataRoot='/var/lib/die/h01'}={}){
 const state=await latestDaily(dataRoot);
 if(!state)return {schema:'die.h01.founder-console.demand-telemetry.v1',available:false,state:'NO_DAILY_STATE',read_only:true,zero_evidence:true,fallback:{state:'UNKNOWN',policy:'SOURCE_ORDER_FALLBACK'},mutation:false};
 const {dailyRoot,dayRoot,latestPath,latest}=state;
 const cyclePath=String(latest.cycle_receipt||''),refreshPath=String(latest.refresh_attempt_receipt||'');
 if(!inside(dailyRoot,cyclePath)||!inside(dailyRoot,refreshPath))return {schema:'die.h01.founder-console.demand-telemetry.v1',available:false,state:'INVALID_DAILY_POINTER',read_only:true,zero_evidence:true,fallback:{state:'UNKNOWN',policy:'SOURCE_ORDER_FALLBACK'},mutation:false};
 const cycle=await jsonFile(cyclePath),refresh=await jsonFile(refreshPath);
 if(!cycle||!refresh)return {schema:'die.h01.founder-console.demand-telemetry.v1',available:false,state:'INCOMPLETE_DAILY_STATE',read_only:true,zero_evidence:true,fallback:{state:'UNKNOWN',policy:'SOURCE_ORDER_FALLBACK'},mutation:false};
 const materializationPath=String(cycle.materialization?.path||''),selectorPath=String(cycle.selector?.path||'');
 if(!inside(dayRoot,materializationPath)||!inside(dayRoot,selectorPath))return {schema:'die.h01.founder-console.demand-telemetry.v1',available:false,state:'INVALID_ARTIFACT_POINTER',read_only:true,zero_evidence:true,fallback:{state:'UNKNOWN',policy:'SOURCE_ORDER_FALLBACK'},mutation:false};
 const [derived,selector]=await Promise.all([deriveMaterialization(materializationPath),jsonFile(selectorPath)]);
 if(!derived||!selector)return {schema:'die.h01.founder-console.demand-telemetry.v1',available:false,state:'INCOMPLETE_CYCLE_ARTIFACTS',read_only:true,zero_evidence:true,fallback:{state:'UNKNOWN',policy:'SOURCE_ORDER_FALLBACK'},mutation:false};
 const source_health=[];
 for(const row of refresh.source_results||[]){
  const acq=await acquisition(dataRoot,String(row.source||''),String(row.acquisition_id||''));
  source_health.push({
   source:row.source,status:row.status||'UNKNOWN',health:healthFromStatus(row.status),
   freshness:acq?.effective_freshness||freshnessFromStatus(row.status),retrieved_at:acq?.retrieved_at||null,
   evidence_count:Array.isArray(row.evidence_ids)?row.evidence_ids.length:0,error_code:row.error?.code||row.error?.type||null
  });
 }
 const refreshTimes=source_health.map(x=>x.retrieved_at).filter(Boolean).sort();
 let refreshObservedAt=refreshTimes.at(-1)||null,basis=refreshObservedAt?'SOURCE_ACQUISITION_RECEIPT':null;
 if(!refreshObservedAt){try{refreshObservedAt=(await stat(refreshPath)).mtime.toISOString();basis='REFRESH_RECEIPT_MTIME'}catch{}}
 const queueItems=Number(cycle.queue?.row_count)||0,ranked=Number(cycle.materialization?.ranked_count)||0,unranked=Number(cycle.materialization?.unranked_count)||0,materialized=ranked+unranked;
 const evidenceCount=Number(cycle.evidence?.record_count)||0,fallbackSelected=Number(cycle.selector?.fallback_selected)||0,rankedSelected=Number(cycle.selector?.ranked_selected)||0;
 const selectorItems=Array.isArray(selector.items)?selector.items:[];
 const reason_distribution=countBy(selectorItems,'selection_reason');
 const top_ranked_nouns=selectorItems.filter(x=>x?.selection_reason==='EVIDENCE_RANKED').sort((a,b)=>(Number(a.priority_rank)||Number.MAX_SAFE_INTEGER)-(Number(b.priority_rank)||Number.MAX_SAFE_INTEGER)||(Number(a.batch_position)||0)-(Number(b.batch_position)||0)).slice(0,10).map(x=>({
  rank:x.priority_rank??null,queue_item_id:x.queue_item_id,canonical_name:x.canonical_name??null,
  priority_score:x.priority_score??null,confidence:x.priority_components?.confidence??null,
  evidence_count:Array.isArray(x.priority_components?.evidence_ids)?x.priority_components.evidence_ids.length:0,selection_reason:x.selection_reason
 }));
 const connector_distribution={};for(const ref of cycle.evidence?.refs||[]){const k=String(ref.connector_id||'UNKNOWN');connector_distribution[k]=(connector_distribution[k]||0)+1}
 const zeroEvidence=evidenceCount===0;
 const evidenceState=zeroEvidence?'ZERO_EVIDENCE':(ranked===0?'EVIDENCE_NO_RANKED_MATCH':'EVIDENCE_PRESENT');
 return {
  schema:'die.h01.founder-console.demand-telemetry.v1',available:true,state:evidenceState,read_only:true,mutation:false,
  day_key:cycle.day_key||latest.day_key||null,cycle_id:cycle.cycle_id||latest.cycle_id||null,selection_id:cycle.selector?.selection_id||latest.selection_id||null,
  source_health,
  evidence:{record_count:evidenceCount,connector_distribution},
  queue_coverage:{queue_items:queueItems,materialized_records:materialized,materialized_pct:pct(materialized,queueItems),ranked_count:ranked,unranked_count:unranked,ranked_pct:pct(ranked,queueItems)},
  confidence_distribution:derived.confidence_distribution,
  signal_state_distribution:derived.signal_state_distribution,
  top_ranked_nouns,
  daily_selection:{selected:Number(cycle.selector?.selected)||0,ranked_selected:rankedSelected,fallback_selected:fallbackSelected,reason_distribution},
  zero_evidence:zeroEvidence,
  fallback:{state:fallbackSelected>0?'ACTIVE':'NOT_USED',policy:cycle.policy?.no_evidence_selector_policy||selector.evidence?.no_evidence_policy||'SOURCE_ORDER_FALLBACK',selected:fallbackSelected,explicit_reason:'SOURCE_ORDER_FALLBACK'},
  last_refresh:{observed_at:refreshObservedAt,basis,attempt_id:refresh.attempt_id||null,status:refresh.status||'UNKNOWN'},
  provenance:{latest_pointer:latestPath,cycle_receipt:cyclePath,refresh_attempt_receipt:refreshPath,materialization:materializationPath,selector:selectorPath},
  authority:cycle.authority||{production_authorized:false,submission_authorized:false,publication_authorized:false,spend_authorized:false}
 };
}
