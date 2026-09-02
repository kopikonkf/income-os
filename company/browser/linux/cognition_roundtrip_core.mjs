#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { enforceTabBudget, MAX_TABS_PER_PRINCIPAL } from './tab_budget.mjs';

export const MAX_PROMPT_CHARS = 12000;
export const MAX_RESPONSE_CHARS = 40000;

const COGNITION_COMPOSER_SELECTORS = [
  '[data-testid="prompt-textarea"]',
  '#prompt-textarea',
  'textarea[placeholder*="Message" i]',
  'textarea[placeholder*="Ask" i]',
  '[contenteditable="true"][data-lexical-editor="true"]',
];
const COGNITION_SEND_SELECTORS = [
  'button[data-testid="send-button"]',
  'button[aria-label="Send prompt"]',
  'button[aria-label*="Send" i]',
];
async function acquireComposer(page, attempts=8){
  for(let attempt=1;attempt<=attempts;attempt++){
    for(const selector of COGNITION_COMPOSER_SELECTORS){
      const box=page.locator(selector).first();
      if(await box.isVisible({timeout:350}).catch(()=>false)) return {box,selector,attempt};
    }
    await page.waitForTimeout(300*attempt);
  }
  throw new Error('E_COMPOSER_REACQUIRE');
}
async function acquireSend(page, attempts=8){
  for(let attempt=1;attempt<=attempts;attempt++){
    for(const selector of COGNITION_SEND_SELECTORS){
      const send=page.locator(selector).first();
      if(await send.isVisible({timeout:300}).catch(()=>false) && !await send.isDisabled().catch(()=>true)) return {send,selector,attempt};
    }
    await page.waitForTimeout(250*attempt);
  }
  throw new Error('E_SEND_BUTTON_REACQUIRE');
}
export const PRINCIPALS = {
  'die-lnx-division-001': {
    statusFile: '/var/lib/die/division01/browser-status.json',
    threadFile: '/var/lib/die/division01/wake-thread.json',
    receiptDir: '/var/lib/die/division01/cognition-receipts',
  },
  'die-lnx-executive-001': {
    statusFile: '/var/lib/die/executive/browser-status.json',
    threadFile: '/var/lib/die/executive/wake-thread.json',
    receiptDir: '/var/lib/die/executive/cognition-receipts',
  },
};
const REQUEST_RE = /^COG-[A-Z0-9_-]{8,160}$/;
const ALLOWED_ACTIONS = new Set(['PRODUCTION_BLUEPRINT_AUTHOR', 'PRODUCTION_BLUEPRINT_REVIEW', 'PRODUCTION_BLUEPRINT_REVISE', 'AUTONOMY_CANARY']);

function sha256(text) { return crypto.createHash('sha256').update(text, 'utf8').digest('hex'); }
function atomicJson(file, value) { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o750 }); const tmp=`${file}.tmp-${process.pid}`; fs.writeFileSync(tmp, JSON.stringify(value,null,2)+'\n',{mode:0o640}); fs.renameSync(tmp,file); }
function parseTime(v){ const x=Date.parse(v); if(!Number.isFinite(x)) throw new Error('E_TIME'); return x; }

