#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { readRepairHold, writeAuthRepairHold } from './auth_repair_hold.mjs';

const SOCKET=process.env.DIE_PRINCIPAL_BROWSER_BROKER_SOCKET||'/run/die/principal-browser-broker.sock';
const HOLD_ROOT='/var/lib/die/state/principal-auth-repair';
const CFG={
  'die-lnx-executive-001':{
    profile:'/var/lib/die/executive/browser-profile',
    status:'/var/lib/die/executive/browser-status.json',
    script:'/srv/die/company/executive/linux/operator_browser.mjs',
    display:103,
    receiptDir:'/var/lib/die/executive/cognition-receipts',
  },
  'die-lnx-division-001':{
    profile:'/var/lib/die/division01/browser-profile',
    status:'/var/lib/die/division01/browser-status.json',
    script:'/srv/die/company/division/division001/linux/operator_browser.mjs',
    display:104,
    receiptDir:'/var/lib/die/division01/cognition-receipts',
  },
};
const SAFE_JOB=/^[A-Za-z0-9][A-Za-z0-9_.:-]{2,180}$/;
const sleep=(ms)=>new Promise((r)=>setTimeout(r,ms));
const active=new Map();

function safeJob(value){return String(value||'').replace(/[^A-Za-z0-9_.-]/g,'_')}
function atomicJson(file,value){
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});
  const tmp=`${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n',{mode:0o640});
  fs.renameSync(tmp,file);
}
function pidAlive(pid){if(!Number.isInteger(pid)||pid<1)return false;try{process.kill(pid,0);return true}catch{return false}}
function procProfile(profile){
  let entries=[];try{entries=fs.readdirSync('/proc')}catch{return null}
  const needle=`--user-data-dir=${profile}`;
  for(const e of entries){
    if(!/^\d+$/.test(e))continue;
    try{
      const s=fs.readFileSync(`/proc/${e}/cmdline`).toString().replace(/\0/g,' ');
      if(s.includes(needle)&&(s.includes('chrome')||s.includes('chromium')||s.includes('brave')))return Number(e);
    }catch{}
  }
  return null;
}
async function waitExit(child,ms){
  if(!child||child.exitCode!==null)return true;
  return await new Promise((resolve)=>{
    let done=false,timer;
    const finish=(v)=>{if(done)return;done=true;clearTimeout(timer);child.off('exit',onExit);resolve(v)};
    const onExit=()=>finish(true);
    child.once('exit',onExit);timer=setTimeout(()=>finish(false),ms);
  });
}
async function waitDisplay(displayNum,xvfb,timeout=10000){
  const sock=`/tmp/.X11-unix/X${displayNum}`,deadline=Date.now()+timeout;
  while(Date.now()<deadline){
    if(xvfb.exitCode!==null)throw new Error(`E_PRINCIPAL_XVFB_EXIT:${xvfb.exitCode}`);
    if(fs.existsSync(sock))return;
    await sleep(100);
  }
  throw new Error('E_PRINCIPAL_XVFB_READY_TIMEOUT');
}
async function waitStatus(cfg,started,owner,timeout=45000){
  const deadline=Date.now()+timeout;let v=null;
  while(Date.now()<deadline){
    if(owner.exitCode!==null)throw new Error(`E_PRINCIPAL_BROWSER_EXIT:${owner.exitCode}`);
    try{
      v=JSON.parse(fs.readFileSync(cfg.status,'utf8'));
      if(Date.parse(v.observed_at)>=started&&v.debugHost==='127.0.0.1'&&['READY','AUTH_REQUIRED','OPERATOR_CHECK_REQUIRED'].includes(v.state))return v;
    }catch{}
    await sleep(150);
  }
  throw new Error('E_PRINCIPAL_BROWSER_STATUS_TIMEOUT');
}
function terminalEvidence(cfg,file){
  if(typeof file!=='string'||!path.isAbsolute(file))throw new Error('E_PRINCIPAL_TERMINAL_EVIDENCE_PATH');
  const root=path.resolve(cfg.receiptDir),resolved=path.resolve(file);
  if(resolved!==root&&!resolved.startsWith(root+path.sep))throw new Error('E_PRINCIPAL_TERMINAL_EVIDENCE_SCOPE');
  const bytes=fs.readFileSync(resolved);
  if(bytes.length<2||bytes.length>2_000_000)throw new Error('E_PRINCIPAL_TERMINAL_EVIDENCE_SIZE');
  let parsed;try{parsed=JSON.parse(bytes.toString('utf8'))}catch{throw new Error('E_PRINCIPAL_TERMINAL_EVIDENCE_JSON')}
  return{path:resolved,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),schema:parsed?.schema||null,status:parsed?.status||null};
}
function lifecycleReceipt(cfg,jobId){return path.join(cfg.receiptDir,`browser-lifecycle-${safeJob(jobId)}.json`)}
function publicHandle(h){return{principal_id:h.principalId,job_id:h.jobId,state:h.state,profile:h.cfg.profile,headful:true,virtual_display:h.cfg.display,browser_pid:h.status?.browserPid||null,debug_host:h.status?.debugHost||null,debug_port:h.status?.debugPort||null,ready_state:h.status?.state||null,started_at:h.startedAt,credential_values_read:false,cookies_or_tokens_read:false}}
async function stopChildren(h){
  let forced=false;
  if(h.owner&&h.owner.exitCode===null){
    h.owner.kill('SIGTERM');
    if(!await waitExit(h.owner,10000)){forced=true;h.owner.kill('SIGKILL');await waitExit(h.owner,2000)}
  }
  if(h.xvfb&&h.xvfb.exitCode===null){
    h.xvfb.kill('SIGTERM');
    if(!await waitExit(h.xvfb,2500)){forced=true;h.xvfb.kill('SIGKILL');await waitExit(h.xvfb,1000)}
  }
  const deadline=Date.now()+5000;
  while(Date.now()<deadline&&procProfile(h.cfg.profile))await sleep(100);
  return{forced_process_cleanup:forced,profile_process_gone:!procProfile(h.cfg.profile),owner_exit_code:h.owner?.exitCode??null,xvfb_exit_code:h.xvfb?.exitCode??null};
}
async function startRuntime(principalId,jobId){
  const cfg=CFG[principalId];if(!cfg)throw Object.assign(new Error('E_PRINCIPAL_BROWSER_PRINCIPAL'),{httpStatus:400});
  if(!SAFE_JOB.test(String(jobId||'')))throw Object.assign(new Error('E_PRINCIPAL_BROWSER_JOB_ID'),{httpStatus:400});
  const holdPath=path.join(HOLD_ROOT,`${principalId}.json`),hold=readRepairHold(holdPath);
  if(hold)throw Object.assign(new Error(`E_AUTH_REPAIR_REQUIRED_HELD:${principalId}`),{httpStatus:423,details:{repair_hold:hold}});
  const prior=active.get(principalId);
  if(prior){
    if(prior.jobId===jobId&&prior.state==='WORK')return{...publicHandle(prior),idempotent_replay:true};
    throw Object.assign(new Error(`E_PRINCIPAL_BROWSER_BUSY:${prior.jobId}`),{httpStatus:409});
  }
  const foreignPid=procProfile(cfg.profile);
  if(foreignPid)throw Object.assign(new Error(`E_PRINCIPAL_PROFILE_BUSY:${foreignPid}`),{httpStatus:409});
  for(const name of ['DevToolsActivePort','SingletonLock','SingletonCookie','SingletonSocket'])fs.rmSync(path.join(cfg.profile,name),{force:true});
  const started=Date.now(),startedAt=new Date(started).toISOString(),receipt=lifecycleReceipt(cfg,jobId);
  const base={schema:'die.cognition.principal-browser-broker-lifecycle.v1',principal_id:principalId,job_id:jobId,profile:cfg.profile,headful:true,virtual_display:cfg.display,broker_socket:SOCKET,credential_values_read:false,cookies_or_tokens_read:false,started_at:startedAt,status:'SPAWNING'};
  atomicJson(receipt,base);
  let xvfb=null,owner=null;
  try{
    xvfb=spawn('/usr/bin/Xvfb',[`:${cfg.display}`,'-screen','0','1920x1080x24','-nolisten','tcp'],{stdio:'ignore'});
    await waitDisplay(cfg.display,xvfb);
    owner=spawn('/usr/local/bin/node',[cfg.script,'launch'],{env:{...process.env,DISPLAY:`:${cfg.display}`,HOME:'/home/kopiko'},stdio:['ignore','ignore','pipe']});
    const status=await waitStatus(cfg,started,owner);
    const h={principalId,jobId,cfg,xvfb,owner,status,state:'WORK',startedAt,receipt};active.set(principalId,h);
    atomicJson(receipt,{...base,status:'WORK',browser_pid:status.browserPid,debug_host:status.debugHost,debug_port:status.debugPort,ready_state:status.state,ready_at:new Date().toISOString()});
    if(status.state!=='READY'){
      const repair=writeAuthRepairHold(holdPath,{scopeId:principalId,profileId:cfg.profile,providerId:'chatgpt',reasonCode:status.state,sourceJobId:jobId});
      const stopped=await stopChildren(h);active.delete(principalId);
      atomicJson(receipt,{...base,status:'COLD',ready_state:status.state,auth_repair_required:true,repair_hold_path:holdPath,repair_hold_state:repair.state,...stopped,completed_at:new Date().toISOString()});
      const authError=Object.assign(new Error(`E_AUTH_REPAIR_REQUIRED:${principalId}:${status.state}`),{httpStatus:423,details:{repair_hold:repair},lifecycleHandled:true});
      throw authError;
    }
    return publicHandle(h);
  }catch(error){
    if(!active.has(principalId)&&!error?.lifecycleHandled){
      const h={principalId,jobId,cfg,xvfb,owner,status:null,state:'FAILED',startedAt,receipt};
      const stopped=await stopChildren(h).catch(()=>({profile_process_gone:!procProfile(cfg.profile)}));
      atomicJson(receipt,{...base,status:'START_FAILED',error:String(error?.message||error).slice(0,800),...stopped,completed_at:new Date().toISOString()});
    }
    throw error;
  }
}
async function stopRuntime(principalId,jobId,terminalPath,reason='COGNITION_TERMINAL'){
  const cfg=CFG[principalId];if(!cfg)throw Object.assign(new Error('E_PRINCIPAL_BROWSER_PRINCIPAL'),{httpStatus:400});
  const h=active.get(principalId);
  if(!h)throw Object.assign(new Error('E_PRINCIPAL_BROWSER_NOT_ACTIVE'),{httpStatus:409});
  if(h.jobId!==jobId)throw Object.assign(new Error(`E_PRINCIPAL_BROWSER_JOB_MISMATCH:${h.jobId}`),{httpStatus:409});
  const terminal=terminalEvidence(cfg,terminalPath);
  h.state='STOPPING';
  const stopped=await stopChildren(h);active.delete(principalId);
  const out={schema:'die.cognition.principal-browser-broker-lifecycle.v1',principal_id:principalId,job_id:jobId,profile:cfg.profile,headful:true,virtual_display:cfg.display,broker_socket:SOCKET,status:stopped.profile_process_gone?'COLD':'CLOSE_FAILED',close_reason:reason,browser_pid:h.status?.browserPid||null,debug_host:h.status?.debugHost||null,debug_port:h.status?.debugPort||null,terminal_evidence_path:terminal.path,terminal_evidence_sha256:terminal.sha256,terminal_schema:terminal.schema,terminal_status:terminal.status,...stopped,credential_values_read:false,cookies_or_tokens_read:false,started_at:h.startedAt,completed_at:new Date().toISOString()};
  atomicJson(h.receipt,out);
  if(out.status!=='COLD')throw Object.assign(new Error('E_PRINCIPAL_BROWSER_CLOSE_INCOMPLETE'),{httpStatus:500});
  return out;
}
async function readBody(req){
  let raw='';for await(const chunk of req){raw+=chunk;if(raw.length>16384)throw Object.assign(new Error('E_REQUEST_TOO_LARGE'),{httpStatus:413})}
  if(!raw)return{};try{return JSON.parse(raw)}catch{throw Object.assign(new Error('E_REQUEST_JSON'),{httpStatus:400})}
}
function send(res,status,value){const body=JSON.stringify(value);res.writeHead(status,{'content-type':'application/json','content-length':Buffer.byteLength(body)});res.end(body)}
const server=http.createServer(async(req,res)=>{
  try{
    const url=new URL(req.url||'/','http://localhost');
    if(req.method==='GET'&&url.pathname==='/v1/status'){
      const principalId=url.searchParams.get('principal_id');
      if(principalId){const h=active.get(principalId);return send(res,200,{schema:'die.cognition.principal-browser-broker-status.v1',broker_state:'READY',principal_id:principalId,runtime:h?publicHandle(h):{state:'COLD'},credential_values_read:false,cookies_or_tokens_read:false})}
      return send(res,200,{schema:'die.cognition.principal-browser-broker-status.v1',broker_state:'READY',active:[...active.values()].map(publicHandle),credential_values_read:false,cookies_or_tokens_read:false});
    }
    if(req.method==='POST'&&url.pathname==='/v1/start'){
      const b=await readBody(req),out=await startRuntime(b.principal_id,b.job_id);return send(res,200,{schema:'die.cognition.principal-browser-broker-start.v1',status:'READY',runtime:out});
    }
    if(req.method==='POST'&&url.pathname==='/v1/stop'){
      const b=await readBody(req),out=await stopRuntime(b.principal_id,b.job_id,b.terminal_evidence_path,b.reason||'COGNITION_TERMINAL');return send(res,200,{schema:'die.cognition.principal-browser-broker-stop.v1',status:'COLD',runtime:out});
    }
    send(res,404,{error:'E_NOT_FOUND'});
  }catch(error){send(res,Number(error?.httpStatus)||500,{error:String(error?.message||error).slice(0,1000),details:error?.details||null,credential_values_read:false,cookies_or_tokens_read:false});}
});

fs.mkdirSync(path.dirname(SOCKET),{recursive:true,mode:0o770});fs.rmSync(SOCKET,{force:true});
server.listen(SOCKET,()=>{fs.chmodSync(SOCKET,0o660);console.log(JSON.stringify({schema:'die.cognition.principal-browser-broker.v1',state:'READY',socket:SOCKET,principals:Object.keys(CFG),credential_values_read:false,cookies_or_tokens_read:false}))});
async function shutdown(){
  server.close();
  for(const h of [...active.values()]){await stopChildren(h).catch(()=>{});active.delete(h.principalId)}
  fs.rmSync(SOCKET,{force:true});
  process.exit(0);
}
process.once('SIGTERM',shutdown);process.once('SIGINT',shutdown);
