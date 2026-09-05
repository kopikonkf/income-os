#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

function arg(name, fallback = null) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : fallback;
}

const dieHome = path.resolve(arg('--die-home', '/srv/die'));
const { PlaywrightChromiumDriver } = await import(pathToFileURL(path.join(dieHome, 'company/muxia/dist/browser/playwright-driver.js')).href);
const { enforceTabBudget, MAX_TABS_PER_PRINCIPAL } = await import(pathToFileURL(path.join(dieHome, 'company/browser/linux/tab_budget.mjs')).href);
const jobId = String(arg('--job-id', '')).trim();
const promptFile = String(arg('--prompt-file', '')).trim();
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{4,120}$/.test(jobId)) throw new Error('E_JOB_ID');
if (!path.isAbsolute(promptFile)) throw new Error('E_PROMPT_FILE');
const prompt = fs.readFileSync(promptFile, 'utf8').trim();
if (prompt.length < 10 || prompt.length > 4000) throw new Error('E_PROMPT_LENGTH');

const profileDir = '/var/lib/muxia/profiles/chatgpt-linux-a/browser';
const providerDir = path.join('/var/lib/die/workspaces', jobId, 'provider');
const chrome = process.env.MUXIA_CHROME || '/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome';
const generationTimeoutMs = 180000;
const downloadTimeoutMs = 20000;
const composerSelectors = ['[contenteditable="true"][role="textbox"]','.ql-editor[contenteditable="true"]','[contenteditable="true"]','textarea'];
const signInSelector = 'a:has-text("Sign in"), button:has-text("Sign in"), [aria-label*="sign in" i]';
const downloadSelector = 'button[aria-label*="download" i], [role="button"][aria-label*="download" i], a[aria-label*="download" i], button[title*="download" i], a[title*="download" i], a[download]';
const receipt = {
  schema: 'die.factory-asset.gemini-linux-canary.v1', task_id: 'FA-114', job_id: jobId,
  provider_id: 'gemini', transport_class: 'BROWSER_CDP', browser_runtime_owner: 'MUXIA',
  profile_id: 'chatgpt-linux-a', prompt_sha256: crypto.createHash('sha256').update(prompt).digest('hex'),
  prompt_submitted_by_automation: false, output_extracted_by_automation: false,
  credential_values_read: false, cookies_or_tokens_read: false, operator_actions_after_dispatch: 0,
  status: 'FAILED',
};
const now = () => new Date().toISOString();

function mimeAndExt(bytes) {
  if (bytes.length >= 8 && bytes.subarray(0,8).equals(Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]))) return ['image/png','png'];
  if (bytes.length >= 3 && bytes[0]===0xff && bytes[1]===0xd8 && bytes[2]===0xff) return ['image/jpeg','jpg'];
  if (bytes.length >= 12 && bytes.toString('ascii',0,4)==='RIFF' && bytes.toString('ascii',8,12)==='WEBP') return ['image/webp','webp'];
  throw new Error('E_IMAGE_MAGIC');
}
async function visibleCount(page, selector) {
  const loc = page.locator(selector); let n=0;
  for (let i=0;i<await loc.count();i+=1) if (await loc.nth(i).isVisible().catch(()=>false)) n+=1;
  return n;
}
async function findComposer(page) {
  const deadline=Date.now()+15000;
  while(Date.now()<deadline){
    if(await visibleCount(page,signInSelector)) throw new Error('E_AUTH_REQUIRED');
    for(const selector of composerSelectors){ const loc=page.locator(selector); for(let i=0;i<await loc.count();i+=1){const c=loc.nth(i); if(await c.isVisible().catch(()=>false)) return c;} }
    await page.waitForTimeout(250);
  }
  throw new Error('E_COMPOSER_UNAVAILABLE');
}
async function hrefFor(control){
  return await control.getAttribute('href').catch(()=>null) || await control.evaluate(el=>el.closest('a')?.href || el.querySelector?.('a')?.href || null).catch(()=>null);
}
async function acquireBytes(page, context, control){
  const href=await hrefFor(control);
  try{
    const pending=page.waitForEvent('download',{timeout:downloadTimeoutMs});
    await control.click();
    const download=await pending;
    const tmp=path.join(os.tmpdir(),`fa114-gemini-${crypto.randomUUID()}`);
    await download.saveAs(tmp);
    const raw=fs.readFileSync(tmp); fs.rmSync(tmp,{force:true});
    if(!raw.length) throw new Error('E_EMPTY_DOWNLOAD');
    return [raw,'provider_browser_download_event'];
  }catch(error){
    if(!href) throw new Error(`E_DOWNLOAD_FAILED:${String(error?.message||error).slice(0,100)}`);
  }
  const response=await context.request.get(href,{timeout:45000});
  if(!response.ok()) throw new Error(`E_DOWNLOAD_HTTP_${response.status()}`);
  const raw=Buffer.from(await response.body());
  if(!raw.length) throw new Error('E_EMPTY_DOWNLOAD');
  return [raw,'provider_download_href_browser_context'];
}

