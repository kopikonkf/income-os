#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';

const DEFAULT_STATE_ROOT='/var/lib/muxia/state/job-browser-runtime';
const DEFAULT_BROKER_STATE_ROOT='/var/lib/muxia/state/job-cluster-brokers';
const DISPLAY_BY_CLUSTER=Object.freeze({'cluster-a':101,'cluster-b':102});
const SAFE_JOB=/^[A-Za-z0-9][A-Za-z0-9_.:-]{2,180}$/;
const sleep=(ms)=>new Promise((r)=>setTimeout(r,ms));

function atomicJson(file,value){
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});
  const tmp=`${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n',{mode:0o640});
  fs.renameSync(tmp,file);
}
function pidAlive(pid){if(!Number.isInteger(pid)||pid<1)return false;try{process.kill(pid,0);return true}catch{return false}}
function safeReadJson(file){try{return JSON.parse(fs.readFileSync(file,'utf8'))}catch{return null}}
function procHasProfile(profileDir){
  let entries=[];try{entries=fs.readdirSync('/proc')}catch{return false}
  const needle=`--user-data-dir=${profileDir}`;
  for(const ent of entries){
    if(!/^\d+$/.test(ent))continue;
    try{
      const s=fs.readFileSync(`/proc/${ent}/cmdline`).toString('utf8').replace(/\0/g,' ');
      if(s.includes(needle)&&(s.includes('chrome')||s.includes('chromium')||s.includes('brave')))return true;
    }catch{}
  }
  return false;
}
function acquireLock(file,payload){
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});
  for(let i=0;i<2;i++){
    try{const fd=fs.openSync(file,'wx',0o640);fs.writeFileSync(fd,JSON.stringify(payload)+'\n');fs.closeSync(fd);return}
    catch(e){
      if(e?.code!=='EEXIST')throw e;
      const old=safeReadJson(file);
      if(old&&pidAlive(Number(old.owner_pid)))throw new Error(`E_JOB_BROWSER_CLUSTER_BUSY:${old.owner_pid}`);
      fs.rmSync(file,{force:true});
    }
  }
  throw new Error('E_JOB_BROWSER_LOCK');
}
function tailBuffer(){let text='';return{push:(chunk)=>{text=(text+String(chunk)).slice(-6000)},get:()=>text}}
async function waitChildExit(child,ms){
  if(!child||child.exitCode!==null)return true;
  return await new Promise((resolve)=>{
    let done=false;let timer;
    const finish=(v)=>{if(done)return;done=true;clearTimeout(timer);child.off('exit',onExit);resolve(v)};
    const onExit=()=>finish(true);
    child.once('exit',onExit);timer=setTimeout(()=>finish(false),ms);
  });
}
async function waitDisplay(displayNum,xvfb,timeoutMs=10000){
  const sock=`/tmp/.X11-unix/X${displayNum}`,end=Date.now()+timeoutMs;
  while(Date.now()<end){
    if(xvfb.exitCode!==null)throw new Error(`E_XVFB_EXIT:${xvfb.exitCode}`);
    if(fs.existsSync(sock))return;
    await sleep(100);
  }
  throw new Error('E_XVFB_READY_TIMEOUT');
}
async function fetchStatus(controlBaseUrl,timeoutMs=1500){
  const r=await fetch(new URL('/v1/status',controlBaseUrl),{signal:AbortSignal.timeout(timeoutMs)});
  if(!r.ok)throw new Error(`E_BROKER_HTTP:${r.status}`);
  return await r.json();
}
async function waitBrokerReady(controlBaseUrl,broker,timeoutMs=45000){
  const end=Date.now()+timeoutMs;let last=null;
  while(Date.now()<end){
    if(broker.exitCode!==null)throw new Error(`E_JOB_BROKER_EXIT:${broker.exitCode}`);
    try{last=await fetchStatus(controlBaseUrl);if(last?.state==='READY'&&last?.debug_host==='127.0.0.1')return last}catch{}
    await sleep(150);
  }
  throw new Error(`E_JOB_BROKER_READY_TIMEOUT:${last?.state||'OFFLINE'}`);
}
async function waitEndpointClosed(url,timeoutMs=6000){
  const end=Date.now()+timeoutMs;
  while(Date.now()<end){try{await fetch(url,{signal:AbortSignal.timeout(500)})}catch{return true}await sleep(100)}
  return false;
}
function validateTerminalEvidence(file){
  const v=safeReadJson(file);
  if(!v)throw new Error('E_LIFECYCLE_TERMINAL_EVIDENCE_MISSING');
  if(!['SUCCEEDED','FAILED'].includes(String(v.status||'')))throw new Error(`E_LIFECYCLE_TERMINAL_EVIDENCE_STATE:${v.status||'UNKNOWN'}`);
  return v;
}

export function runtimeIdleSnapshot({registry,stateRoot=DEFAULT_STATE_ROOT}={}){
  const clusters=[];
  for(const c of registry.clusters||[]){
    if(!DISPLAY_BY_CLUSTER[c.cluster_id])continue;
    const lock=path.join(stateRoot,`${c.cluster_id}.lock`),old=safeReadJson(lock);
    const active=Boolean(old&&pidAlive(Number(old.owner_pid)));
    clusters.push({cluster_id:c.cluster_id,profile_id:c.profile_id,active_runtime:active,profile_process_active:procHasProfile(c.profile_dir),control_port:Number(c.broker_control_port)});
  }
  return{schema:'die.factory-asset.v1-job-browser-idle-snapshot.v1',clusters,active_runtimes:clusters.filter(x=>x.active_runtime).length,active_profile_processes:clusters.filter(x=>x.profile_process_active).length,credential_values_read:false,cookies_or_tokens_read:false};
}

export async function startJobScopedClusterRuntime({dieHome='/srv/die',registry,clusterId,jobId,stateRoot=DEFAULT_STATE_ROOT,brokerStateRoot=DEFAULT_BROKER_STATE_ROOT,browserExecutable='/usr/bin/google-chrome-stable',receiptPath=null}={}){
  if(!SAFE_JOB.test(String(jobId||'')))throw new Error('E_JOB_BROWSER_JOB_ID');
  const c=(registry.clusters||[]).find(x=>x.cluster_id===clusterId);if(!c)throw new Error(`E_JOB_BROWSER_CLUSTER:${clusterId}`);
  const displayNum=DISPLAY_BY_CLUSTER[clusterId];if(!displayNum)throw new Error(`E_JOB_BROWSER_DISPLAY:${clusterId}`);
  const lockFile=path.join(stateRoot,`${clusterId}.lock`);
  acquireLock(lockFile,{schema:'die.factory-asset.v1-job-browser-lock.v1',cluster_id:clusterId,job_id:jobId,owner_pid:process.pid,acquired_at:new Date().toISOString()});
  const startedAt=new Date().toISOString(),controlBaseUrl=`http://127.0.0.1:${Number(c.broker_control_port)}/`;
  let xvfb=null,broker=null,brokerStatus=null;const brokerOut=tailBuffer(),brokerErr=tailBuffer();
  const base={schema:'die.factory-asset.v1-job-browser-runtime.v1',cluster_id:clusterId,profile_id:c.profile_id,job_id:jobId,profile_dir:c.profile_dir,headful:true,virtual_display:displayNum,control_base_url:controlBaseUrl,credential_values_read:false,cookies_or_tokens_read:false,started_at:startedAt,status:'SPAWNING'};
  if(receiptPath)atomicJson(receiptPath,base);
  try{
    if(procHasProfile(c.profile_dir))throw new Error('E_JOB_BROWSER_PROFILE_ALREADY_OWNED');
    for(const name of ['SingletonLock','SingletonCookie','SingletonSocket'])fs.rmSync(path.join(c.profile_dir,name),{force:true});
    try{await fetchStatus(controlBaseUrl,500);throw new Error('E_JOB_BROWSER_CONTROL_PORT_BUSY')}catch(e){if(String(e?.message||e)==='E_JOB_BROWSER_CONTROL_PORT_BUSY')throw e}
    xvfb=spawn('/usr/bin/Xvfb',[`:${displayNum}`,'-screen','0','1920x1080x24','-nolisten','tcp'],{stdio:['ignore','ignore','pipe']});
    await waitDisplay(displayNum,xvfb);
    const brokerScript=path.join(dieHome,'company/muxia/scripts/linux/muxia-cluster-broker.mjs');
    broker=spawn('/usr/local/bin/node',[brokerScript,'--die-home',dieHome,'--cluster-id',clusterId,'--registry',path.join(dieHome,'company/factory-asset/registries/web-ai-clusters.v1.json'),'--state-root',brokerStateRoot,'--control-port',String(c.broker_control_port),'--browser-executable',browserExecutable,'--headless','false'],{env:{...process.env,DISPLAY:`:${displayNum}`,HOME:process.env.HOME||'/var/lib/muxia/service-home'},stdio:['ignore','pipe','pipe']});
    broker.stdout?.on('data',brokerOut.push);broker.stderr?.on('data',brokerErr.push);
    brokerStatus=await waitBrokerReady(controlBaseUrl,broker);
    const ready={...base,status:'WORK',browser_owner_pid:brokerStatus.browser_owner_pid,debug_host:brokerStatus.debug_host,debug_port:brokerStatus.debug_port,debug_url:`http://${brokerStatus.debug_host}:${brokerStatus.debug_port}`,broker_pid:broker.pid,xvfb_pid:xvfb.pid,ready_at:new Date().toISOString()};
    if(receiptPath)atomicJson(receiptPath,ready);
    let stopped=false;
    return{...ready,async stop({terminalEvidencePath,reason='JOB_TERMINAL'}={}){
      if(stopped)return receiptPath?safeReadJson(receiptPath):{...ready,status:'COLD',idempotent_replay:true};
      stopped=true;
      if(!terminalEvidencePath)throw new Error('E_LIFECYCLE_TERMINAL_EVIDENCE_REQUIRED');
      const terminal=validateTerminalEvidence(terminalEvidencePath);
      const terminalSha=crypto.createHash('sha256').update(fs.readFileSync(terminalEvidencePath)).digest('hex');
      let graceful=true,forced=false;
      if(broker&&broker.exitCode===null){
        broker.kill('SIGTERM');
        if(!await waitChildExit(broker,12000)){graceful=false;forced=true;broker.kill('SIGKILL');await waitChildExit(broker,3000)}
      }
      const debugClosed=ready.debug_url?await waitEndpointClosed(`${ready.debug_url}/json/version`):true;
      if(xvfb&&xvfb.exitCode===null){xvfb.kill('SIGTERM');if(!await waitChildExit(xvfb,3000)){xvfb.kill('SIGKILL');await waitChildExit(xvfb,1000)}}
      const controlClosed=await waitEndpointClosed(new URL('/v1/status',controlBaseUrl).toString());
      const profileGone=!procHasProfile(c.profile_dir);fs.rmSync(lockFile,{force:true});
      const out={...ready,status:(debugClosed&&controlClosed&&profileGone)?'COLD':'CLOSE_FAILED',close_reason:reason,terminal_evidence_path:terminalEvidencePath,terminal_evidence_sha256:terminalSha,terminal_status:terminal.status,browser_close_graceful:graceful,forced_process_cleanup:forced,debug_endpoint_closed:debugClosed,control_endpoint_closed:controlClosed,profile_process_gone:profileGone,lease_released:!fs.existsSync(lockFile),broker_exit_code:broker?.exitCode??null,xvfb_exit_code:xvfb?.exitCode??null,broker_stdout_tail:brokerOut.get(),broker_stderr_tail:brokerErr.get(),completed_at:new Date().toISOString()};
      if(receiptPath)atomicJson(receiptPath,out);
      if(out.status!=='COLD')throw new Error('E_JOB_BROWSER_CLOSE_INCOMPLETE');
      return out;
    }};
  }catch(error){
    if(broker&&broker.exitCode===null){broker.kill('SIGTERM');await waitChildExit(broker,3000);if(broker.exitCode===null)broker.kill('SIGKILL')}
    if(xvfb&&xvfb.exitCode===null){xvfb.kill('SIGTERM');await waitChildExit(xvfb,1500);if(xvfb.exitCode===null)xvfb.kill('SIGKILL')}
    fs.rmSync(lockFile,{force:true});
    const out={...base,status:'START_FAILED',error:String(error?.message||error).slice(0,800),broker_stdout_tail:brokerOut.get(),broker_stderr_tail:brokerErr.get(),completed_at:new Date().toISOString()};
    if(receiptPath)atomicJson(receiptPath,out);
    throw error;
  }
}
