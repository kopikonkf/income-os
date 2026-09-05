#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
const dieHome=path.resolve(arg('--die-home','/srv/die'));
const {PlaywrightChromiumDriver}=await import(pathToFileURL(path.join(dieHome,'company/muxia/dist/browser/playwright-driver.js')).href);
const {enforceTabBudget,MAX_TABS_PER_PRINCIPAL}=await import(pathToFileURL(path.join(dieHome,'company/browser/linux/tab_budget.mjs')).href);
const jobId=String(arg('--job-id','')).trim();
const promptFile=String(arg('--prompt-file','')).trim();
if(!/^[A-Za-z0-9][A-Za-z0-9._-]{4,120}$/.test(jobId)) throw new Error('E_JOB_ID');
if(!path.isAbsolute(promptFile)) throw new Error('E_PROMPT_FILE');
const prompt=fs.readFileSync(promptFile,'utf8').trim();
if(prompt.length<10||prompt.length>4000) throw new Error('E_PROMPT_LENGTH');

const profileDir='/var/lib/muxia/profiles/chatgpt-linux-a/browser';
const providerDir=path.join('/var/lib/die/workspaces',jobId,'provider');
fs.mkdirSync(providerDir,{recursive:true,mode:0o770});
const receipt={schema:'die.factory-asset.duckai-linux-canary.v1',task_id:'FA-118',job_id:jobId,provider_id:'duckai',transport_class:'BROWSER_CDP',browser_runtime_owner:'MUXIA',profile_id:'chatgpt-linux-a',prompt_sha256:crypto.createHash('sha256').update(prompt).digest('hex'),prompt_submitted_by_automation:false,output_extracted_by_automation:false,credential_values_read:false,cookies_or_tokens_read:false,operator_actions_after_dispatch:0,status:'FAILED'};
const now=()=>new Date().toISOString();

