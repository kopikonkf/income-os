#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';

const CFG={
  'die-lnx-executive-001':{profile:'/var/lib/die/executive/browser-profile',status:'/var/lib/die/executive/browser-status.json',script:'/srv/die/company/executive/linux/operator_browser.mjs',display:103,receiptDir:'/var/lib/die/executive/job-browser-receipts'},
  'die-lnx-division-001':{profile:'/var/lib/die/division01/browser-profile',status:'/var/lib/die/division01/browser-status.json',script:'/srv/die/company/division/division001/linux/operator_browser.mjs',display:104,receiptDir:'/var/lib/die/division01/job-browser-receipts'},
};
const sleep=(ms)=>new Promise((r)=>setTimeout(r,ms));
function atomic(file,v){fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});const t=`${file}.tmp-${process.pid}`;fs.writeFileSync(t,JSON.stringify(v,null,2)+'\n',{mode:0o640});fs.renameSync(t,file)}
async function waitExit(c,ms){if(!c||c.exitCode!==null)return true;return await new Promise((resolve)=>{let done=false,timer;const finish=(v)=>{if(done)return;done=true;clearTimeout(timer);c.off('exit',onExit);resolve(v)};const onExit=()=>finish(true);c.once('exit',onExit);timer=setTimeout(()=>finish(false),ms)})}
function procProfile(profile){
  for(const e of fs.readdirSync('/proc').filter((x)=>/^\d+$/.test(x))){
    try{const s=fs.readFileSync(`/proc/${e}/cmdline`).toString().replace(/\0/g,' ');if(s.includes(`--user-data-dir=${profile}`)&&(s.includes('chrome')||s.includes('chromium')))return Number(e)}catch{}
  }
  return null;
}
async function waitStatus(cfg,started,child,timeout=45000){
  const end=Date.now()+timeout;let v=null;
  while(Date.now()<end){
    if(child.exitCode!==null)throw new Error(`E_PRINCIPAL_BROWSER_EXIT:${child.exitCode}`);
    try{v=JSON.parse(fs.readFileSync(cfg.status,'utf8'));if(Date.parse(v.observed_at)>=started&&v.debugHost==='127.0.0.1'&&['READY','AUTH_REQUIRED','OPERATOR_CHECK_REQUIRED'].includes(v.state))return v}catch{}
    await sleep(150);
  }
  throw new Error('E_PRINCIPAL_BROWSER_STATUS_TIMEOUT');
}

export async function withPrincipalJobBrowser({principalId,jobId,work,terminalEvidencePath=null}={}){
  const cfg=CFG[principalId];if(!cfg)throw new Error('E_PRINCIPAL_BROWSER_PRINCIPAL');
  if(procProfile(cfg.profile))throw new Error('E_PRINCIPAL_PROFILE_BUSY');
  const safeJob=String(jobId).replace(/[^A-Za-z0-9_.-]/g,'_');
  const receipt=path.join(cfg.receiptDir,`${safeJob}.json`),started=Date.now();
  let xvfb=null,owner=null,status=null,workError=null,result=null;
  const base={schema:'die.cognition.job-browser-runtime.v1',principal_id:principalId,job_id:jobId,profile:cfg.profile,headful:true,virtual_display:cfg.display,credential_values_read:false,cookies_or_tokens_read:false,started_at:new Date(started).toISOString(),status:'SPAWNING'};
  atomic(receipt,base);
  try{
    xvfb=spawn('/usr/bin/Xvfb',[`:${cfg.display}`,'-screen','0','1920x1080x24','-nolisten','tcp'],{stdio:'ignore'});
    for(let i=0;i<100&&!fs.existsSync(`/tmp/.X11-unix/X${cfg.display}`);i++){if(xvfb.exitCode!==null)throw new Error('E_PRINCIPAL_XVFB_EXIT');await sleep(100)}
    owner=spawn('/usr/local/bin/node',[cfg.script,'launch'],{env:{...process.env,DISPLAY:`:${cfg.display}`,HOME:'/home/kopiko'},stdio:['ignore','pipe','pipe']});
    status=await waitStatus(cfg,started,owner);
    atomic(receipt,{...base,status:'WORK',browser_pid:status.browserPid,debug_host:status.debugHost,debug_port:status.debugPort,ready_state:status.state,ready_at:new Date().toISOString()});
    if(status.state!=='READY')throw new Error(`E_AUTH_REPAIR_REQUIRED:${principalId}:${status.state}`);
    try{
      result=await work();
      if(!terminalEvidencePath&&result?.receipt_ref)terminalEvidencePath=result.receipt_ref;
    }catch(error){workError=error}
    if(workError){
      const fail={schema:'die.cognition.job-browser-terminal.v1',status:'FAILED',principal_id:principalId,job_id:jobId,error:String(workError?.message||workError).slice(0,800),completed_at:new Date().toISOString()};
      terminalEvidencePath=path.join(cfg.receiptDir,`${safeJob}.terminal.json`);atomic(terminalEvidencePath,fail);
    }
    if(!terminalEvidencePath||!fs.existsSync(terminalEvidencePath)){
      const fail={schema:'die.cognition.job-browser-terminal.v1',status:'FAILED',principal_id:principalId,job_id:jobId,error:'E_TERMINAL_EVIDENCE_MISSING',completed_at:new Date().toISOString()};
      terminalEvidencePath=path.join(cfg.receiptDir,`${safeJob}.terminal.json`);atomic(terminalEvidencePath,fail);
      if(!workError)workError=new Error('E_TERMINAL_EVIDENCE_MISSING');
    }
    if(owner&&owner.exitCode===null){owner.kill('SIGTERM');if(!await waitExit(owner,10000)){owner.kill('SIGKILL');await waitExit(owner,2000)}}
    if(xvfb&&xvfb.exitCode===null){xvfb.kill('SIGTERM');if(!await waitExit(xvfb,2500)){xvfb.kill('SIGKILL');await waitExit(xvfb,1000)}}
    const profileGone=!procProfile(cfg.profile),sha=crypto.createHash('sha256').update(fs.readFileSync(terminalEvidencePath)).digest('hex');
    atomic(receipt,{...base,status:profileGone?'COLD':'CLOSE_FAILED',browser_pid:status?.browserPid||null,debug_host:status?.debugHost||null,debug_port:status?.debugPort||null,terminal_evidence_path:terminalEvidencePath,terminal_evidence_sha256:sha,profile_process_gone:profileGone,completed_at:new Date().toISOString()});
    if(!profileGone)throw new Error('E_PRINCIPAL_BROWSER_CLOSE_INCOMPLETE');
    if(workError)throw workError;
    return result;
  }catch(error){
    if(owner&&owner.exitCode===null){owner.kill('SIGTERM');await waitExit(owner,3000)}
    if(xvfb&&xvfb.exitCode===null){xvfb.kill('SIGTERM');await waitExit(xvfb,1500)}
    atomic(receipt,{...base,status:'FAILED',error:String(error?.message||error).slice(0,800),completed_at:new Date().toISOString()});
    throw error;
  }
}
