#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { startJobScopedClusterRuntime, runtimeIdleSnapshot } from '../../browser/linux/job_scoped_cluster_runtime.mjs';
import { probeConsoleProvider } from '../lib/console_broker_provider_worker.mjs';

const REPO=path.resolve(path.dirname(new URL(import.meta.url).pathname),'../../..');
const REG=JSON.parse(fs.readFileSync(path.join(REPO,'company/factory-asset/registries/web-ai-clusters.v1.json'),'utf8'));
const READY=JSON.parse(fs.readFileSync(path.join(REPO,'company/factory-asset/registries/provider-readiness-profiles.v1.json'),'utf8')).providers;
const PLAYWRIGHT=path.join(REPO,'company/muxia/node_modules/playwright/index.mjs');
const ROOT=process.env.FA338_CANARY_ROOT||'/var/lib/die/acceptance/FA-338';
const clusterId=process.env.FA338_CANARY_CLUSTER||'cluster-b';
const providerId=process.env.FA338_CANARY_PROVIDER||'gemini';
const URLS={chatgpt:'https://chatgpt.com/',qwen:'https://chat.qwen.ai/',gemini:'https://gemini.google.com/app',manus:'https://manus.im/app',duckai:'https://duck.ai/'};
function atomic(file,v){fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});const t=`${file}.tmp-${process.pid}`;fs.writeFileSync(t,JSON.stringify(v,null,2)+'\n',{mode:0o640});fs.renameSync(t,file)}
function cfg(provider){return{browser_url:URLS[provider],actual_live_transport:'BROWSER_CDP',transport_role:'FA338_LIFECYCLE_CANARY',primary_transport_contract:'BROWSER_CDP',session_api_live_executor_claimed:provider==='qwen'?false:null}}
const before=runtimeIdleSnapshot({registry:REG});
if(before.active_runtimes!==0||before.active_profile_processes!==0)throw new Error(`E_FA338_NOT_COLD:${JSON.stringify(before)}`);
const rounds=[];
for(let i=1;i<=2;i++){
 const runtimeReceipt=path.join(ROOT,`round-${i}-runtime.json`),terminal=path.join(ROOT,`round-${i}-terminal.json`);
 const runtime=await startJobScopedClusterRuntime({dieHome:REPO,registry:REG,clusterId,jobId:`FA338-CANARY-R${i}`,receiptPath:runtimeReceipt});
 const observation=await probeConsoleProvider({controlBaseUrl:runtime.control_base_url,playwrightEntry:PLAYWRIGHT,providerId,providerConfig:cfg(providerId),readinessProfile:READY[providerId],jobId:`FA338-CANARY-R${i}-READINESS`,clusterId,ttlMs:120000});
 const terminalValue={schema:'die.factory-asset.fa338-canary-terminal.v1',status:observation.status==='OBSERVED'&&observation.readiness?.state==='HEALTHY'?'SUCCEEDED':'FAILED',round:i,cluster_id:clusterId,provider_id:providerId,readiness:observation.readiness||null,provider_generation_dispatched:false,credential_values_read:false,cookies_or_tokens_read:false,completed_at:new Date().toISOString()};
 atomic(terminal,terminalValue);
 const closed=await runtime.stop({terminalEvidencePath:terminal,reason:'FA338_READINESS_CANARY'});
 rounds.push({round:i,profile_id:runtime.profile_id,browser_owner_pid:runtime.browser_owner_pid,debug_port:runtime.debug_port,readiness:observation.readiness,status:terminalValue.status,closed:{status:closed.status,debug_endpoint_closed:closed.debug_endpoint_closed,control_endpoint_closed:closed.control_endpoint_closed,profile_process_gone:closed.profile_process_gone,lease_released:closed.lease_released}});
 if(terminalValue.status!=='SUCCEEDED')throw new Error(`E_FA338_READINESS:${observation.readiness?.state||observation.failure_code||observation.status}`);
 const idle=runtimeIdleSnapshot({registry:REG});if(idle.active_runtimes!==0||idle.active_profile_processes!==0)throw new Error(`E_FA338_NOT_COLD_AFTER_ROUND:${i}`);
}
if(rounds[0].profile_id!==rounds[1].profile_id)throw new Error('E_FA338_PROFILE_IDENTITY_DRIFT');
const after=runtimeIdleSnapshot({registry:REG});
const out={schema:'die.factory-asset.fa338-live-canary.v1',task_id:'FA-338',status:'PASS',owner_model:'JOB_SCOPED_HEADFUL_BROWSER_CDP',cluster_id:clusterId,provider_id:providerId,before,rounds,after,same_persistent_profile_reopened:true,provider_generation_calls_performed:0,credential_values_read:false,cookies_or_tokens_read:false,submission_authorized:false,publication_authorized:false,spend_usd:0,completed_at:new Date().toISOString()};
atomic(path.join(ROOT,'FA-338-live-canary.receipt.json'),out);
console.log(JSON.stringify(out));
