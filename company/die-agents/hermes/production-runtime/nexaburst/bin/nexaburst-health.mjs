#!/usr/bin/env node
import { chromium } from '/srv/die/company/muxia/node_modules/playwright/index.mjs';
const cdp='http://127.0.0.1:9311';
try{
  const b=await chromium.connectOverCDP(cdp,{timeout:8000});
  const c=b.contexts()[0];
  let p=c?.pages().find(x=>x.url().includes('nexabot.id'));
  if(!p){console.log(JSON.stringify({cdp:true,page:false,authenticated:false}));await b.close();process.exit(1)}
  const a=await p.evaluate(async()=>{
    const r=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
    let j={};try{j=await r.json()}catch{}
    return {http:r.status,authenticated:!!j.authenticated,unlimited_active:!!j.unlimited_active,unlimited_until:j.unlimited_until||null,credit:Number(j.credit||0)};
  });
  console.log(JSON.stringify({cdp:true,page:true,url:p.url(),...a}));
  await b.close();
  process.exit(a.authenticated&&a.unlimited_active?0:2);
}catch(e){
  console.log(JSON.stringify({cdp:false,page:false,authenticated:false,error:String(e.message||e)}));
  process.exit(3);
}
