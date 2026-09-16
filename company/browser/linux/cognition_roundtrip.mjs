#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { runRoundtrip } from './cognition_roundtrip_core.mjs';
import { withPrincipalJobBrowser } from './principal_job_browser_runtime.mjs';

const requestFile=process.argv[2]?path.resolve(process.argv[2]):null;
const responseFile=process.argv[3]?path.resolve(process.argv[3]):null;
if(!requestFile){console.error('usage: cognition_roundtrip.mjs REQUEST_JSON [RESPONSE_TEXT]');process.exit(2);}
try{
  const req=JSON.parse(fs.readFileSync(requestFile,'utf8'));
  const out=await withPrincipalJobBrowser({
    principalId:req.target_principal_id,
    jobId:req.request_id,
    work:()=>runRoundtrip({requestFile,responseFile}),
  });
  console.log(JSON.stringify(out));
  process.exit(0);
}catch(e){
  console.error(e instanceof Error?e.message:String(e));
  process.exit(2);
}
