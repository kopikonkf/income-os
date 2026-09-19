#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import process from 'node:process';
import { chromium } from '/srv/die/company/muxia/node_modules/playwright/index.mjs';

const CFG_PATH='/home/kopiko/die-sessions/NEXABURST-H01-P001/config/nexaburst.json';
const cfg=JSON.parse(fs.readFileSync(CFG_PATH,'utf8'));
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{
  if(v.startsWith('--')) a.push([v.slice(2), x[i+1] && !x[i+1].startsWith('--') ? x[i+1] : 'true']);
  return a;
},[]));

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const sha256=b=>crypto.createHash('sha256').update(b).digest('hex');
const slug=s=>String(s||'asset').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,72)||'asset';
const iso=()=>new Date().toISOString();
const stateRoot=cfg.state_root;
const receiptRoot=cfg.receipt_root;
fs.mkdirSync(stateRoot,{recursive:true});
fs.mkdirSync(receiptRoot,{recursive:true});

const lockPath=path.join(stateRoot, cfg.profile_id+'.inflight.lock');
const cooldownPath=path.join(stateRoot, cfg.profile_id+'.cooldown.json');
const ledgerPath=path.join(receiptRoot,'nexaburst-ledger.jsonl');
let lockFd=null;

function pidAlive(pid){try{process.kill(pid,0);return true}catch{return false}}
function acquireLock(){
  if(fs.existsSync(lockPath)){
    try{
      const old=JSON.parse(fs.readFileSync(lockPath,'utf8'));
      if(pidAlive(Number(old.pid))) throw new Error('E_PROFILE_INFLIGHT');
    }catch(e){if(e.message==='E_PROFILE_INFLIGHT') throw e}
    fs.rmSync(lockPath,{force:true});
  }
  lockFd=fs.openSync(lockPath,'wx',0o640);
  fs.writeFileSync(lockFd,JSON.stringify({pid:process.pid,started_at:iso()})+'\n');
}
function releaseLock(){
  try{if(lockFd!==null)fs.closeSync(lockFd)}catch{}
  try{fs.rmSync(lockPath,{force:true})}catch{}
}
function appendLedger(v){fs.appendFileSync(ledgerPath,JSON.stringify(v)+'\n',{encoding:'utf8',mode:0o640})}
function setCooldown(ms,reason){
  fs.writeFileSync(cooldownPath,JSON.stringify({next_allowed_ms:Date.now()+ms,reason,updated_at:iso()},null,2)+'\n');
}
async function honorCooldown(){
  if(!fs.existsSync(cooldownPath))return;
  try{
    const d=JSON.parse(fs.readFileSync(cooldownPath,'utf8'));
    const wait=Math.max(0,Number(d.next_allowed_ms||0)-Date.now());
    if(wait>0){console.error('NEXABURST_COOLDOWN wait_ms='+wait+' reason='+(d.reason||'unknown'));await sleep(wait)}
  }catch{}
}
function buildPrompt(noun,style){
  const rules={
    'isolated-object':`Create one ${noun} as a single isolated object, centered and fully visible, clean pure white background, crisp natural edges, commercially useful stock composition, realistic materials and proportions, soft studio lighting, no text, no logo, no trademark, no brand, no watermark, no extra objects.`,
    'flat':`Create one ${noun} as a clean flat illustration, isolated and centered on a pure white background, simple geometric shapes, balanced proportions, crisp edges, commercial stock design component, no text, no logo, no trademark, no brand, no watermark, no extra objects.`,
    'cartoon':`Create one ${noun} as a polished friendly cartoon illustration, isolated and centered on a pure white background, clear silhouette, clean edges, tasteful color palette, commercial stock design component, no text, no logo, no trademark, no brand, no watermark, no extra objects.`,
    'watercolor':`Create one ${noun} as a refined watercolor illustration, isolated and centered on a clean white paper background, clear recognizable silhouette, delicate natural pigment texture, commercial stock design component, no text, no logo, no trademark, no brand, no watermark, no extra objects.`
  };
  return rules[style] || rules['isolated-object'];
}
function mediaInfo(buf){
  if(buf.length>=24 && buf.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))
    return {format:'PNG',width:buf.readUInt32BE(16),height:buf.readUInt32BE(20)};
  if(buf.length>=4 && buf[0]===0xff && buf[1]===0xd8){
    let i=2; const sof=new Set([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf]);
    while(i+4<=buf.length){
      if(buf[i]!==0xff){i++;continue} let m=buf[i+1]; i+=2;
      if(m===0xd8||m===0xd9||(m>=0xd0&&m<=0xd7))continue;
      if(i+2>buf.length)break; const n=buf.readUInt16BE(i); if(n<2||i+n>buf.length)break;
      if(sof.has(m)&&n>=7)return {format:'JPEG',height:buf.readUInt16BE(i+3),width:buf.readUInt16BE(i+5)};
      i+=n;
    }
    return {format:'JPEG',width:null,height:null};
  }
  return {format:'UNKNOWN',width:null,height:null};
}
async function main(){
  acquireLock();
  const stat=fs.statfsSync(cfg.raw_root);
  const freeBytes=Number(stat.bavail)*Number(stat.bsize);
  const minFree=Number(cfg.raw_min_free_gib||5)*1024**3;
  if(freeBytes<minFree) throw new Error('E_RAW_STORAGE_GATE_FREE_BYTES_'+freeBytes);
  await honorCooldown();
  const cdp=`http://${cfg.cdp_host}:${cfg.cdp_port}`;
  const browser=await chromium.connectOverCDP(cdp,{timeout:15000});
  const context=browser.contexts()[0];
  if(!context)throw new Error('E_CDP_CONTEXT_MISSING');
  let page=context.pages().find(p=>p.url().includes('nexabot.id'));
  if(!page){page=await context.newPage();await page.goto(cfg.landing_url,{waitUntil:'domcontentloaded',timeout:30000})}
  if(!page.url().includes('nexabot.id'))await page.goto(cfg.landing_url,{waitUntil:'domcontentloaded',timeout:30000});

  const account=await page.evaluate(async()=>{
    const r=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
    let j={};try{j=await r.json()}catch{}
    return {http:r.status,authenticated:!!j.authenticated,unlimited_active:!!j.unlimited_active,unlimited_until:j.unlimited_until||null};
  });
  if(!account.authenticated)throw new Error('E_AUTH_REQUIRED');
  if(!account.unlimited_active)throw new Error('E_UNLIMITED_INACTIVE');

  const noun=args.noun||'ceramic mug';
  const style=args.style||'isolated-object';
  const prompt=args.prompt||buildPrompt(noun,style);
  const promptAuthority=args['prompt-authority']||'NEXABURST_CANARY_TEMPLATE_V0';
  const compiledContractSha256=args['compiled-contract-sha256']||null;
  const aspect=Number(args.aspect||1);
  const assetId=args['asset-id']||`OBJ-${slug(noun)}-${slug(style)}-${Date.now()}`;
  const promptSha=sha256(Buffer.from(prompt));
  let submit=null;

  for(let attempt=1;attempt<=Number(cfg.submit_retry_limit||4);attempt++){
    submit=await page.evaluate(async ({prompt,aspect})=>{
      const me=await (await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'})).json();
      const payload={mode:'img',prompt,aspect,use_unlimited:true,telegram_id:me?.user?.telegramid||'web'};
      const r=await fetch('/api/v1/generate',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});
      let j={};try{j=await r.json()}catch{}
      return {http:r.status,ok:r.ok&&!!j.ok,job_id:j.job_id||null,status:j.status||null,mode_type:j.mode_type||null,est_seconds:j.est_seconds||null,error:j.error||null};
    },{prompt,aspect});
    if(submit.ok)break;
    const ms=submit.http===429?Number(cfg.rate_limit_cooldown_ms):Number(cfg.busy_cooldown_ms);
    console.error(`NEXABURST_SUBMIT_RETRY attempt=${attempt} http=${submit.http} wait_ms=${ms}`);
    setCooldown(ms,'submit_http_'+submit.http);
    if(attempt===Number(cfg.submit_retry_limit||4))throw new Error('E_SUBMIT:'+JSON.stringify(submit));
    await sleep(ms);
  }

  const jobId=submit.job_id;
  const started=Date.now();
  let lastProgress='';
  let job=null;
  while(Date.now()-started<Number(cfg.job_timeout_ms||240000)){
    const res=await page.evaluate(async id=>{
      const r=await fetch('/api/v1/jobs/'+id,{credentials:'same-origin',cache:'no-store'});
      let j={};try{j=await r.json()}catch{}
      return {http:r.status,ok:r.ok&&!!j.ok,job:j.job||null,error:j.error||null};
    },jobId);
    if(!res.ok)throw new Error('E_POLL:'+JSON.stringify({http:res.http,error:res.error}));
    job=res.job;
    const prog=String(job?.progress||job?.status_text||job?.status||'');
    if(prog!==lastProgress){
      lastProgress=prog;
      appendLedger({schema:'die.h01.nexaburst.event.v1',kind:'PROGRESS',job_id:jobId,asset_id:assetId,status:job?.status,progress:prog,at:iso()});
      console.error(`NEXABURST_PROGRESS job=${jobId} status=${job?.status} progress=${prog}`);
    }
    if(job?.status==='done'||job?.status==='failed')break;
    await sleep(Number(cfg.poll_ms||2000));
  }
  if(!job||job.status!=='done'){
    setCooldown(Number(cfg.busy_cooldown_ms),'job_failed_or_timeout');
    throw new Error('E_JOB_TERMINAL:'+JSON.stringify({job_id:jobId,status:job?.status,error:job?.error}));
  }

  const dl=await page.evaluate(async id=>{
    const r=await fetch('/api/v1/jobs/'+id+'/download?download=1',{credentials:'same-origin',cache:'no-store'});
    const a=new Uint8Array(await r.arrayBuffer());
    let s='';for(let i=0;i<a.length;i+=32768)s+=String.fromCharCode(...a.subarray(i,i+32768));
    return {http:r.status,ok:r.ok,mime:r.headers.get('content-type')||'',disposition:r.headers.get('content-disposition')||'',b64:btoa(s)};
  },jobId);
  if(!dl.ok)throw new Error('E_DOWNLOAD_HTTP_'+dl.http);
  const bytes=Buffer.from(dl.b64,'base64');
  const info=mediaInfo(bytes);
  const ext=dl.mime.includes('png')?'.png':'.jpg';
  const day=new Date().toISOString().slice(0,10);
  const dir=path.join(cfg.raw_root,day);
  fs.mkdirSync(dir,{recursive:true});
  const out=path.join(dir,`${assetId}__${jobId}${ext}`);
  fs.writeFileSync(out,bytes,{mode:0o640});
  const digest=sha256(bytes);

  const receipt={
    schema:'die.h01.nexaburst.generation-receipt.v1',
    engine_id:cfg.engine_id,profile_id:cfg.profile_id,transport:'WEB_SESSION_INTERNAL_JOB_API',
    billing:'UNLIMITED',asset_id:assetId,noun,style,prompt,prompt_sha256:promptSha,prompt_authority:promptAuthority,compiled_contract_sha256:compiledContractSha256,aspect,
    job_id:jobId,submit:{mode_type:submit.mode_type,est_seconds:submit.est_seconds},
    result:{status:'DONE',provider_progress:lastProgress,source_path:out,sha256:digest,bytes:bytes.length,mime:dl.mime,format:info.format,width:info.width,height:info.height},
    timing:{started_at:new Date(started).toISOString(),finished_at:iso(),elapsed_ms:Date.now()-started},
    authority:{submission_authorized:false,publication_authorized:false},
    secrets:{credential_values_read:false,cookies_or_tokens_read:false}
  };
  const receiptPath=path.join(receiptRoot,`${assetId}__${jobId}.json`);
  fs.writeFileSync(receiptPath,JSON.stringify(receipt,null,2)+'\n',{mode:0o640});
  appendLedger({schema:'die.h01.nexaburst.event.v1',kind:'ARTIFACT_CREATED',job_id:jobId,asset_id:assetId,sha256:digest,path:out,at:iso()});
  const queue={schema:'die.h01.nexaburst.v2-queue-item.v1',asset_id:assetId,noun,style,job_id:jobId,source_path:out,source_sha256:digest,generation_receipt:receiptPath,enqueued_at:iso()};
  fs.appendFileSync(path.join(stateRoot,'v2-queue.jsonl'),JSON.stringify(queue)+'\n',{encoding:'utf8',mode:0o640});
  setCooldown(Number(cfg.success_cooldown_ms||2000),'success');
  fs.writeFileSync(path.join(stateRoot,'last-success.json'),JSON.stringify(receipt,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:'DONE',asset_id:assetId,job_id:jobId,path:out,sha256:digest,width:info.width,height:info.height,bytes:bytes.length,elapsed_ms:receipt.timing.elapsed_ms,queued_for_v2:true}));
}

main().then(()=>{
  releaseLock();
  process.exit(0);
}).catch(err=>{
  const row={schema:'die.h01.nexaburst.event.v1',kind:'ERROR',error:String(err?.message||err),at:iso()};
  try{appendLedger(row)}catch{}
  console.error('NEXABURST_ERROR '+row.error);
  releaseLock();
  process.exit(2);
});
