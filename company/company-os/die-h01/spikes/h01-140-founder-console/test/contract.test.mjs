import test from 'node:test';
import assert from 'node:assert/strict';
import {createApp} from '../server.mjs';

const paths=['overview','production','providers','qc/gallery','submission-ready','demand','tasks','system/health','settings'];

async function withServer(fn){
  const app=createApp();
  await new Promise(r=>app.listen(0,'127.0.0.1',r));
  const {port}=app.address();
  try{return await fn(`http://127.0.0.1:${port}`)} finally {await new Promise(r=>app.close(r));}
}

test('all nine Founder Console read models are GET-only and provenance-bearing', async()=>withServer(async base=>{
  for(const p of paths){
    const r=await fetch(`${base}/api/die/v1/${p}`);
    assert.equal(r.status,200,p);
    const j=await r.json();
    assert.equal(j.read_only,true,p);
    assert.ok(j.source,p);
    assert.ok(j.observed_at,p);
    assert.ok(j.data,p);
    const w=await fetch(`${base}/api/die/v1/${p}`,{method:'POST'});
    assert.equal(w.status,405,p);
    assert.equal(w.headers.get('allow'),'GET',p);
  }
}));

test('security headers and loopback-safe shell contract are present', async()=>withServer(async base=>{
  const r=await fetch(`${base}/`);
  assert.equal(r.status,200);
  assert.equal(r.headers.get('x-frame-options'),'DENY');
  assert.equal(r.headers.get('x-content-type-options'),'nosniff');
  assert.match(r.headers.get('content-security-policy'),/frame-ancestors 'none'/);
  const body=await r.text();
  for(const label of ['Overview','Production','Providers/BYOK','QC Gallery','Submission Ready','Demand Intelligence','Tasks/MC','System Health','Settings']) assert.match(body,new RegExp(label.replace('/','\\/')));
  assert.match(body,/localhost:8876 remains live/);
}));

test('health receipt proves bounded spike authority', async()=>withServer(async base=>{
  const r=await fetch(`${base}/healthz`);
  const j=await r.json();
  assert.deepEqual(j,{status:'PASS',mode:'READ_ONLY_SPIKE',live_provider_accounts:false,marketplace_actions:false});
}));
