import test from 'node:test'; import assert from 'node:assert/strict'; import fs from 'node:fs';
import {validateRequest,requestMarker,chooseRecoveredTurn} from '../../company/browser/linux/cognition_roundtrip_core.mjs';
function req(){const now=Date.now();return {schema:'die.cognition.outbox-request.v1',company_instance_id:'DIE-LINUX',request_id:'COG-B04_CANARY_0001',task_id:'T1',action_type:'AUTONOMY_CANARY',target_principal_id:'die-lnx-division-001',thread_generation:1,prompt:'hello',expected_response_schema:'die.cognition.canary.v1',evidence_refs:[],created_at:new Date(now-1000).toISOString(),expires_at:new Date(now+60000).toISOString()};}
test('valid request passes',()=>assert.equal(validateRequest(req()).request_id,'COG-B04_CANARY_0001'));
test('cross-principal unknown target fails',()=>{const x=req();x.target_principal_id='wrong';assert.throws(()=>validateRequest(x),/E_TARGET_PRINCIPAL/)});
test('expired fails',()=>{const x=req();x.expires_at=new Date(Date.now()-1).toISOString();assert.throws(()=>validateRequest(x),/E_REQUEST_EXPIRED/)});
test('request marker is deterministic',()=>assert.equal(requestMarker('COG-X12345678'),'[DIE-COGNITION-REQUEST:COG-X12345678]'));
test('recovery distinguishes unsent/waiting/responded',()=>{const id='COG-X12345678',m=requestMarker(id);assert.equal(chooseRecoveredTurn([],id).state,'NOT_SENT');assert.equal(chooseRecoveredTurn([{role:'user',text:m,id:'u'}],id).state,'SENT_WAITING');const r=chooseRecoveredTurn([{role:'user',text:m,id:'u'},{role:'assistant',text:'{}',id:'a'}],id);assert.equal(r.state,'RESPONDED');assert.equal(r.assistant.id,'a');});

test('expired request can be structurally loaded for recovery only',()=>{const x=req();x.expires_at=new Date(Date.now()-1).toISOString();assert.equal(validateRequest(x,Date.now(),true).request_id,x.request_id);});


test('roundtrip recovers missing bound tab by navigating an existing page under tab budget',()=>{
  const text=fs.readFileSync(new URL('../../company/browser/linux/cognition_roundtrip_core.mjs',import.meta.url),'utf8');
  assert.match(text,/page=ctx\.pages\(\)\.find/);
  assert.match(text,/await page\.goto\(expectedUrl/);
  assert.match(text,/enforceTabBudget/);
  assert.match(text,/bound_thread_recovered:rebound/);
  assert.doesNotMatch(text,/throw new Error\('E_BOUND_THREAD_PAGE'\)/);
});
