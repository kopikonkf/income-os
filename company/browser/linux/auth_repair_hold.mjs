#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function atomicJson(file,value){
  fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o750});
  const tmp=`${file}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n',{mode:0o640});
  fs.renameSync(tmp,file);
}
export function readRepairHold(file,nowMs=Date.now()){
  let v=null;try{v=JSON.parse(fs.readFileSync(file,'utf8'))}catch{return null}
  if(v?.state!=='ACTIVE')return null;
  if(v.requires_founder_release===true)return v;
  const exp=Number(v.expires_at_epoch||0);
  if(Number.isFinite(exp)&&exp*1000>nowMs)return v;
  return null;
}
export function writeAuthRepairHold(file,{scopeId,profileId,providerId=null,reasonCode,sourceJobId=null}={}){
  const value={schema:'die.browser.auth-repair-hold.v1',state:'ACTIVE',mode:'FOUNDER_NO_CDP_AUTH_REPAIR',scope_id:scopeId,profile_id:profileId,provider_id:providerId,reason_code:reasonCode,source_job_id:sourceJobId,requires_founder_release:true,automated_cdp_allowed:false,credential_values_read:false,cookies_or_tokens_read:false,captcha_bypass_authorized:false,opened_at:new Date().toISOString()};
  atomicJson(file,value);return value;
}
export function closeRepairHold(file,{closedBy='FOUNDER_NO_CDP_REPAIR'}={}){
  let value={schema:'die.browser.auth-repair-hold.v1'};try{value=JSON.parse(fs.readFileSync(file,'utf8'))}catch{}
  value={...value,state:'CLOSED',requires_founder_release:false,automated_cdp_allowed:false,closed_by:closedBy,closed_at:new Date().toISOString(),credential_values_read:false,cookies_or_tokens_read:false,captcha_bypass_authorized:false};
  atomicJson(file,value);return value;
}
