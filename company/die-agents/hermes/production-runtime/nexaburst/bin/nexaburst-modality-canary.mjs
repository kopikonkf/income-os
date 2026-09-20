#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import process from 'node:process';
import { chromium } from '/srv/die/company/muxia/node_modules/playwright/index.mjs';

const CFG='/home/kopiko/die-sessions/NEXABURST-H01-P001/config/nexaburst.json';
const cfg=JSON.parse(fs.readFileSync(CFG,'utf8'));
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{
  if(v.startsWith('--')) a.push([v.slice(2),x[i+1]&&!x[i+1].startsWith('--')?x[i+1]:'true']);
  return a;
},[]));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const iso=()=>new Date().toISOString();
const canaryId=String(args['canary-id']||('MOD-'+Date.now())).replace(/[^A-Za-z0-9._-]/g,'-');
const mode=String(args.mode||'img');
const prompt=String(args.prompt||'Create a simple editable native SVG vector icon of a paper airplane. Return SVG, not a raster image.');
const root='/var/lib/die/h01/nexaburst/canary/modality';
const outDir=path.join(root,canaryId);
fs.mkdirSync(outDir,{recursive:true});
const lockPath=path.join(cfg.state_root,cfg.profile_id+'.inflight.lock');
let lockFd=null;
function pidAlive(pid){try{process.kill(pid,0);return true}catch{return false}}
function acquireLock(){
  if(fs.existsSync(lockPath)){
    try{const old=JSON.parse(fs.readFileSync(lockPath,'utf8'));if(pidAlive(Number(old.pid)))throw new Error('E_PROFILE_INFLIGHT')}catch(e){if(e.message==='E_PROFILE_INFLIGHT')throw e}
    fs.rmSync(lockPath,{force:true});
  }
  lockFd=fs.openSync(lockPath,'wx',0o640);fs.writeFileSync(lockFd,JSON.stringify({pid:process.pid,canary_id:canaryId,started_at:iso()})+'\n');
}
function releaseLock(){try{if(lockFd!==null)fs.closeSync(lockFd)}catch{}try{fs.rmSync(lockPath,{force:true})}catch{}}
async function honorCooldown(){
  const p=path.join(cfg.state_root,cfg.profile_id+'.cooldown.json');
  if(!fs.existsSync(p))return;
  try{const d=JSON.parse(fs.readFileSync(p,'utf8'));const wait=Math.max(0,Number(d.next_allowed_ms||0)-Date.now());if(wait>0)await sleep(wait)}catch{}
}
function classify(buf,mime){
  const head=buf.subarray(0,512).toString('utf8').trimStart().toLowerCase();
  if(String(mime).includes('svg')||head.startsWith('<svg')||head.startsWith('<?xml')&&head.includes('<svg'))return 'SVG';
  if(buf.length>=8&&buf.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))return 'PNG';
  if(buf.length>=2&&buf[0]===0xff&&buf[1]===0xd8)return 'JPEG';
  if(buf.length>=12&&buf.subarray(0,4).toString()==='RIFF'&&buf.subarray(8,12).toString()==='WEBP')return 'WEBP';
  if(buf.length>=12&&buf.subarray(4,8).toString()==='ftyp')return 'MP4_OR_ISOBMFF';
  return 'UNKNOWN';
}
async function main(){
  acquireLock();await honorCooldown();
  const browser=await chromium.connectOverCDP(`http://${cfg.cdp_host}:${cfg.cdp_port}`,{timeout:15000});
  const context=browser.contexts()[0];if(!context)throw new Error('E_CDP_CONTEXT_MISSING');
  let page=context.pages().find(p=>p.url().includes('nexabot.id'));
  if(!page){page=await context.newPage();await page.goto(cfg.landing_url,{waitUntil:'domcontentloaded',timeout:30000})}
  const account=await page.evaluate(async()=>{const r=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});let j={};try{j=await r.json()}catch{};return {http:r.status,authenticated:!!j.authenticated,unlimited_active:!!j.unlimited_active,telegram_id:j?.user?.telegramid||'web'}});
  if(!account.authenticated)throw new Error('E_AUTH_REQUIRED');if(!account.unlimited_active)throw new Error('E_UNLIMITED_INACTIVE');
  const submitted=await page.evaluate(async ({mode,prompt,telegram_id})=>{const r=await fetch('/api/v1/generate',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({mode,prompt,aspect:1,use_unlimited:true,telegram_id})});let j={};try{j=await r.json()}catch{};return {http:r.status,ok:r.ok&&!!j.ok,job_id:j.job_id||null,status:j.status||null,mode_type:j.mode_type||null,error:j.error||null}}, {mode,prompt,telegram_id:account.telegram_id});
  if(!submitted.ok)throw new Error('E_SUBMIT:'+JSON.stringify(submitted));
  const started=Date.now();let job=null;
  while(Date.now()-started<240000){
    const r=await page.evaluate(async id=>{const z=await fetch('/api/v1/jobs/'+id,{credentials:'same-origin',cache:'no-store'});let j={};try{j=await z.json()}catch{};return {http:z.status,ok:z.ok&&!!j.ok,job:j.job||null,error:j.error||null}},submitted.job_id);
    if(!r.ok)throw new Error('E_POLL:'+JSON.stringify(r));job=r.job;if(job?.status==='done'||job?.status==='failed')break;await sleep(2000);
  }
  if(!job||job.status!=='done')throw new Error('E_JOB_TERMINAL:'+JSON.stringify({job_id:submitted.job_id,status:job?.status||null,error:job?.error||''}));
  const dl=await page.evaluate(async id=>{const r=await fetch('/api/v1/jobs/'+id+'/download?download=1',{credentials:'same-origin',cache:'no-store'});const a=new Uint8Array(await r.arrayBuffer());let s='';for(let i=0;i<a.length;i+=32768)s+=String.fromCharCode(...a.subarray(i,i+32768));return {http:r.status,ok:r.ok,mime:r.headers.get('content-type')||'',disposition:r.headers.get('content-disposition')||'',b64:btoa(s)}},submitted.job_id);
  if(!dl.ok)throw new Error('E_DOWNLOAD_HTTP_'+dl.http);
  const bytes=Buffer.from(dl.b64,'base64'),format=classify(bytes,dl.mime),ext={SVG:'.svg',PNG:'.png',JPEG:'.jpg',WEBP:'.webp',MP4_OR_ISOBMFF:'.mp4'}[format]||'.bin';
  const out=path.join(outDir,'provider-output'+ext);fs.writeFileSync(out,bytes,{mode:0o640});
  const receipt={schema:'die.h01.nexaburst.modality-canary.v1',canary_id:canaryId,status:'DONE',requested_mode:mode,requested_requirement:'NATIVE_SVG_VECTOR',prompt,prompt_sha256:sha(Buffer.from(prompt)),job_id:submitted.job_id,provider_mode_type:submitted.mode_type,mime:dl.mime,disposition:dl.disposition,detected_format:format,bytes:bytes.length,sha256:sha(bytes),output_path:out,elapsed_ms:Date.now()-started,native_svg_pass:format==='SVG',queued_for_v2:false,created_at:iso()};
  fs.writeFileSync(path.join(outDir,'receipt.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o640});console.log(JSON.stringify(receipt));
  await browser.close();
}
main().then(()=>{releaseLock();process.exit(0)}).catch(e=>{const r={schema:'die.h01.nexaburst.modality-canary.v1',canary_id:canaryId,status:'FAILED',error:String(e?.message||e),created_at:iso(),queued_for_v2:false};try{fs.writeFileSync(path.join(outDir,'receipt.json'),JSON.stringify(r,null,2)+'\n',{mode:0o640})}catch{}console.error(JSON.stringify(r));releaseLock();process.exit(2)});
