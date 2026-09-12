#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

export const TERMINAL_STATES=new Set(['SUCCEEDED','FAILED','TIMEOUT','CANCELLED','UNSUPPORTED','AMBIGUOUS','EMPTY']);
export class RuntimeError extends Error{constructor(code,detail=''){super(detail?`${code}:${detail}`:code);this.code=code;this.detail=detail}}

export function normalizeProfileId(raw){
  const s=String(raw||'').trim().replace(/^h01-web-p/i,'').replace(/^p/i,'');
  if(!/^\d{1,3}$/.test(s))throw new RuntimeError('E_PROFILE_ID');
  const n=parseInt(s,10); if(n<1||n>100)throw new RuntimeError('E_PROFILE_RANGE');
  return `h01-web-p${String(n).padStart(3,'0')}`;
}
export function expectedBinding(raw){
  const profile_id=normalizeProfileId(raw),n=parseInt(profile_id.slice(-3),10),udd_index=Math.floor((n-1)/5)+1;
  const udd_id=`h01-web-s${String(udd_index).padStart(2,'0')}`;
  return {profile_id,profile_number:n,udd_id,udd_index,slot:((n-1)%5)+1,cdp_host:'127.0.0.1',cdp_port:9200+n,user_data_dir:`/var/lib/die/h01/browser/${udd_id}`,profile_directory:profile_id};
}
export function resolveBinding(manifest,raw){
  if(manifest?.schema!=='die.h01.brave-fabric.host-local.v1')throw new RuntimeError('E_MANIFEST_SCHEMA');
  if(manifest?.topology?.max_active_per_udd!==1)throw new RuntimeError('E_MANIFEST_UDD_LIMIT');
  const want=expectedBinding(raw),row=(manifest.profiles||[]).find(x=>x.profile_id===want.profile_id);
  if(!row)throw new RuntimeError('E_PROFILE_NOT_IN_MANIFEST');
  for(const k of ['profile_number','udd_id','udd_index','slot','cdp_host','cdp_port','user_data_dir','profile_directory'])if(row[k]!==want[k])throw new RuntimeError('E_MANIFEST_BINDING_MISMATCH',k);
  if(row.cdp_host!=='127.0.0.1')throw new RuntimeError('E_CDP_NOT_LOOPBACK');
  return want;
}
export function validateTerminalResult(v,ctx){
  if(v?.job_id!==ctx.job_id)throw new RuntimeError('E_RESULT_JOB_MISMATCH');
  if(v?.provider_id!==ctx.provider_id)throw new RuntimeError('E_RESULT_PROVIDER_MISMATCH');
  if(v?.profile_id!==ctx.profile_id)throw new RuntimeError('E_RESULT_PROFILE_MISMATCH');
  if(!TERMINAL_STATES.has(String(v?.terminal_state||'')))throw new RuntimeError('E_RESULT_NOT_TERMINAL');
  return v;
}
export function sha256File(file){return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')}
export function atomicJson(file,value){
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});
  const data=Buffer.from(JSON.stringify(value,null,2)+'\n'),tmp=`${file}.${process.pid}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  const fd=fs.openSync(tmp,'wx',0o640);try{fs.writeFileSync(fd,data);fs.fsyncSync(fd)}finally{fs.closeSync(fd)}fs.renameSync(tmp,file);
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const running=c=>c&&c.exitCode===null&&c.signalCode===null;
class Cdp{
  constructor(url){this.url=url;this.ws=null;this.seq=0;this.pending=new Map()}
  async connect(){this.ws=new WebSocket(this.url);await new Promise((res,rej)=>{const t=setTimeout(()=>rej(new RuntimeError('E_CDP_WS_TIMEOUT')),10000);this.ws.addEventListener('open',()=>{clearTimeout(t);res()});this.ws.addEventListener('error',()=>{clearTimeout(t);rej(new RuntimeError('E_CDP_WS'))})});this.ws.addEventListener('message',e=>{let m;try{m=JSON.parse(String(e.data))}catch{return}const p=this.pending.get(m.id);if(!p)return;this.pending.delete(m.id);m.error?p.reject(new RuntimeError('E_CDP_RPC',m.error.message||'')):p.resolve(m.result||{})})}
  send(method,params={}){const id=++this.seq;return new Promise((resolve,reject)=>{const t=setTimeout(()=>{this.pending.delete(id);reject(new RuntimeError('E_CDP_RPC_TIMEOUT',method))},10000);this.pending.set(id,{resolve:v=>{clearTimeout(t);resolve(v)},reject:e=>{clearTimeout(t);reject(e)}});this.ws.send(JSON.stringify({id,method,params}))})}
  close(){try{this.ws?.close()}catch{}}
}
async function getJson(url,timeout=4000){const r=await fetch(url,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw new RuntimeError('E_HTTP',String(r.status));return await r.json()}
async function waitCdp(b,child,ms){const end=Date.now()+ms,u=`http://${b.cdp_host}:${b.cdp_port}/json/version`;while(Date.now()<end){if(!running(child))throw new RuntimeError(child.exitCode===73?'E_UDD_BUSY':'E_BROWSER_EXIT',String(child.exitCode??child.signalCode));try{const v=await getJson(u,1200);if(v.webSocketDebuggerUrl)return v}catch{}await sleep(200)}throw new RuntimeError('E_CDP_START_TIMEOUT')}
async function targets(b){return await getJson(`http://${b.cdp_host}:${b.cdp_port}/json/list`)}
async function closeTarget(b,id){const r=await fetch(`http://${b.cdp_host}:${b.cdp_port}/json/close/${encodeURIComponent(id)}`,{signal:AbortSignal.timeout(4000)});if(!r.ok)throw new RuntimeError('E_TARGET_CLOSE',String(r.status))}
async function enforceOnePage(b,providerUrl){
  const wanted=new URL(providerUrl).origin;let pages=(await targets(b)).filter(x=>x.type==='page');
  let keep=pages.find(x=>{try{return new URL(x.url).origin===wanted}catch{return false}});if(!keep)throw new RuntimeError('E_PROVIDER_TARGET_MISSING',wanted);
  for(const p of pages)if(p.id!==keep.id)await closeTarget(b,p.id);await sleep(400);
  pages=(await targets(b)).filter(x=>x.type==='page');if(pages.length!==1)throw new RuntimeError('E_PAGE_CARDINALITY',String(pages.length));
  keep=pages[0];if(new URL(keep.url).origin!==wanted)throw new RuntimeError('E_PROVIDER_ORIGIN_MISMATCH');return keep;
}
async function observePage(t,wantedOrigin){const c=new Cdp(t.webSocketDebuggerUrl);await c.connect();try{const end=Date.now()+15000;while(Date.now()<end){const r=await c.send('Runtime.evaluate',{expression:`(()=>({readyState:document.readyState,title:(document.title||'').slice(0,120),origin:location.origin,path:location.pathname}))()`,returnByValue:true});const v=r.result?.value||{};if(v.origin===wantedOrigin&&['interactive','complete'].includes(v.readyState))return v;await sleep(250)}throw new RuntimeError('E_PROVIDER_PAGE_NOT_READY',wantedOrigin)}finally{c.close()}}
async function browserClose(b){const v=await getJson(`http://${b.cdp_host}:${b.cdp_port}/json/version`);const c=new Cdp(v.webSocketDebuggerUrl);await c.connect();try{await c.send('Browser.close')}finally{c.close()}}
async function waitExit(child,ms){const end=Date.now()+ms;while(running(child)&&Date.now()<end)await sleep(100);return !running(child)}
async function cdpClosed(b){try{await getJson(`http://${b.cdp_host}:${b.cdp_port}/json/version`,800);return false}catch{return true}}
function lockPath(b){const rt=process.env.XDG_RUNTIME_DIR||`/run/user/${process.getuid?.()??1000}`;return path.join(rt,'die-h01-brave',`${b.udd_id}.lock`)}
function lockReleased(b){return spawnSync('flock',['-n',lockPath(b),'true']).status===0}
async function waitLockReleased(b,ms=4000){const end=Date.now()+ms;while(Date.now()<end){if(lockReleased(b))return true;await sleep(100)}return lockReleased(b)}
function probeResult(ctx,o){return {schema:'die.h01.browser-job-result.v1',job_id:ctx.job_id,job_kind:'RUNTIME_READINESS_PROBE',provider_id:ctx.provider_id,profile_id:ctx.profile_id,udd_id:ctx.udd_id,terminal_state:'SUCCEEDED',completed_at:new Date().toISOString(),provider_page:{origin:String(o.origin||''),path:String(o.path||''),ready_state:String(o.readyState||''),title:String(o.title||'')},authority:{provider_generation_dispatched:false,submission_authorized:false,publication_authorized:false}}}
function failureResult(ctx,e){return {schema:'die.h01.browser-job-result.v1',job_id:ctx.job_id,job_kind:'RUNTIME_FAILURE',provider_id:ctx.provider_id,profile_id:ctx.profile_id,udd_id:ctx.udd_id,terminal_state:e?.code==='E_RESULT_TIMEOUT'?'TIMEOUT':'FAILED',completed_at:new Date().toISOString(),error_code:String(e?.code||'E_RUNTIME'),error_detail:String(e?.detail||'').slice(0,500),authority:{provider_generation_dispatched:false,submission_authorized:false,publication_authorized:false}}}
async function waitResult(file,ctx,ms){const end=Date.now()+ms;while(Date.now()<end){if(fs.existsSync(file))return validateTerminalResult(JSON.parse(fs.readFileSync(file,'utf8')),ctx);await sleep(250)}throw new RuntimeError('E_RESULT_TIMEOUT')}

