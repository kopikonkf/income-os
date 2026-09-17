#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

const SOCKET=process.env.DIE_PRINCIPAL_BROWSER_BROKER_SOCKET||'/run/die/principal-browser-broker.sock';
const CFG={
  'die-lnx-executive-001':{receiptDir:'/var/lib/die/executive/cognition-receipts'},
  'die-lnx-division-001':{receiptDir:'/var/lib/die/division01/cognition-receipts'},
};
function atomic(file,v){fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});const t=`${file}.tmp-${process.pid}`;fs.writeFileSync(t,JSON.stringify(v,null,2)+'\n',{mode:0o640});fs.renameSync(t,file)}
function safeJob(v){return String(v||'').replace(/[^A-Za-z0-9_.-]/g,'_')}
async function brokerRequest(method,urlPath,body=null,timeoutMs=60000){
  const payload=body===null?null:Buffer.from(JSON.stringify(body));
  return await new Promise((resolve,reject)=>{
    const req=http.request({socketPath:SOCKET,path:urlPath,method,headers:payload?{'content-type':'application/json','content-length':payload.length}:undefined,timeout:timeoutMs},(res)=>{
      const chunks=[];res.on('data',(c)=>chunks.push(c));res.on('end',()=>{
        let value={};try{value=JSON.parse(Buffer.concat(chunks).toString('utf8')||'{}')}catch{return reject(new Error(`E_PRINCIPAL_BROKER_RESPONSE_JSON:${res.statusCode}`))}
        if((res.statusCode||500)>=400){const e=new Error(value.error||`E_PRINCIPAL_BROKER_HTTP:${res.statusCode}`);e.httpStatus=res.statusCode;e.details=value.details||null;return reject(e)}
        resolve(value);
      });
    });
    req.on('timeout',()=>req.destroy(new Error('E_PRINCIPAL_BROKER_TIMEOUT')));
    req.on('error',(e)=>reject(new Error(`E_PRINCIPAL_BROKER_TRANSPORT:${e.message}`)));
    if(payload)req.write(payload);req.end();
  });
}
export async function principalBrowserBrokerStatus(principalId){
  return await brokerRequest('GET',`/v1/status?principal_id=${encodeURIComponent(principalId)}`,null,10000);
}
export async function withPrincipalJobBrowser({principalId,jobId,work,terminalEvidencePath=null}={}){
  const cfg=CFG[principalId];if(!cfg)throw new Error('E_PRINCIPAL_BROWSER_PRINCIPAL');
  if(typeof work!=='function')throw new Error('E_PRINCIPAL_BROWSER_WORK');
  const start=await brokerRequest('POST','/v1/start',{principal_id:principalId,job_id:jobId},60000);
  let result=null,workError=null;
  try{
    result=await work();
    if(!terminalEvidencePath&&result?.receipt_ref)terminalEvidencePath=result.receipt_ref;
  }catch(error){workError=error}
  const safe=safeJob(jobId);
  if(workError){
    const fail={schema:'die.cognition.job-browser-terminal.v1',status:'FAILED',principal_id:principalId,job_id:jobId,error:String(workError?.message||workError).slice(0,800),completed_at:new Date().toISOString()};
    terminalEvidencePath=path.join(cfg.receiptDir,`browser-lifecycle-${safe}.terminal.json`);atomic(terminalEvidencePath,fail);
  }
  if(!terminalEvidencePath||!fs.existsSync(terminalEvidencePath)){
    const fail={schema:'die.cognition.job-browser-terminal.v1',status:'FAILED',principal_id:principalId,job_id:jobId,error:'E_TERMINAL_EVIDENCE_MISSING',completed_at:new Date().toISOString()};
    terminalEvidencePath=path.join(cfg.receiptDir,`browser-lifecycle-${safe}.terminal.json`);atomic(terminalEvidencePath,fail);
    if(!workError)workError=new Error('E_TERMINAL_EVIDENCE_MISSING');
  }
  let stopError=null;
  try{
    const stopped=await brokerRequest('POST','/v1/stop',{principal_id:principalId,job_id:jobId,terminal_evidence_path:terminalEvidencePath,reason:workError?'COGNITION_FAILED':'COGNITION_TERMINAL'},30000);
    if(stopped?.runtime?.status!=='COLD')stopError=new Error('E_PRINCIPAL_BROWSER_CLOSE_INCOMPLETE');
  }catch(error){stopError=error}
  if(stopError)throw stopError;
  if(workError)throw workError;
  return result;
}
