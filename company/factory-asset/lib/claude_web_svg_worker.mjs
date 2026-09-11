import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { acquireClusterTab, connectLeasedClusterTab, markClusterTab, releaseClusterTab, setClusterProviderState } from '../../browser/linux/cluster_broker_client.mjs';
import { classifyProviderPage } from '../../browser/linux/provider_readiness.mjs';

function sha256(v){return crypto.createHash('sha256').update(v).digest('hex')}
function now(){return new Date().toISOString()}
function atomic(file,text){fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});const t=`${file}.tmp-${process.pid}`;fs.writeFileSync(t,text,{mode:0o640});fs.renameSync(t,file)}
async function composerText(loc){return await loc.evaluate(el=>typeof el.value==='string'?el.value.trim():String(el.innerText||el.textContent||'').trim()).catch(()=> '')}
async function fillSubmit(page,prompt,profile){
 for(let attempt=0;attempt<8;attempt++){
  for(const sel of profile.composer_selectors||[]){
   const loc=page.locator(sel).first(); if(!await loc.isVisible({timeout:300}).catch(()=>false))continue;
   if(typeof loc.isEditable==='function'&&!await loc.isEditable().catch(()=>false))continue;
   try{await loc.click({timeout:1500});await loc.fill(prompt,{timeout:4000}).catch(async()=>{await page.keyboard.press('Control+A');await page.keyboard.type(prompt,{delay:2})});if(!(await composerText(loc)))continue;
    for(const s of ['button[aria-label*="Send" i]','button[data-testid*="send" i]','button[type="submit"]']){const b=page.locator(s).first();if(await b.isVisible({timeout:250}).catch(()=>false)&&await b.isEnabled().catch(()=>false)){await b.click();return {composer_selector:sel,send_selector:s}}}
    await loc.press('Enter');return {composer_selector:sel,send_selector:'composer-enter'};
   }catch{}
  }
  await page.waitForTimeout(500*(attempt+1));
 }
 throw new Error('E_CLAUDE_COMPOSER_UNAVAILABLE');
}
async function extractSvgCandidate(page){
 const selectors=['pre code','pre','code','[data-testid*="message" i]','article','[class*="claude-message" i]'];
 let best='';
 for(const sel of selectors){
  const rows=await page.locator(sel).evaluateAll(es=>es.map(e=>String(e.innerText||e.textContent||'').trim()).filter(Boolean)).catch(()=>[]);
  for(const text of rows){const a=text.indexOf('<svg');const b=text.lastIndexOf('</svg>');if(a>=0&&b>a){const x=text.slice(a,b+6).trim();if(x.length>best.length&&x.length<=250000)best=x}}
 }
 return best;
}
export async function runClaudeWebSvg({controlBaseUrl,playwrightEntry,readinessProfile,jobId,prompt,responseFile,receiptFile,clusterId,timeoutMs=300000}){
 if(typeof prompt!=='string'||prompt.length<40||prompt.length>12000)throw new Error('E_CLAUDE_PROMPT');
 let lease=null,disconnect=null,page=null;const out={schema:'die.factory-asset.claude-web-svg-attempt.v1',job_id:jobId,provider_id:'claude',cluster_id:clusterId,transport:'BROWSER_CDP',prompt_sha256:sha256(prompt),credential_values_read:false,cookies_or_tokens_read:false,submission_authorized:false,publication_authorized:false,started_at:now()};
 try{
  lease=await acquireClusterTab(controlBaseUrl,{providerId:'claude',jobId,ttlMs:Math.min(600000,timeoutMs+120000)});
  const c=await connectLeasedClusterTab({controlBaseUrl,lease,playwrightEntry,timeoutMs:15000});disconnect=c.disconnect;page=c.page;
  await page.goto('https://claude.ai/new',{waitUntil:'domcontentloaded',timeout:60000});await page.waitForTimeout(2500);
  const readiness=await classifyProviderPage({page,providerId:'claude',profile:readinessProfile});out.readiness=readiness;
  await setClusterProviderState(controlBaseUrl,'claude',readiness.state).catch(()=>null);
  if(readiness.state!=='HEALTHY')throw new Error(`E_CLAUDE_${readiness.state}:${readiness.reason_code||'UNKNOWN'}`);
  out.dispatch=await fillSubmit(page,prompt,readinessProfile);await markClusterTab(controlBaseUrl,lease.lease_id,'IN_FLIGHT').catch(()=>null);
  const deadline=Date.now()+timeoutMs;let stable=0,last='';
  while(Date.now()<deadline){await page.waitForTimeout(1500);const svg=await extractSvgCandidate(page);if(svg){if(svg===last)stable++;else{last=svg;stable=0}if(stable>=2){out.svg_sha256=sha256(svg);out.svg_chars=svg.length;out.status='SUCCEEDED';out.completed_at=now();atomic(responseFile,svg+'\n');atomic(receiptFile,JSON.stringify(out,null,2)+'\n');return out}}}
  throw new Error('E_CLAUDE_SVG_RESPONSE_TIMEOUT');
 }catch(e){out.status='FAILED';out.error=String(e?.message||e).slice(0,600);out.completed_at=now();if(receiptFile)atomic(receiptFile,JSON.stringify(out,null,2)+'\n');return out}
 finally{if(lease?.lease_id)await releaseClusterTab(controlBaseUrl,lease.lease_id,'FA322_CLAUDE_WEB_COMPLETE').catch(()=>null);if(disconnect)await disconnect()}
}
