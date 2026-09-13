#!/usr/bin/env python3
from __future__ import annotations
import argparse,fcntl,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Jakarta')
DEFAULT_REGISTRY=Path('/var/lib/die/h01/browser/daily-provider-threads.v1.json')
SCHEMA='die.h01.daily-provider-thread-registry.v1'

def now_local(): return datetime.now(timezone.utc).astimezone(TZ)
def local_day(dt=None): return (dt or now_local()).astimezone(TZ).date().isoformat()
def parse_time(s):
 if not s:return None
 return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(TZ)
def load(path):
 try:return json.loads(Path(path).read_text())
 except Exception:return {'schema':SCHEMA,'timezone':'Asia/Jakarta','rollover_local':'00:00:00','days':{}}
def atomic(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as h:json.dump(data,h,indent=2,sort_keys=True);h.write('\n');h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def key(provider,profile_id):return f'{provider}:{profile_id}'
def valid_url(provider,url):
 origins={'gemini':'https://gemini.google.com','chatgpt':'https://chatgpt.com','copilot':'https://copilot.microsoft.com','qwen':'https://chat.qwen.ai','claude':'https://claude.ai','manus':'https://manus.im'}
 return bool(url and provider in origins and url.startswith(origins[provider]))
def scan_dispatches(runs_root,provider,profile_id,day):
 rows=[]
 for p in Path(runs_root).glob('*/provider-dispatch.receipt.json'):
  try:j=json.loads(p.read_text())
  except Exception:continue
  if j.get('status')!='COMMITTED' or j.get('provider')!=provider:continue
  if j.get('profile_id') not in (None,'',profile_id):continue
  dt=parse_time(j.get('committed_at'))
  if not dt or dt.date().isoformat()!=day:continue
  url=j.get('conversation_url','')
  if valid_url(provider,url):rows.append((dt,url,j,p.parent.name))
 return sorted(rows,key=lambda x:x[0])
def resolve(provider,profile_id,runs_root,registry=DEFAULT_REGISTRY,dt=None):
 day=local_day(dt);j=load(registry);rec=j.get('days',{}).get(day,{}).get(key(provider,profile_id))
 if rec and valid_url(provider,rec.get('conversation_url','')):
  return {'day':day,'timezone':'Asia/Jakarta','conversation_url':rec['conversation_url'],'source':'REGISTRY','dispatch_count':rec.get('dispatch_count',0),'success_count':rec.get('success_count',0)}
 rows=scan_dispatches(runs_root,provider,profile_id,day)
 if rows:
  urls=[]
  for _,u,_,_ in rows:
   if u not in urls:urls.append(u)
  return {'day':day,'timezone':'Asia/Jakarta','conversation_url':urls[0],'source':'DISPATCH_RECOVERY','historical_thread_count':len(urls),'duplicate_thread_violation':len(urls)>1}
 return {'day':day,'timezone':'Asia/Jakarta','conversation_url':'','source':'NEW_DAILY_THREAD'}
def record_dispatch(provider,profile_id,conversation_url,prompt_sha256,job_id,committed_at,runs_root,registry=DEFAULT_REGISTRY):
 day=parse_time(committed_at).date().isoformat() if parse_time(committed_at) else local_day()
 if not valid_url(provider,conversation_url):raise ValueError('E_DAILY_THREAD_URL')
 registry=Path(registry);lock=registry.with_suffix(registry.suffix+'.lock');lock.parent.mkdir(parents=True,exist_ok=True)
 with open(lock,'a+') as lh:
  fcntl.flock(lh,fcntl.LOCK_EX);j=load(registry);days=j.setdefault('days',{});bucket=days.setdefault(day,{});k=key(provider,profile_id);rec=bucket.get(k)
  if rec and rec.get('conversation_url')!=conversation_url:raise RuntimeError(f'E_DAILY_THREAD_VIOLATION:{rec.get("conversation_url")}!={conversation_url}')
  if not rec:rec={'provider':provider,'profile_id':profile_id,'conversation_url':conversation_url,'opened_at':committed_at,'dispatch_count':0,'success_count':0,'jobs':[],'prompt_sha256':[]};bucket[k]=rec
  if job_id not in rec['jobs']:rec['jobs'].append(job_id);rec['dispatch_count']+=1
  if prompt_sha256 not in rec['prompt_sha256']:rec['prompt_sha256'].append(prompt_sha256)
  rec['last_dispatch_at']=committed_at;atomic(registry,j);fcntl.flock(lh,fcntl.LOCK_UN)
 return rec
def mark_success(provider,profile_id,job_id,registry=DEFAULT_REGISTRY,dt=None):
 registry=Path(registry);lock=registry.with_suffix(registry.suffix+'.lock');lock.parent.mkdir(parents=True,exist_ok=True)
 with open(lock,'a+') as lh:
  fcntl.flock(lh,fcntl.LOCK_EX);j=load(registry);rec=None
  preferred=local_day(dt)
  for day in [preferred]+[d for d in sorted(j.get('days',{}),reverse=True) if d!=preferred]:
   candidate=j.get('days',{}).get(day,{}).get(key(provider,profile_id))
   if candidate and job_id in candidate.get('jobs',[]):rec=candidate;break
  if not rec:
   fcntl.flock(lh,fcntl.LOCK_UN);return None
  done=rec.setdefault('successful_jobs',[])
  if job_id not in done:done.append(job_id);rec['success_count']=len(done)
  rec['success_rate']=round(rec['success_count']/rec['dispatch_count'],6) if rec.get('dispatch_count') else 0.0;atomic(registry,j);fcntl.flock(lh,fcntl.LOCK_UN);return rec
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 r=sp.add_parser('resolve');r.add_argument('--provider',required=True);r.add_argument('--profile-id',required=True);r.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');r.add_argument('--registry',default=str(DEFAULT_REGISTRY))
 d=sp.add_parser('record-dispatch');
 for x in ['provider','profile-id','conversation-url','prompt-sha256','job-id','committed-at']:d.add_argument('--'+x,required=True)
 d.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');d.add_argument('--registry',default=str(DEFAULT_REGISTRY))
 s=sp.add_parser('mark-success');s.add_argument('--provider',required=True);s.add_argument('--profile-id',required=True);s.add_argument('--job-id',required=True);s.add_argument('--registry',default=str(DEFAULT_REGISTRY))
 ns=ap.parse_args()
 if ns.cmd=='resolve':out=resolve(ns.provider,ns.profile_id,ns.runs_root,ns.registry)
 elif ns.cmd=='record-dispatch':out=record_dispatch(ns.provider,ns.profile_id,ns.conversation_url,ns.prompt_sha256,ns.job_id,ns.committed_at,ns.runs_root,ns.registry)
 else:out=mark_success(ns.provider,ns.profile_id,ns.job_id,ns.registry)
 print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
