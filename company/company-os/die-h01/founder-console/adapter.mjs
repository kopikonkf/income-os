import {readFile, readdir, stat} from 'node:fs/promises';
import path from 'node:path';
import {buildProviderBridgeReadModel} from './byok_bridge.mjs';

const LEGACY_JSON_PATHS=new Set(['/api/production-acceptance','/api/queue/jobs','/api/providers','/api/qc-gallery','/api/telemetry']);
const receiptIds=['H01-130-demand-signal-engine.receipt.json','H01-131-market-signal-connectors.receipt.json','H01-132-human-atlas-demand-join.receipt.json','H01-133-evidence-prioritization.receipt.json'];

async function jsonFile(file,fallback={}){try{return JSON.parse(await readFile(file,'utf8'))}catch{return fallback}}
async function legacyJson(base,pathname){
 if(!LEGACY_JSON_PATHS.has(pathname))throw new Error('E_LEGACY_PATH_NOT_ALLOWLISTED');
 try{const r=await fetch(new URL(pathname,base),{method:'GET',signal:AbortSignal.timeout(2500),headers:{accept:'application/json'}}); if(!r.ok)return {available:false,status:r.status,data:null}; return {available:true,status:r.status,data:await r.json()}}catch{return {available:false,status:null,data:null}}
}
async function countDirs(root){try{return (await readdir(root,{withFileTypes:true})).filter(x=>x.isDirectory()).length}catch{return 0}}
async function submissionReady(root){
 const out={marketplaces:{},total_assets:0};
 try{for(const m of await readdir(root,{withFileTypes:true})){if(!m.isDirectory())continue;const n=await countDirs(path.join(root,m.name));out.marketplaces[m.name]=n;out.total_assets+=n}}catch{}
 return out;
}
async function taskReadModel(repoRoot){
 const graph=await jsonFile(path.join(repoRoot,'company/company-os/die-h01/die-h01-task-graph.v1.json'),{tasks:[]});
 const counts={}; for(const t of graph.tasks||[])counts[t.status]=(counts[t.status]||0)+1;
 return {authority:'MISSION_CONTROL',source:'canonical-git-task-graph',counts,tasks:(graph.tasks||[]).map(t=>({id:t.id,title:t.title,status:t.status,track:t.track,depends_on:t.depends_on||[]}))};
}
async function demandReadModel(repoRoot){
 const base=path.join(repoRoot,'company/company-os/die-h01/receipts'); const receipts={};
 for(const name of receiptIds)receipts[name]=await jsonFile(path.join(base,name),{status:'UNAVAILABLE'});
 return {mode:'NON_BLOCKING_PRIORITY_OVERLAY',object_atlas_validity_effect:'NONE',standalone_production_blocking_effect:'NONE',receipts};
}
async function providerReadModel(repoRoot,legacyBase){
 const runtime=await jsonFile(path.join(repoRoot,'company/company-os/die-h01/runtime/h01-byok-api-provider-bridge.v1.json'),{providers:[]});
 const legacy=await legacyJson(legacyBase,'/api/providers');
 return {browser_native_primary:true,legacy_provider_inventory:legacy,api_bridge:buildProviderBridgeReadModel(runtime)};
}
export function createReadModels({repoRoot,dataRoot='/var/lib/die/h01',legacyBase='http://127.0.0.1:8876'}){
 return {
  async overview(){const [tasks,submission,production,providers,qc]=await Promise.all([taskReadModel(repoRoot),submissionReady(path.join(dataRoot,'submission-ready')),legacyJson(legacyBase,'/api/production-acceptance'),providerReadModel(repoRoot,legacyBase),legacyJson(legacyBase,'/api/qc-gallery')]);return {mission_control:'GLOBAL_BRAIN',h01_runtime:'EXECUTION_PLANE',legacy_8876:production.available?'AVAILABLE':'UNAVAILABLE',task_counts:tasks.counts,submission_ready_assets:submission.total_assets,qc_assets:qc.data?.asset_count??0,api_provider_count:providers.api_bridge.provider_count};},
  async production(){return {acceptance:await legacyJson(legacyBase,'/api/production-acceptance'),queue:await legacyJson(legacyBase,'/api/queue/jobs'),mutation:false};},
  async providers(){return providerReadModel(repoRoot,legacyBase)},
  async qc(){const q=await legacyJson(legacyBase,'/api/qc-gallery');return {...q,proxied_by:'FOUNDER_CONSOLE_V1'};},
  async submission(){return {source_root:path.join(dataRoot,'submission-ready'),...(await submissionReady(path.join(dataRoot,'submission-ready'))),submission_action:'NONE',publication_action:'NONE'};},
  async demand(){return demandReadModel(repoRoot)},
  async tasks(){return taskReadModel(repoRoot)},
  async health(){const telemetry=await legacyJson(legacyBase,'/api/telemetry');return {console:'PASS',legacy_8876:telemetry.available?'PASS':'UNAVAILABLE',legacy_telemetry:telemetry.available?telemetry.data:null,mission_control_authority:'EXTERNAL_GLOBAL',cutover:false};},
  async settings(){return {console_mode:'SHADOW_V1',legacy_8876_preserved:true,write_actions_enabled:false,provider_secrets_exposed:false,mission_control_authority:'EXTERNAL_GLOBAL'};}
 };
}

export async function proxyQcImage(legacyBase,url){
 const id=url.searchParams.get('id')||''; const variant=url.searchParams.get('variant')||'thumb';
 if(!/^[a-f0-9]{24}$/.test(id)||!['thumb','full'].includes(variant))return {status:400,headers:{'content-type':'application/json'},body:Buffer.from(JSON.stringify({error:'INVALID_QC_IMAGE_REQUEST'}))};
 try{const target=new URL('/api/qc-image',legacyBase);target.searchParams.set('id',id);target.searchParams.set('variant',variant);const r=await fetch(target,{method:'GET',signal:AbortSignal.timeout(4000)});return {status:r.status,headers:{'content-type':r.headers.get('content-type')||'application/octet-stream','cache-control':'no-store'},body:Buffer.from(await r.arrayBuffer())}}catch{return {status:503,headers:{'content-type':'application/json'},body:Buffer.from(JSON.stringify({error:'LEGACY_QC_UNAVAILABLE'}))}}
}
