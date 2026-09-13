import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {createApp} from '../server.mjs';

const paths=['overview','production','providers','qc/gallery','submission-ready','demand','tasks','system/health','settings'];
async function fixture(){
 const root=await mkdtemp(path.join(os.tmpdir(),'h01-141-')); const die=path.join(root,'company/company-os/die-h01'); await mkdir(path.join(die,'receipts'),{recursive:true});await mkdir(path.join(die,'runtime'),{recursive:true});
 await writeFile(path.join(die,'die-h01-task-graph.v1.json'),JSON.stringify({tasks:[{id:'H01-140',title:'spike',status:'DONE',track:'FOUNDER_CONSOLE',depends_on:[]},{id:'H01-141',title:'shell',status:'READY',track:'FOUNDER_CONSOLE',depends_on:['H01-140']}]}));
 for(const n of ['H01-130-demand-signal-engine.receipt.json','H01-131-market-signal-connectors.receipt.json','H01-132-human-atlas-demand-join.receipt.json','H01-133-evidence-prioritization.receipt.json'])await writeFile(path.join(die,'receipts',n),JSON.stringify({status:'PASS'}));
 await writeFile(path.join(die,'runtime/h01-byok-api-provider-bridge.v1.json'),JSON.stringify({providers:[]}));
 const data=path.join(root,'data');await mkdir(path.join(data,'submission-ready','adobe','A1'),{recursive:true});
 return {root,data};
}
async function legacy(){
 const seen=[]; const app=http.createServer((req,res)=>{seen.push([req.method,req.url]);res.setHeader('content-type','application/json');if(req.url.startsWith('/api/qc-image')){res.setHeader('content-type','image/webp');return res.end(Buffer.from([1,2,3]))}const bodies={'/api/production-acceptance':{result:'PASS'},'/api/queue/jobs':{jobs:[]},'/api/providers':{providers:[]},'/api/qc-gallery':{asset_count:1,source_counts:{H01_108_VECTOR_SOAK:1},items:[]},'/api/telemetry':{status:'PASS'}};if(!(req.url in bodies)){res.statusCode=404;return res.end('{}')}res.end(JSON.stringify(bodies[req.url]))});await new Promise(r=>app.listen(0,'127.0.0.1',r));return {app,seen,base:`http://127.0.0.1:${app.address().port}`};
}
async function withConsole(fn){const f=await fixture(),l=await legacy(),app=createApp({repoRoot:f.root,dataRoot:f.data,legacyBase:l.base});await new Promise(r=>app.listen(0,'127.0.0.1',r));try{return await fn(`http://127.0.0.1:${app.address().port}`,l.seen)}finally{await new Promise(r=>app.close(r));await new Promise(r=>l.app.close(r));await rm(f.root,{recursive:true,force:true})}}

test('nine Founder Console menus have bounded GET read models',async()=>withConsole(async(base,seen)=>{for(const p of paths){const r=await fetch(`${base}/api/die/v1/${p}`);assert.equal(r.status,200,p);const j=await r.json();assert.equal(j.read_only,true,p);assert.ok(j.observed_at,p);const w=await fetch(`${base}/api/die/v1/${p}`,{method:'POST'});assert.equal(w.status,405,p)}assert.ok(seen.every(([method])=>method==='GET'))}));
test('provider model preserves browser-native primary and optional bridge',async()=>withConsole(async base=>{const j=await (await fetch(`${base}/api/die/v1/providers`)).json();assert.equal(j.data.browser_native_primary,true);assert.equal(j.data.api_bridge.provider_count,0);assert.equal(j.data.api_bridge.policy.browser_native_replacement_allowed,false);assert.equal(j.data.api_bridge.policy.scheduling_authority,'MISSION_CONTROL')}));
test('legacy QC is exposed through bounded read adapter',async()=>withConsole(async base=>{const j=await (await fetch(`${base}/api/die/v1/qc/gallery`)).json();assert.equal(j.data.available,true);assert.equal(j.data.data.asset_count,1)}));
test('health proves shadow mode and legacy coexistence',async()=>withConsole(async base=>{const j=await (await fetch(`${base}/healthz`)).json();assert.equal(j.status,'PASS');assert.equal(j.mode,'SHADOW_V1');assert.equal(j.legacy_8876,'PASS');assert.equal(j.cutover,false);assert.equal(j.write_actions_enabled,false)}));
test('shell contains all centralized menu labels and 8876 preservation notice',async()=>withConsole(async base=>{const body=await (await fetch(`${base}/`)).text();for(const label of ['Overview','Production','Providers/BYOK','QC Gallery','Submission Ready','Demand Intelligence','Tasks/MC','System Health','Settings'])assert.match(body,new RegExp(label.replace('/','\\/')));assert.match(body,/localhost:8876 remains (?:live|available)/)}));