fs.mkdirSync(providerDir,{recursive:true,mode:0o770});
const driver=new PlaywrightChromiumDriver({executablePath:chrome,headless:true,launchTimeoutMs:30000,shutdownTimeoutMs:8000});
try{
  receipt.started_at=now();
  const handle=await driver.launch(profileDir); const context=handle.browser.contexts()[0];
  let page=context.pages().find(p=>p.url().includes('gemini.google.com')) || context.pages()[0] || await context.newPage();
  await enforceTabBudget(context,{preserve:[page],maxTabs:MAX_TABS_PER_PRINCIPAL});
  await page.goto('https://gemini.google.com/app',{waitUntil:'domcontentloaded',timeout:60000}); await page.waitForTimeout(2500);
  if(await visibleCount(page,signInSelector)) throw new Error('E_AUTH_REQUIRED');
  const composer=await findComposer(page); const before=await page.locator(downloadSelector).count(); receipt.preflight_at=now();
  receipt.dispatch_started_at=now(); await composer.fill(prompt); await composer.press('Enter'); receipt.dispatch_committed_at=now(); receipt.prompt_submitted_by_automation=true;
  const deadline=Date.now()+generationTimeoutMs; let control=null;
  while(Date.now()<deadline && !control){
    if(await visibleCount(page,signInSelector)) throw new Error('E_AUTH_EXPIRED');
    const loc=page.locator(downloadSelector); const count=await loc.count();
    if(count>before){ for(let i=count-1;i>=before;i-=1){const c=loc.nth(i); if(await c.isVisible().catch(()=>false)){control=c;break;}} }
    if(!control){ const body=(await page.locator('body').innerText({timeout:3000}).catch(()=>'' )).toLowerCase(); if(/image creation isn.t available|can.t seem to create any/.test(body)) throw new Error('E_UNSUPPORTED_CAPABILITY'); await page.waitForTimeout(500); }
  }
  if(!control) throw new Error('E_BOUNDED_COMPLETION_TIMEOUT');
  receipt.generation_completed_at=now(); const [raw,method]=await acquireBytes(page,context,control); const [mime,ext]=mimeAndExt(raw); if(raw.length<10000) throw new Error('E_IMAGE_TOO_SMALL');
  const outputPath=path.join(providerDir,`source-original.${ext}`); fs.writeFileSync(outputPath,raw,{mode:0o660});
  receipt.output_extracted_by_automation=true; receipt.original_byte_acquisition_method=method; receipt.local_path=outputPath; receipt.mime=mime; receipt.bytes=raw.length; receipt.sha256=crypto.createHash('sha256').update(raw).digest('hex'); receipt.status='PASS'; receipt.completed_at=now();
}catch(error){ receipt.failure_code=String(error?.message||error).slice(0,240); receipt.completed_at=now(); }
finally{ await driver.stop().catch(()=>{}); fs.writeFileSync(path.join(providerDir,'gemini-canary-result.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o660}); console.log(JSON.stringify(receipt)); }
process.exitCode=receipt.status==='PASS'?0:1;
