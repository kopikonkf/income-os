#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

ENV=Path('/home/kopiko/.config/die/nexaburst.env')

def load_env():
    if ENV.is_file():
        for raw in ENV.read_text(encoding='utf-8').splitlines():
            line=raw.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1)
            os.environ.setdefault(k.strip(),v.strip())

def truthy(v:str|None)->bool:
    return str(v or '').strip().lower() in {'1','true','yes','on'}

def render_message(event,text):
    titles={
      'BATCH_SUMMARY':'NexaBurst · Batch Summary',
      'JOB_FAILED':'NexaBurst · Job Needs Attention',
      'BROWSER_ROTATE':'NexaBurst · Browser Refresh',
      'BROWSER_MANAGER_FAILED':'NexaBurst · Browser Manager Alert',
      'WAITING_FOUNDER_QC':'NexaBurst · Ready for Founder QC',
      'V2_FAILED':'NexaBurst · Post-Processing Alert',
      'ROUTING_TEST':'NexaBurst · Routing Test',
      'CHALLENGE_STARTED':'NexaBurst · 30-Render Challenge Started',
      'CHALLENGE_COMPLETE':'NexaBurst · 30-Render Challenge Complete'
    }
    title=titles.get(event,'NexaBurst · '+event.replace('_',' ').title())
    pairs=re.findall(r'([A-Za-z0-9_]+)=([^\s]+)',text)
    if pairs and len(' '.join(f'{k}={v}' for k,v in pairs)) >= max(1,len(text.strip())-10):
        labels={'status':'Status','total':'Total','ok':'Succeeded','fail':'Failed','skip':'Skipped','asset':'Asset','noun':'Noun','elapsed_sec':'Elapsed','workspace':'Workspace','exit':'Exit code','reason':'Reason'}
        body='\n'.join(f'{labels.get(k,k.replace("_"," ").title()):<12}: {v}' for k,v in pairs)
    else:
        body=text.strip()
    return f'{title}\n'+'─'*28+f'\n{body}'

def main():
    load_env()
    ap=argparse.ArgumentParser()
    ap.add_argument('--event',required=True)
    ap.add_argument('--text',required=True)
    ap.add_argument('--silent',action='store_true')
    a=ap.parse_args()
    if not truthy(os.getenv('NEXABURST_NOTIFY_ENABLED','true')):
        print(json.dumps({'status':'SKIP','reason':'disabled'})); return 0
    token=os.getenv('NEXABURST_TELEGRAM_BOT_TOKEN','').strip()
    chat=os.getenv('NEXABURST_TELEGRAM_CHAT_ID','').strip()
    thread=os.getenv('NEXABURST_TELEGRAM_THREAD_ID','').strip()
    if not token or not chat:
        print(json.dumps({'status':'BLOCKED','code':'E_NOTIFY_CONFIG'})); return 2
    data={
      'chat_id':chat,
      'text':render_message(a.event,a.text),
      'disable_notification':'true' if a.silent else 'false',
      'disable_web_page_preview':'true',
    }
    if thread:
        data['message_thread_id']=thread
    req=urllib.request.Request(
      f'https://api.telegram.org/bot{token}/sendMessage',
      data=urllib.parse.urlencode(data).encode(),
      method='POST',
      headers={'Content-Type':'application/x-www-form-urlencoded'}
    )
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            payload=json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(json.dumps({'status':'FAILED','code':'E_NOTIFY_HTTP','error':str(e)})); return 3
    if not payload.get('ok'):
        print(json.dumps({'status':'FAILED','code':'E_NOTIFY_API','description':payload.get('description')})); return 4
    msg=payload.get('result') or {}
    print(json.dumps({'status':'SENT','message_id':msg.get('message_id'),'message_thread_id':msg.get('message_thread_id'),'event':a.event}))
    return 0
if __name__=='__main__':
    raise SystemExit(main())
