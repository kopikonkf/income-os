#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { withPrincipalJobBrowser } from '../../browser/linux/principal_job_browser_runtime.mjs';

const principalId=process.env.FA338_COGNITION_PRINCIPAL||'die-lnx-executive-001';
const root=process.env.FA338_CANARY_ROOT||'/var/lib/die/acceptance/FA-338';
const jobId=`FA338-COGNITION-${principalId.endsWith('executive-001')?'EXEC':'DIV'}`;
const terminal=path.join(root,`${jobId}.terminal.json`);
function atomic(file,v){fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});const t=`${file}.tmp-${process.pid}`;fs.writeFileSync(t,JSON.stringify(v,null,2)+'\n',{mode:0o640});fs.renameSync(t,file)}
const out=await withPrincipalJobBrowser({principalId,jobId,work:async()=>{
 const t={schema:'die.cognition.fa338-lifecycle-canary-terminal.v1',status:'SUCCEEDED',principal_id:principalId,job_id:jobId,provider_prompt_submitted:false,credential_values_read:false,cookies_or_tokens_read:false,completed_at:new Date().toISOString()};
 atomic(terminal,t);return{receipt_ref:terminal,status:'SUCCEEDED'};
}});
const result={schema:'die.cognition.fa338-lifecycle-canary.v1',task_id:'FA-338',status:'PASS',principal_id:principalId,job_id:jobId,provider_prompt_submitted:false,credential_values_read:false,cookies_or_tokens_read:false,completed_at:new Date().toISOString(),result:out};
atomic(path.join(root,`${jobId}.receipt.json`),result);
console.log(JSON.stringify(result));
