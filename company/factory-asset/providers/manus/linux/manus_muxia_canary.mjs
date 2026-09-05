#!/usr/bin/env node
import fs from 'node:fs'; import path from 'node:path'; import crypto from 'node:crypto'; import {pathToFileURL} from 'node:url';
function arg(n,f=null){const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;}
const dieHome=path.resolve(arg('--die-home','/srv/die'));
const {PlaywrightChromiumDriver}=await import(pathToFileURL(path.join(dieHome,'company/muxia/dist/browser/playwright-driver.js')).href);
const {enforceTabBudget,MAX_TABS_PER_PRINCIPAL}=await import(pathToFileURL(path.join(dieHome,'company/browser/linux/tab_budget.mjs')).href);
const jobId=String(arg('--job-id','')).trim(), promptFile=String(arg('--prompt-file','')).trim(); if(!/^[A-Za-z0-9][A-Za-z0-9._-]{4,120}$/.test(jobId))throw new Error('E_JOB_ID'); if(!path.isAbsolute(promptFile))throw new Error('E_PROMPT_FILE');
const prompt=fs.readFileSync(promptFile,'utf8').trim(); if(prompt.length<10||prompt.length>4000)throw new Error('E_PROMPT_LENGTH');
const profileDir='/var/lib/muxia/profiles/chatgpt-linux-a/browser', providerDir=path.join('/var/lib/die/workspaces',jobId,'provider'); fs.mkdirSync(providerDir,{recursive:true,mode:0o770});
const receipt={schema:'die.factory-asset.manus-linux-canary.v1',task_id:'FA-116',job_id:jobId,provider_id:'manus',transport_class:'BROWSER_CDP',browser_runtime_owner:'MUXIA',profile_id:'chatgpt-linux-a',prompt_sha256:crypto.createHash('sha256').update(prompt).digest('hex'),prompt_submitted_by_automation:false,output_extracted_by_automation:false,credential_values_read:false,cookies_or_tokens_read:false,operator_actions_after_dispatch:0,status:'FAILED'};
const now=()=>new Date().toISOString();
function imageType(b){if(b.length>=8&&b.subarray(0,8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a])))return['image/png','png'];if(b.length>=3&&b[0]===0xff&&b[1]===0xd8&&b[2]===0xff)return['image/jpeg','jpg'];if(b.length>=12&&b.toString('ascii',0,4)==='RIFF'&&b.toString('ascii',8,12)==='WEBP')return['image/webp','webp'];return null;}
function safeHost(raw){try{return new URL(raw).hostname.toLowerCase()}catch{return''}}
const driver=new PlaywrightChromiumDriver({executablePath:process.env.MUXIA_CHROME||'/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome',headless:true,launchTimeoutMs:30000,shutdownTimeoutMs:8000});
try{
 receipt.started_at=now(); const h=await driver.launch(profileDir), c=h.browser.contexts()[0]; let p=c.pages().find(x=>x.url().includes('manus.im'))||c.pages()[0]||await c.newPage(); await enforceTabBudget(c,{preserve:[p],maxTabs:MAX_TABS_PER_PRINCIPAL});
 await p.goto('https://manus.im/app',{waitUntil:'domcontentloaded',timeout:60000}); await p.waitForTimeout(5000);
 const body=(await p.locator('body').innerText().catch(()=>'' )).toLowerCase(); if(body.includes('log in')&& !body.includes('free plan'))throw new Error('E_AUTH_REQUIRED');
 const editor=p.locator('.tiptap.ProseMirror[contenteditable="true"]').first(); const editorDeadline=Date.now()+20000; while(Date.now()<editorDeadline && !await editor.isVisible().catch(()=>false)) await p.waitForTimeout(500); if(!await editor.isVisible().catch(()=>false))throw new Error('E_EDITOR_UNAVAILABLE'); receipt.preflight_at=now();
 let dispatchCommitted=false; const candidates=[];
 p.on('response',async r=>{if(!dispatchCommitted)return; const host=safeHost(r.url()); if(!host.endsWith('manuscdn.com')||host==='files.manuscdn.com')return; try{const ct=(r.headers()['content-type']||'').split(';')[0].toLowerCase(); if(!ct.startsWith('image/'))return; const raw=Buffer.from(await r.body()); const typ=imageType(raw); if(!typ||raw.length<50000)return; candidates.push({raw,mime:typ[0],ext:typ[1],host});}catch{}});
 receipt.dispatch_started_at=now(); await editor.fill(prompt); await editor.press('Enter'); receipt.dispatch_committed_at=now(); receipt.prompt_submitted_by_automation=true; dispatchCommitted=true;
 const deadline=Date.now()+300000; let found=null; while(Date.now()<deadline&&!found){if(candidates.length)found=candidates.shift(); if(!found)await p.waitForTimeout(1000);} if(!found)throw new Error('E_BOUNDED_COMPLETION_TIMEOUT');
 receipt.generation_completed_at=now(); const out=path.join(providerDir,`source-original.${found.ext}`); fs.writeFileSync(out,found.raw,{mode:0o660}); receipt.output_extracted_by_automation=true; receipt.original_byte_acquisition_method='BROWSER_CDP generated manuscdn asset response/body'; receipt.provider_original_url_host=found.host; receipt.local_path=out; receipt.mime=found.mime; receipt.bytes=found.raw.length; receipt.sha256=crypto.createHash('sha256').update(found.raw).digest('hex'); receipt.status='PASS'; receipt.completed_at=now();
}catch(e){receipt.failure_code=String(e?.message||e).slice(0,240);receipt.completed_at=now();}
finally{await driver.stop().catch(()=>{});fs.writeFileSync(path.join(providerDir,'manus-canary-result.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o660});console.log(JSON.stringify(receipt));}
process.exitCode=receipt.status==='PASS'?0:1;