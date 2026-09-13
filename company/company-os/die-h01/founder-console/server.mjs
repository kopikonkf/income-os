import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createReadModels,proxyQcImage} from './adapter.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
export const HOST=process.env.H01_FOUNDER_CONSOLE_HOST||'127.0.0.1';
export const PORT=Number(process.env.H01_FOUNDER_CONSOLE_PORT||20128);
const REPO_ROOT=process.env.H01_FOUNDER_CONSOLE_REPO_ROOT||path.resolve(ROOT,'../../../..');
const DATA_ROOT=process.env.H01_FOUNDER_CONSOLE_DATA_ROOT||'/var/lib/die/h01';
const LEGACY_BASE=process.env.H01_FOUNDER_CONSOLE_LEGACY_BASE||'http://127.0.0.1:8876';
const securityHeaders={'content-security-policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",'x-content-type-options':'nosniff','x-frame-options':'DENY','referrer-policy':'no-referrer','cache-control':'no-store'};
const routeNames=new Map([['/api/die/v1/overview','overview'],['/api/die/v1/production','production'],['/api/die/v1/providers','providers'],['/api/die/v1/qc/gallery','qc'],['/api/die/v1/submission-ready','submission'],['/api/die/v1/demand','demand'],['/api/die/v1/tasks','tasks'],['/api/die/v1/system/health','health'],['/api/die/v1/settings','settings']]);
function json(res,status,body,extra={}){res.writeHead(status,{'content-type':'application/json; charset=utf-8',...securityHeaders,...extra});res.end(JSON.stringify(body))}
const envelope=(source,data)=>({schema:'die.h01.founder-console.read.v1',read_only:true,source,observed_at:new Date().toISOString(),data});
export function createApp(options={}){
 const repoRoot=options.repoRoot||REPO_ROOT,dataRoot=options.dataRoot||DATA_ROOT,legacyBase=options.legacyBase||LEGACY_BASE;const models=createReadModels({repoRoot,dataRoot,legacyBase});
 return http.createServer(async(req,res)=>{const url=new URL(req.url,'http://localhost');
  if(url.pathname.startsWith('/api/die/v1/')){
   if(req.method!=='GET')return json(res,405,{error:'READ_ONLY_CONTRACT',allowed:['GET']},{allow:'GET'});
   if(url.pathname==='/api/die/v1/qc/image'){const p=await proxyQcImage(legacyBase,url);res.writeHead(p.status,{...securityHeaders,...p.headers});return res.end(p.body)}
   const name=routeNames.get(url.pathname);if(!name)return json(res,404,{error:'NOT_FOUND'});
   try{return json(res,200,envelope(name,await models[name]()))}catch{return json(res,503,envelope(name,{status:'UNAVAILABLE'}))}
  }
  if(url.pathname==='/healthz'){const health=await models.health();const legacy=health.legacy_8876==='PASS'?'LISTENING':'UNAVAILABLE';return json(res,200,{status:'PASS',mode:'SHADOW_V1',legacy_8876:health.legacy_8876,cutover:false,write_actions_enabled:false,read_only:true,source:'founder-console-runtime',data:{console:'PASS',adapter:'PASS',legacy_8876:legacy,cutover:false,write_actions_enabled:false}})}
  if(req.method!=='GET'&&req.method!=='HEAD')return json(res,405,{error:'READ_ONLY_CONSOLE'},{allow:'GET, HEAD'});
  if(url.pathname==='/'||url.pathname==='/index.html'){const html=await readFile(path.join(ROOT,'public','index.html'));res.writeHead(200,{'content-type':'text/html; charset=utf-8',...securityHeaders});return req.method==='HEAD'?res.end():res.end(html)}
  return json(res,404,{error:'NOT_FOUND'});
 });
}
if(process.argv[1]===fileURLToPath(import.meta.url)){const app=createApp();app.listen(PORT,HOST,()=>console.log(JSON.stringify({status:'LISTENING',host:HOST,port:PORT,mode:'SHADOW_V1',legacy_8876:'PRESERVED'})))}