function imageType(bytes){
  if(bytes.length>=8&&bytes.subarray(0,8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]))) return ['image/png','png'];
  if(bytes.length>=3&&bytes[0]===0xff&&bytes[1]===0xd8&&bytes[2]===0xff) return ['image/jpeg','jpg'];
  if(bytes.length>=12&&bytes.toString('ascii',0,4)==='RIFF'&&bytes.toString('ascii',8,12)==='WEBP') return ['image/webp','webp'];
  return null;
}
function safeHost(raw){try{return new URL(raw).hostname.toLowerCase();}catch{return '';}}
function safePath(raw){try{return new URL(raw).pathname;}catch{return '';}}
function imageDimensions(bytes,mime){
  if(mime==='image/png'&&bytes.length>=24) return [bytes.readUInt32BE(16),bytes.readUInt32BE(20)];
  if(mime==='image/jpeg'){
    let i=2;
    while(i+9<bytes.length){
      if(bytes[i]!==0xff){i+=1;continue;}
      const marker=bytes[i+1];
      if(marker===0xd8||marker===0xd9){i+=2;continue;}
      if(i+4>bytes.length) break;
      const len=bytes.readUInt16BE(i+2);
      if([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)&&i+9<bytes.length) return [bytes.readUInt16BE(i+7),bytes.readUInt16BE(i+5)];
      if(len<2) break; i+=2+len;
    }
  }
  return [0,0];
}
function decodeDataUri(src){
  const comma=src.indexOf(','); if(comma<0) return null;
  const head=src.slice(0,comma); if(!head.startsWith('data:image/')||!head.includes(';base64')) return null;
  const raw=Buffer.from(src.slice(comma+1),'base64'); const typ=imageType(raw); if(!typ) return null;
  return {raw,mime:typ[0],ext:typ[1],method:'provider_data_uri_dom'};
}
async function sourceBytes(page,context,src){
  if(!src) return null;
  if(src.startsWith('data:image/')) return decodeDataUri(src);
  if(src.startsWith('blob:')){
    const b64=await page.evaluate(async url=>{const r=await fetch(url);const a=new Uint8Array(await r.arrayBuffer());let s='';for(let i=0;i<a.length;i+=0x8000)s+=String.fromCharCode(...a.subarray(i,i+0x8000));return btoa(s);},src).catch(()=>null);
    if(!b64) return null; const raw=Buffer.from(b64,'base64'); const typ=imageType(raw); return typ?{raw,mime:typ[0],ext:typ[1],method:'provider_blob_dom'}:null;
  }
  if(src.startsWith('http://')||src.startsWith('https://')){
    const r=await context.request.get(src,{timeout:30000}).catch(()=>null); if(!r||!r.ok()) return null;
    const raw=Buffer.from(await r.body()); const typ=imageType(raw); return typ?{raw,mime:typ[0],ext:typ[1],method:'provider_image_url_browser_context',host:safeHost(src)}:null;
  }
  return null;
}
async function domCandidates(page){
  return await page.evaluate(()=>{
    const out=[];
    const push=(src,w=0,h=0,kind='dom')=>{if(src&&typeof src==='string')out.push({src,w:Number(w)||0,h:Number(h)||0,kind});};
    for(const img of document.querySelectorAll('img')) push(img.currentSrc||img.src,img.naturalWidth,img.naturalHeight,'img');
    for(const source of document.querySelectorAll('source[srcset]')) for(const item of source.srcset.split(',')){const src=item.trim().split(/\\s+/)[0];push(src,0,0,'srcset');}
    for(const el of document.querySelectorAll('[style]')){const bg=getComputedStyle(el).backgroundImage||'';for(const m of bg.matchAll(/url\\(["']?(.*?)["']?\\)/g))push(m[1],el.clientWidth,el.clientHeight,'background');}
    for(const c of document.querySelectorAll('canvas')){if(c.width>=512&&c.height>=512){try{push(c.toDataURL('image/png'),c.width,c.height,'canvas');}catch{}}}
    return out;
  });
}

const driver=new PlaywrightChromiumDriver({executablePath:process.env.MUXIA_CHROME||'/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome',headless:true,launchTimeoutMs:30000,shutdownTimeoutMs:8000});
try{
  receipt.started_at=now();
  const handle=await driver.launch(profileDir); const context=handle.browser.contexts()[0];
  let page=context.pages().find(x=>x.url().includes('duck.ai'))||context.pages()[0]||await context.newPage();
  await enforceTabBudget(context,{preserve:[page],maxTabs:MAX_TABS_PER_PRINCIPAL});
  await page.goto('https://duck.ai/',{waitUntil:'domcontentloaded',timeout:60000}); await page.waitForTimeout(3500);
  const tools=page.getByRole('button',{name:'Tools'}); if(!await tools.isVisible().catch(()=>false)) throw new Error('E_TOOLS_UNAVAILABLE');
  await tools.click(); await page.waitForTimeout(400);
  const createImage=page.getByText('Create Image',{exact:true}); if(!await createImage.isVisible().catch(()=>false)) throw new Error('E_CREATE_IMAGE_MODE_UNAVAILABLE');
  await createImage.click(); await page.waitForTimeout(700);
  const composer=page.locator('textarea[aria-label="Ask anything privately"], textarea').first(); if(!await composer.isVisible().catch(()=>false)) throw new Error('E_COMPOSER_UNAVAILABLE');
  let createButton=page.getByRole('button',{name:'Create',exact:true}); if(!await createButton.isVisible().catch(()=>false)) createButton=page.getByRole('button',{name:'Send',exact:true}); if(!await createButton.isVisible().catch(()=>false)) createButton=page.locator('button[type="submit"]').first(); if(!await createButton.isVisible().catch(()=>false)) throw new Error('E_CREATE_BUTTON_UNAVAILABLE');
  const baseline=new Set((await domCandidates(page)).map(x=>x.src));
  const responseCandidates=[]; let committed=false; let challengeDetected=false;
  page.on('response',async response=>{
    if(!committed) return;
    try{
      const pathname=safePath(response.url());
      if(pathname==='/duckchat/v1/chat' && response.status()===418){challengeDetected=true; return;}
      if(pathname.startsWith('/assets/anomaly/')) return;
      const ct=(response.headers()['content-type']||'').toLowerCase(); if(!ct.startsWith('image/')) return;
      const raw=Buffer.from(await response.body()); const typ=imageType(raw); if(!typ||raw.length<30000) return;
      const dims=imageDimensions(raw,typ[0]); if(Math.min(...dims)<512) return; responseCandidates.push({raw,mime:typ[0],ext:typ[1],method:'provider_image_response_body',host:safeHost(response.url()),dims});
    }catch{}
  });
  receipt.preflight_at=now(); receipt.dispatch_started_at=now();
  await composer.fill(prompt); await createButton.click();
  receipt.dispatch_committed_at=now(); receipt.prompt_submitted_by_automation=true; committed=true;

  const deadline=Date.now()+180000; let found=null;
  while(Date.now()<deadline&&!found){
    while(responseCandidates.length&&!found){const c=responseCandidates.shift();if(c.raw.length>=30000)found=c;}
    if(found) break;
    for(const item of (await domCandidates(page)).reverse()){
      if(!item.src||baseline.has(item.src)) continue;
      if(Math.max(item.w,item.h)>0&&Math.max(item.w,item.h)<512) continue;
      const got=await sourceBytes(page,context,item.src); if(!got||got.raw.length<10000) continue;
      found={...got,dims:[item.w,item.h],dom_kind:item.kind}; break;
    }
    if(!found){
      const body=(await page.locator('body').innerText({timeout:3000}).catch(()=>'' )).toLowerCase();
      if(challengeDetected || body.includes('complete the following challenge') || body.includes('confirm this prompt was made by a human')) throw new Error('E_HUMAN_CHALLENGE_REQUIRED');
      if(/failed to create|couldn't create|could not create|image generation failed/.test(body)) throw new Error('E_PROVIDER_GENERATION_FAILED');
      await page.waitForTimeout(500);
    }
  }
  if(!found) throw new Error('E_BOUNDED_COMPLETION_TIMEOUT');
  receipt.generation_completed_at=now();
  const out=path.join(providerDir,`source-original.${found.ext}`); fs.writeFileSync(out,found.raw,{mode:0o660});
  receipt.output_extracted_by_automation=true; receipt.original_byte_acquisition_method=found.method; receipt.provider_original_url_host=found.host||undefined; receipt.dom_kind=found.dom_kind||undefined; receipt.local_path=out; receipt.mime=found.mime; receipt.dom_dimensions=found.dims; receipt.bytes=found.raw.length; receipt.sha256=crypto.createHash('sha256').update(found.raw).digest('hex'); receipt.status='PASS'; receipt.completed_at=now();
}catch(e){receipt.failure_code=String(e?.message||e).slice(0,240);receipt.completed_at=now();}
finally{await driver.stop().catch(()=>{});fs.writeFileSync(path.join(providerDir,'duckai-canary-result.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o660});console.log(JSON.stringify(receipt));}
process.exitCode=receipt.status==='PASS'?0:1;