export async function runRuntime(o){
  const manifest=JSON.parse(fs.readFileSync(o.manifest,'utf8')),b=resolveBinding(manifest,o.profileId),ctx={job_id:o.jobId,provider_id:o.providerId,profile_id:b.profile_id,udd_id:b.udd_id};
  let child=null,target=null,result=null,resultSha=null,error=null,closeSent=false,exited=false,closed=false,released=false;const started_at=new Date().toISOString();
  const env={...process.env,DISPLAY:process.env.DISPLAY||':12.0',XAUTHORITY:process.env.XAUTHORITY||'/home/kopiko/.Xauthority',XDG_RUNTIME_DIR:process.env.XDG_RUNTIME_DIR||`/run/user/${process.getuid?.()??1000}`};
  try{
    child=spawn(o.launcher,[b.profile_id,o.providerUrl],{env,stdio:['ignore','ignore','pipe'],detached:true});await waitCdp(b,child,o.startTimeoutMs);target=await enforceOnePage(b,o.providerUrl);const obs=await observePage(target,new URL(o.providerUrl).origin);
    if(o.canaryHoldMs>0)await sleep(o.canaryHoldMs);
    if(o.mode==='probe'){result=probeResult(ctx,obs);atomicJson(o.resultReceipt,result)}else if(o.mode==='wait-result'){result=await waitResult(o.resultReceipt,ctx,o.resultTimeoutMs)}else throw new RuntimeError('E_MODE',o.mode);
    result=validateTerminalResult(result,ctx);resultSha=sha256File(o.resultReceipt);
  }catch(e){error=e instanceof RuntimeError?e:new RuntimeError('E_RUNTIME',String(e?.message||e));if(!fs.existsSync(o.resultReceipt)){try{result=failureResult(ctx,error);atomicJson(o.resultReceipt,result);resultSha=sha256File(o.resultReceipt)}catch{}}}
  finally{
    if(child){try{await browserClose(b);closeSent=true}catch{}exited=await waitExit(child,8000);if(!exited&&running(child)){try{process.kill(-child.pid,'SIGTERM')}catch{}exited=await waitExit(child,5000)}}
    closed=await cdpClosed(b);released=await waitLockReleased(b);
  }
  const receipt={schema:'die.h01.brave-udd-runtime-receipt.v1',status:(!error&&closeSent&&exited&&closed&&released)?'PASS':'FAIL',job_id:ctx.job_id,provider_id:ctx.provider_id,profile_id:ctx.profile_id,udd_id:ctx.udd_id,started_at,completed_at:new Date().toISOString(),mode:o.mode,ownership:{launcher_udd_mutex:true,max_active_per_udd:1,lock_path:lockPath(b),lock_released:released},browser:{launcher:o.launcher,cdp_host:b.cdp_host,cdp_port:b.cdp_port,loopback_only:b.cdp_host==='127.0.0.1',provider_origin:new URL(o.providerUrl).origin,page_count_after_enforcement:target?1:0,browser_close_sent:closeSent,process_exited:exited,cdp_closed:closed},durable_result:{path:o.resultReceipt,sha256:resultSha,terminal_state:result?.terminal_state||null,present:fs.existsSync(o.resultReceipt)},error:error?{code:error.code,detail:String(error.detail||'').slice(0,500)}:null,safety:{cookies_read:false,tokens_read:false,session_bytes_read:false,browser_profile_copied:false,mission_control_mutated:false,scheduler_owned:false}};
  atomicJson(o.runtimeReceipt,receipt);if(receipt.status!=='PASS')throw new RuntimeError('E_RUNTIME_ACCEPTANCE',JSON.stringify(receipt));return receipt;
}
function arg(name,fallback=''){const i=process.argv.indexOf(name);return i>=0?String(process.argv[i+1]||''):fallback}
function numArg(name,fallback){const v=Number(arg(name,String(fallback)));return Number.isFinite(v)?v:fallback}
async function main(){
  const o={manifest:arg('--manifest','/var/lib/die/h01/browser/fabric-manifest-v1.json'),launcher:arg('--launcher','/opt/die/h01/bin/h01-brave-profile'),profileId:arg('--profile-id'),providerId:arg('--provider-id'),providerUrl:arg('--provider-url'),jobId:arg('--job-id'),mode:arg('--mode','probe'),resultReceipt:arg('--result-receipt'),runtimeReceipt:arg('--runtime-receipt'),startTimeoutMs:numArg('--start-timeout-ms',30000),resultTimeoutMs:numArg('--result-timeout-ms',300000),canaryHoldMs:numArg('--canary-hold-ms',0)};
  for(const k of ['profileId','providerId','providerUrl','jobId','resultReceipt','runtimeReceipt'])if(!o[k])throw new RuntimeError('E_CONFIG',k);
  process.stdout.write(JSON.stringify(await runRuntime(o))+'\n');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(e=>{const x=e instanceof RuntimeError?e:new RuntimeError('E_RUNTIME',String(e?.message||e));process.stderr.write(JSON.stringify({status:'ERROR',error:x.code,detail:x.detail})+'\n');process.exitCode=2});
