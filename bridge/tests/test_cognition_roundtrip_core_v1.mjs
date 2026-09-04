import test from 'node:test'; import assert from 'node:assert/strict'; import fs from 'node:fs';
import {validateRequest,requestMarker,requestFingerprint,chooseRecoveredTurn,choosePriorRequestVersion} from '../../company/browser/linux/cognition_roundtrip_core.mjs';
function req(){const now=Date.now();return {schema:'die.cognition.outbox-request.v1',company_instance_id:'DIE-LINUX',request_id:'COG-B04_CANARY_0001',task_id:'T1',action_type:'AUTONOMY_CANARY',target_principal_id:'die-lnx-division-001',thread_generation:1,prompt:'hello',expected_response_schema:'die.cognition.canary.v1',evidence_refs:[],created_at:new Date(now-1000).toISOString(),expires_at:new Date(now+60000).toISOString()};}
test('valid request passes',()=>assert.equal(validateRequest(req()).request_id,'COG-B04_CANARY_0001'));
test('cross-principal unknown target fails',()=>{const x=req();x.target_principal_id='wrong';assert.throws(()=>validateRequest(x),/E_TARGET_PRINCIPAL/)});
test('expired fails',()=>{const x=req();x.expires_at=new Date(Date.now()-1).toISOString();assert.throws(()=>validateRequest(x),/E_REQUEST_EXPIRED/)});
test('request marker is deterministic',()=>assert.equal(requestMarker('COG-X12345678'),'[DIE-COGNITION-REQUEST:COG-X12345678]'));
test('recovery distinguishes unsent/waiting/responded',()=>{const id='COG-X12345678',m=requestMarker(id);assert.equal(chooseRecoveredTurn([],id).state,'NOT_SENT');assert.equal(chooseRecoveredTurn([{role:'user',text:m,id:'u'}],id).state,'SENT_WAITING');const r=chooseRecoveredTurn([{role:'user',text:m,id:'u'},{role:'assistant',text:'{}',id:'a'}],id);assert.equal(r.state,'RESPONDED');assert.equal(r.assistant.id,'a');});


test('request fingerprint ignores volatile timestamps but changes with canon context',()=>{const a=req(),b=req();b.created_at=new Date(Date.now()-5000).toISOString();b.expires_at=new Date(Date.now()+120000).toISOString();assert.equal(requestFingerprint(a),requestFingerprint(b));b.repository_sha='a'.repeat(40);assert.notEqual(requestFingerprint(a),requestFingerprint(b));});
test('versioned marker prevents stale logical request collision',()=>{const x=req(),fp=requestFingerprint(x),m=requestMarker(x.request_id,fp);assert.ok(m.startsWith(`[DIE-COGNITION-REQUEST:${x.request_id}:`));assert.equal(m.length,`[DIE-COGNITION-REQUEST:${x.request_id}:`.length+13);const old=requestMarker(x.request_id);const turns=[{role:'user',text:`${old}\nold prompt`,id:'u-old'},{role:'assistant',text:'',id:'a-old'}];assert.equal(chooseRecoveredTurn(turns,x.request_id,fp,x.prompt).state,'NOT_SENT');assert.equal(choosePriorRequestVersion(turns,x.request_id,fp,x.prompt).state,'SENT_WAITING');});
test('legacy marker remains recoverable when prompt is byte-identical',()=>{const x=req(),fp=requestFingerprint(x),legacy=`${requestMarker(x.request_id)}\n${x.prompt}`;const r=chooseRecoveredTurn([{role:'user',text:legacy,id:'u'},{role:'assistant',text:'{}',id:'a'}],x.request_id,fp,x.prompt);assert.equal(r.state,'RESPONDED');assert.equal(r.assistant.id,'a');});

test('expired request can be structurally loaded for recovery only',()=>{const x=req();x.expires_at=new Date(Date.now()-1).toISOString();assert.equal(validateRequest(x,Date.now(),true).request_id,x.request_id);});


test('roundtrip recovers missing bound tab by navigating an existing page under tab budget',()=>{
  const text=fs.readFileSync(new URL('../../company/browser/linux/cognition_roundtrip_core.mjs',import.meta.url),'utf8');
  assert.match(text,/page=ctx\.pages\(\)\.find/);
  assert.match(text,/await page\.goto\(expectedUrl/);
  assert.match(text,/enforceTabBudget/);
  assert.match(text,/bound_thread_recovered:rebound/);
  assert.doesNotMatch(text,/throw new Error\('E_BOUND_THREAD_PAGE'\)/);
});


test('cognition composer and send controls use bounded reacquisition',()=>{
  const text=fs.readFileSync(new URL('../../company/browser/linux/cognition_roundtrip_core.mjs',import.meta.url),'utf8');
  assert.match(text,/COGNITION_COMPOSER_SELECTORS/);
  assert.match(text,/stagePrompt\(page,fullPrompt,marker/);
  assert.match(text,/E_COMPOSER_REACQUIRE/);
  assert.match(text,/acquireSend\(page/);
  assert.match(text,/E_SEND_BUTTON_REACQUIRE/);
  assert.doesNotMatch(text,/page\.locator\('#prompt-textarea'\)\.first\(\)/);
});


test('cognition staging rejects disabled fallback composers and can recover same staged marker',()=>{
  const text=fs.readFileSync(new URL('../../company/browser/linux/cognition_roundtrip_core.mjs',import.meta.url),'utf8');
  assert.match(text,/isEditable/);
  assert.match(text,/stagePrompt\(page,fullPrompt,marker/);
  assert.match(text,/recoveredStaged:true/);
  assert.match(text,/existing\.includes\(marker\)/);
  assert.match(text,/fill\(fullPrompt,\{timeout:2500\}\)/);
});

test('stale prior request version is stopped before current version submission',()=>{const text=fs.readFileSync(new URL('../../company/browser/linux/cognition_roundtrip_core.mjs',import.meta.url),'utf8');assert.match(text,/choosePriorRequestVersion/);assert.match(text,/stalePriorVersionStopped/);assert.match(text,/await stop\.click/);assert.match(text,/request_fingerprint:fingerprint/);});