export function validateRequest(v, nowMs=Date.now(), allowExpired=false) {
  if(!v || typeof v!=='object' || Array.isArray(v)) throw new Error('E_REQUEST_OBJECT');
  if(v.schema!=='die.cognition.outbox-request.v1') throw new Error('E_REQUEST_SCHEMA');
  if(v.company_instance_id!=='DIE-LINUX') throw new Error('E_COMPANY');
  if(!REQUEST_RE.test(String(v.request_id||''))) throw new Error('E_REQUEST_ID');
  if(!PRINCIPALS[v.target_principal_id]) throw new Error('E_TARGET_PRINCIPAL');
  if(!ALLOWED_ACTIONS.has(v.action_type)) throw new Error('E_ACTION');
  if(!Number.isInteger(v.thread_generation) || v.thread_generation < 1) throw new Error('E_THREAD_GENERATION');
  if(typeof v.prompt!=='string' || !v.prompt.trim() || v.prompt.length>MAX_PROMPT_CHARS) throw new Error('E_PROMPT');
  if(typeof v.expected_response_schema!=='string' || !v.expected_response_schema.trim()) throw new Error('E_RESPONSE_SCHEMA');
  const created=parseTime(v.created_at), expires=parseTime(v.expires_at); if(expires<=created) throw new Error('E_REQUEST_EXPIRY_ORDER'); if(!allowExpired && nowMs>=expires) throw new Error('E_REQUEST_EXPIRED');
  if(created>nowMs+60000) throw new Error('E_REQUEST_FROM_FUTURE');
  if(!Array.isArray(v.evidence_refs||[]) || v.evidence_refs.length>30) throw new Error('E_EVIDENCE_REFS');
  return v;
}

export function requestMarker(requestId){ return `[DIE-COGNITION-REQUEST:${requestId}]`; }
export function chooseRecoveredTurn(turns, requestId) {
  const marker=requestMarker(requestId); let userIndex=-1;
  for(let i=0;i<turns.length;i++) if(turns[i].role==='user' && String(turns[i].text||'').includes(marker)) userIndex=i;
  if(userIndex<0) return {state:'NOT_SENT'};
  for(let i=userIndex+1;i<turns.length;i++) if(turns[i].role==='assistant' && String(turns[i].text||'').trim()) return {state:'RESPONDED', userIndex, assistant:turns[i]};
  return {state:'SENT_WAITING', userIndex};
}

async function turnSnapshot(page){
  return await page.locator('[data-message-author-role]').evaluateAll(es=>es.map((e,i)=>({index:i,role:e.getAttribute('data-message-author-role'),id:e.getAttribute('data-message-id')||e.closest('[data-message-id]')?.getAttribute('data-message-id')||null,text:(e.innerText||e.textContent||'').trim()})));
}
async function composerText(box){ return (await box.inputValue().catch(async()=>await box.innerText().catch(async()=>await box.textContent()||''))).trim(); }
function normalizeThreadUrl(url){ const m=String(url||'').match(/^https:\/\/chatgpt\.com\/c\/([A-Za-z0-9-]+)/); if(!m) throw new Error('E_THREAD_URL'); return `https://chatgpt.com/c/${m[1]}`; }

