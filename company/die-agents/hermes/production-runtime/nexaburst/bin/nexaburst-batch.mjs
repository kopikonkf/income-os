#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';

const argv=process.argv.slice(2);
const get=(k,d=null)=>{const i=argv.indexOf('--'+k);return i>=0&&argv[i+1]?argv[i+1]:d};
const input=get('input');
const style=get('style','isolated-object');
const max=Number(get('max','0'));
const aspect=Number(get('aspect','1'));
if(!input){console.error('usage: nexaburst-batch.mjs --input nouns.txt|queue.jsonl [--style isolated-object] [--max N]');process.exit(64)}
const adapter='/home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-adapter.mjs';
const receiptRoot='/var/lib/die/h01/nexaburst/receipts';
const batchLedger='/var/lib/die/h01/nexaburst/state/batch-ledger.jsonl';
const slug=s=>String(s).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,72)||'asset';
const lines=fs.readFileSync(input,'utf8').split(/\r?\n/).filter(x=>x.trim());
let rows=[];
for(const line of lines){
  if(line.trim().startsWith('{')){
    try{rows.push(JSON.parse(line))}catch(e){console.error('skip invalid jsonl',line.slice(0,80))}
  }else rows.push({noun:line.trim(),style});
}
if(max>0)rows=rows.slice(0,max);
const armFile='/var/lib/die/h01/nexaburst/state/PRODUCTION_ARMED.json';
if(rows.length>100 && !fs.existsSync(armFile)){
  console.error(JSON.stringify({status:'BLOCKED',code:'E_PRODUCTION_NOT_ARMED',rows:rows.length,required_marker:armFile}));
  process.exit(75);
}
if(rows.length>100){
  const sha=s=>crypto.createHash('sha256').update(String(s),'utf8').digest('hex');
  const bad=rows.find(r=>r.prompt_authority!=='TYPED_VISUAL_CONTRACT_V1' || !r.prompt || !r.prompt_sha256 || sha(r.prompt)!==r.prompt_sha256);
  if(bad){
    console.error(JSON.stringify({status:'BLOCKED',code:'E_TYPED_PROMPT_REQUIRED',asset_id:bad.asset_id||null,required_authority:'TYPED_VISUAL_CONTRACT_V1'}));
    process.exit(76);
  }
}
fs.mkdirSync(path.dirname(batchLedger),{recursive:true});
let ok=0,fail=0,skip=0;
for(let i=0;i<rows.length;i++){
  const r=rows[i], noun=r.noun, st=r.style||style;
  if(!noun)continue;
  const assetId=r.asset_id||`OA-${slug(st)}-${slug(noun)}`;
  const already=fs.existsSync(receiptRoot)&&fs.readdirSync(receiptRoot).some(f=>f.startsWith(assetId+'__')&&f.endsWith('.json'));
  if(already){skip++;console.error(`NEXABURST_BATCH_SKIP ${i+1}/${rows.length} asset=${assetId}`);continue}
  const args=['--noun',noun,'--style',st,'--asset-id',assetId,'--aspect',String(r.aspect||aspect)];
  if(r.prompt)args.push('--prompt',r.prompt);
  if(r.prompt_authority)args.push('--prompt-authority',r.prompt_authority);
  if(r.compiled_contract_sha256)args.push('--compiled-contract-sha256',r.compiled_contract_sha256);
  console.error(`NEXABURST_BATCH_RUN ${i+1}/${rows.length} asset=${assetId}`);
  const cp=spawnSync('node',[adapter,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']});
  if(cp.stderr)process.stderr.write(cp.stderr);
  if(cp.stdout)process.stdout.write(cp.stdout);
  const event={schema:'die.h01.nexaburst.batch-event.v1',asset_id:assetId,noun,style:st,index:i+1,total:rows.length,exit_code:cp.status,at:new Date().toISOString()};
  fs.appendFileSync(batchLedger,JSON.stringify(event)+'\n');
  if(cp.status===0)ok++;else fail++;
}
console.error(JSON.stringify({status:fail?'PARTIAL':'DONE',total:rows.length,ok,fail,skip}));
process.exit(fail?2:0);
