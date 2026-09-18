#!/usr/bin/env node
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

export const FOUNDER_DISPLAY=':12.0';
export const WORKSPACE_COUNT=5;
export const WORKSPACE_BY_TARGET=Object.freeze({
  'die-lnx-executive-001':1,
  'die-lnx-division-001':2,
  'cluster-a':3,
  'cluster-b':4,
  'executive':1,
  'division01':2,
  'runtime01':3,
  'runtime02':4,
});
const sleep=(ms)=>new Promise((r)=>setTimeout(r,ms));
function env(){return{...process.env,DISPLAY:FOUNDER_DISPLAY}}
function run(args,{check=true}={}){
  const cp=spawnSync('/usr/bin/wmctrl',args,{encoding:'utf8',env:env()});
  if(check&&cp.status!==0)throw new Error(`E_WMCTRL:${args.join(' ')}:${String(cp.stderr||cp.stdout).slice(-300)}`);
  return cp;
}
function processTree(rootPid){
  const root=Number(rootPid),seen=new Set([root]);let changed=true;
  while(changed){changed=false;for(const name of fs.readdirSync('/proc').filter(x=>/^\d+$/.test(x))){const pid=Number(name);if(seen.has(pid))continue;try{const status=fs.readFileSync(`/proc/${pid}/status`,'utf8');const m=status.match(/^PPid:\s+(\d+)/m);if(m&&seen.has(Number(m[1]))){seen.add(pid);changed=true}}catch{}}}
  return seen;
}
export function founderDisplayReady(){
  return fs.existsSync('/tmp/.X11-unix/X12')&&run(['-d'],{check:false}).status===0;
}
export function ensureFounderDisplay(){
  if(!fs.existsSync('/tmp/.X11-unix/X12'))throw new Error('E_FOUNDER_DISPLAY12_SOCKET');
  run(['-d']);
  run(['-n',String(WORKSPACE_COUNT)]);
  return{display:FOUNDER_DISPLAY,workspace_count:WORKSPACE_COUNT};
}
function windowRows(){
  const cp=run(['-lp'],{check:false});if(cp.status!==0)return[];
  return String(cp.stdout||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{const p=line.split(/\s+/,5);return{window_id:p[0],desktop:Number(p[1]),pid:Number(p[2]),raw:line}}).filter(x=>x.window_id&&Number.isInteger(x.pid));
}
export async function placePidOnFounderWorkspace(target,pid,{timeoutMs=12000}={}){
  const workspace=WORKSPACE_BY_TARGET[target];if(!Number.isInteger(workspace))throw new Error(`E_FOUNDER_WORKSPACE_TARGET:${target}`);
  ensureFounderDisplay();const deadline=Date.now()+timeoutMs;let moved=[];
  while(Date.now()<deadline){
    const tree=processTree(pid);const rows=windowRows().filter(x=>tree.has(x.pid));
    if(rows.length){moved=[];for(const row of rows){run(['-i','-r',row.window_id,'-t',String(workspace)]);moved.push(row.window_id)};return{schema:'die.founder-display12-placement.v1',target,display:FOUNDER_DISPLAY,workspace_index:workspace,workspace_number:workspace+1,browser_pid:Number(pid),window_ids:moved,status:'PLACED'}}
    await sleep(150);
  }
  throw new Error(`E_FOUNDER_WORKSPACE_WINDOW_TIMEOUT:${target}:${pid}`);
}
export function founderWorkspaceStatus(){
  const ready=founderDisplayReady();return{schema:'die.founder-display12-status.v1',display:FOUNDER_DISPLAY,ready,workspace_count:ready?String(run(['-d']).stdout||'').split(/\r?\n/).filter(Boolean).length:0,mapping:WORKSPACE_BY_TARGET};
}

if(import.meta.url===`file://${process.argv[1]}`){
  const cmd=process.argv[2]||'status';
  try{
    if(cmd==='status')console.log(JSON.stringify(founderWorkspaceStatus()));
    else if(cmd==='init')console.log(JSON.stringify(ensureFounderDisplay()));
    else if(cmd==='place'){const target=process.argv[3],pid=Number(process.argv[4]);console.log(JSON.stringify(await placePidOnFounderWorkspace(target,pid)))}
    else throw new Error('usage: founder_display12.mjs status|init|place TARGET PID');
  }catch(e){console.error(e instanceof Error?e.message:String(e));process.exitCode=2}
}