export async function runRoundtrip({dieHome='/srv/die', requestFile, responseFile=null, timeoutMs=240000}) {
  if(!path.isAbsolute(requestFile)) throw new Error('E_REQUEST_PATH');
  const req=validateRequest(JSON.parse(fs.readFileSync(requestFile,'utf8')), Date.now(), true);
  const cfg=PRINCIPALS[req.target_principal_id];
  const status=JSON.parse(fs.readFileSync(cfg.statusFile,'utf8')), thread=JSON.parse(fs.readFileSync(cfg.threadFile,'utf8'));
  if(status.principal_id!==req.target_principal_id || status.state!=='READY' || status.debugHost!=='127.0.0.1') throw new Error('E_BROWSER_STATUS');
  if(thread.principal_id!==req.target_principal_id || thread.lifecycle_state!=='active' || thread.generation!==req.thread_generation) throw new Error('E_THREAD_BINDING');
  const expectedUrl=normalizeThreadUrl(thread.conversation_url);
  const pw=await import(pathToFileURL(path.join(dieHome,'company/muxia/node_modules/playwright/index.mjs')).href);
  const browser=await pw.chromium.connectOverCDP(`http://${status.debugHost}:${status.debugPort}`,{timeout:20000});
  let submitted=false;
  try {
    const ctx=browser.contexts()[0]; if(!ctx) throw new Error('E_BROWSER_CONTEXT');
    let page=ctx.pages().find(p=>normalizeThreadUrlSafe(p.url())===expectedUrl);
    let rebound=false;
    if(!page){
      page=ctx.pages().find(p=>String(p.url()).startsWith('https://chatgpt.com')) || ctx.pages()[0] || await ctx.newPage();
      await enforceTabBudget(ctx,{preserve:[page],maxTabs:MAX_TABS_PER_PRINCIPAL});
      await page.goto(expectedUrl,{waitUntil:'domcontentloaded',timeout:60000});
      await page.waitForTimeout(1200);
      if(normalizeThreadUrlSafe(page.url())!==expectedUrl) throw new Error('E_BOUND_THREAD_NAVIGATION');
      rebound=true;
    }
    await page.bringToFront();
    let turns=await turnSnapshot(page); let recovered=chooseRecoveredTurn(turns,req.request_id); let assistant=null;
    if(recovered.state==='RESPONDED') assistant=recovered.assistant;
    if(recovered.state==='NOT_SENT') {
      if(Date.now()>=parseTime(req.expires_at)) throw new Error('E_REQUEST_EXPIRED');
      const composerAcquisition=await acquireComposer(page); const box=composerAcquisition.box; if(await composerText(box)) throw new Error('E_COMPOSER_NOT_EMPTY');
      const fullPrompt=`${requestMarker(req.request_id)}\n${req.prompt}`; if(fullPrompt.length>MAX_PROMPT_CHARS+220) throw new Error('E_FULL_PROMPT_OVERSIZE');
      await box.fill(fullPrompt); const staged=await composerText(box); if(!staged.includes(requestMarker(req.request_id))) { await box.fill(''); throw new Error('E_STAGE_MISMATCH'); }
      const sendAcquisition=await acquireSend(page); const send=sendAcquisition.send;
      await send.click(); submitted=true; recovered={state:'SENT_WAITING'};
    }
    if(recovered.state==='SENT_WAITING') {
      const deadline=Date.now()+timeoutMs; let stable=0,last='';
      while(Date.now()<deadline){
        await page.waitForTimeout(1000); turns=await turnSnapshot(page); recovered=chooseRecoveredTurn(turns,req.request_id);
        if(recovered.state==='RESPONDED'){
          assistant=recovered.assistant; const text=assistant.text||''; if(text===last && text.length>0) stable++; else {last=text;stable=0;}
          const stop=page.locator('button[data-testid="stop-button"], button[aria-label*="Stop"]').first(); const generating=(await stop.count())>0 && await stop.isVisible().catch(()=>false);
          if(stable>=2 && !generating) break;
        }
      }
    }
    if(!assistant || !assistant.text) throw new Error('E_RESPONSE_TIMEOUT');
    if(assistant.text.length>MAX_RESPONSE_CHARS) throw new Error('E_RESPONSE_OVERSIZE');
    const receipt={schema:'die.cognition.roundtrip-receipt.v1',company_instance_id:'DIE-LINUX',request_id:req.request_id,task_id:req.task_id,target_principal_id:req.target_principal_id,action_type:req.action_type,thread_generation:thread.generation,conversation_id:thread.conversation_id,bound_thread_recovered:rebound,submitted_by_transport:submitted,recovered_existing_request:!submitted,response_schema_expected:req.expected_response_schema,assistant_message_id:assistant.id,response_sha256:sha256(assistant.text),response_chars:assistant.text.length,credential_material_accessed:false,private_backend_called:false,observed_at:new Date().toISOString()};
    const recPath=path.join(cfg.receiptDir,`${req.request_id}.json`); atomicJson(recPath,receipt);
    if(responseFile){ if(!path.isAbsolute(responseFile)) throw new Error('E_RESPONSE_PATH'); fs.mkdirSync(path.dirname(responseFile),{recursive:true,mode:0o750}); fs.writeFileSync(responseFile,assistant.text+'\n',{mode:0o640}); }
    return {...receipt,receipt_ref:recPath,response_file:responseFile};
  } finally { /* Connected over CDP to operator-owned Chrome: process exit drops the socket; never terminate the browser. */ }
}
function normalizeThreadUrlSafe(url){ try{return normalizeThreadUrl(url);}catch{return '';} }
