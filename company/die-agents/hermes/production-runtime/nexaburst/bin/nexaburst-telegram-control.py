#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst')
STATE=ROOT/'state'
ENV=Path('/home/kopiko/.config/die/nexaburst.env')
CONTROL=SESSION/'bin'/'nexaburst-control.py'
OFFSET=STATE/'telegram-control-offset.json'
AUDIT=STATE/'telegram-control-audit.jsonl'

def load_env():
    out={}
    for line in ENV.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1);out[k]=v.strip().strip('"').strip("'")
    return out
E=load_env()
TOKEN=E.get('NEXABURST_TELEGRAM_BOT_TOKEN') or E.get('TELEGRAM_BOT_TOKEN')
CHAT=int(E.get('NEXABURST_TELEGRAM_CHAT_ID','0'))
DEFAULT_THREAD=int(E.get('NEXABURST_TELEGRAM_THREAD_ID','0') or 0)
if not TOKEN or not CHAT: raise SystemExit('E_TELEGRAM_CONTROL_CONFIG')

def api(method,data=None,timeout=60):
    data={} if data is None else data
    req=urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{method}',
                               data=urllib.parse.urlencode(data).encode(),method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        raise RuntimeError(f'TELEGRAM_HTTP_{e.code}:{body[:300]}')

def send(text,thread=None,use_default=False):
    d={'chat_id':str(CHAT),'text':text,'disable_web_page_preview':'true'}
    tid=DEFAULT_THREAD if use_default and thread is None else thread
    if tid:d['message_thread_id']=str(tid)
    return api('sendMessage',d,20)

def audit(event,**kw):
    row={'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':event,**kw}
    with AUDIT.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')

def offset_get():
    try:return int(json.loads(OFFSET.read_text()).get('offset',0))
    except:return 0

def offset_set(v):
    tmp=OFFSET.with_name(OFFSET.name+f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps({'offset':int(v)})+'\n');os.replace(tmp,OFFSET)

def admin(chat_id,user_id):
    try:
        d=api('getChatAdministrators',{'chat_id':str(chat_id)},15)
        if d.get('ok'):
            return any(int(((x.get('user') or {}).get('id') or 0))==int(user_id) for x in (d.get('result') or []))
    except Exception:
        pass
    try:
        d=api('getChatMember',{'chat_id':str(chat_id),'user_id':str(user_id)},15)
        return d.get('ok') and (d.get('result') or {}).get('status') in {'creator','administrator'}
    except Exception:return False

def control_status():
    cp=subprocess.run([str(CONTROL),'status'],text=True,capture_output=True,timeout=30,check=False)
    if cp.returncode!=0:raise RuntimeError((cp.stderr or cp.stdout)[-400:])
    return json.loads(cp.stdout)

def set_mode(mode,reason,actor):
    cp=subprocess.run([str(CONTROL),'set','--mode',mode,'--reason',reason,'--actor',actor],
                      text=True,capture_output=True,timeout=20,check=False)
    if cp.returncode!=0:raise RuntimeError((cp.stderr or cp.stdout)[-400:])
    return json.loads(cp.stdout)

def tabs():
    try:
        with urllib.request.urlopen('http://127.0.0.1:9311/json/list',timeout=2) as r:d=json.load(r)
        return sum(1 for x in d if str(x.get('url','')).startswith('https://nexabot.id/'))
    except:return 0

def fmt_status():
    d=control_status(); c=d['control'];h=d['health'];s=d['stats']
    return (
      'NexaBurst · Control Status\n'
      '────────────────────────────\n'
      f"Control       : {c.get('mode')}\n"
      f"Reason        : {c.get('reason','-')}\n"
      f"Nexa login    : {'OK' if h.get('authenticated') else 'NO'}\n"
      f"Unlimited     : {'ACTIVE' if h.get('unlimited_active') else 'INACTIVE'}\n"
      f"First-100     : {s.get('first100_complete',0)}/100 complete"
      f" · {s.get('first100_failed',0)} retry/block · {s.get('first100_pending',0)} pending\n"
      f"WC reservoir  : {s.get('complete',0)}/{s.get('total',0)} complete\n"
      f"Technical gate: {d.get('phase1_pause') or 'none'}\n"
      f"Runner        : {'RUNNING' if d.get('runner_alive') else 'IDLE'}\n"
      f"V2 worker     : {'RUNNING' if d.get('v2_alive') else 'IDLE'}"
      f" · RealESRGAN {'ACTIVE' if d.get('realesrgan_active') else 'idle'}\n"
      f"Browser tabs  : {tabs()} Nexa\n"
      f"Disk free     : {d.get('disk_free_gib')} GiB\n"
      'Full 42.5K    : LOCKED (first-100 only)'
    )

def register_commands():
    commands=[
      {'command':'nexa_status','description':'Show NexaBurst production status'},
      {'command':'nexa_pause','description':'Pause new submits; drain V2/Vault safely'},
      {'command':'nexa_stop','description':'Hard stop new submits and new V2 work'},
      {'command':'nexa_resume','description':'Resume only the currently authorized window'},
      {'command':'nexa_help','description':'Show NexaBurst control commands'},
    ]
    scope=json.dumps({'type':'chat','chat_id':CHAT},separators=(',',':'))
    api('setMyCommands',{'commands':json.dumps(commands,separators=(',',':')),'scope':scope},20)

def handle(msg):
    if int((msg.get('chat') or {}).get('id',0))!=CHAT:return
    text=str(msg.get('text') or '').strip()
    if not text.startswith('/nexa_'):return
    thread=msg.get('message_thread_id')
    user=msg.get('from') or {};uid=int(user.get('id',0))
    cmdline=text.split(maxsplit=1);cmd=cmdline[0].split('@',1)[0].lower();arg=cmdline[1].strip() if len(cmdline)>1 else ''
    audit('COMMAND_RECEIVED',command=cmd,thread=thread,user_id=uid,username=user.get('username'))
    if not admin(CHAT,uid):
        audit('COMMAND_DENIED',command=cmd,thread=thread,user_id=uid)
        send('NexaBurst control denied: only Telegram group administrators can operate production controls.',thread);return
    actor=f"telegram:{uid}:{user.get('username') or user.get('first_name') or 'admin'}"
    if cmd=='/nexa_status': audit('COMMAND_OK',command=cmd,user_id=uid);send(fmt_status(),thread);return
    if cmd=='/nexa_help':
        audit('COMMAND_OK',command=cmd,user_id=uid)
        send('NexaBurst · Founder Controls\n────────────────────────────\n'
             '/nexa_status — read-only status\n'
             '/nexa_pause [reason] — stop new provider submits; V2/Vault drain safely\n'
             '/nexa_stop [reason] — stop new submits and stop V2 taking new work after current item\n'
             '/nexa_resume [reason] — resume only current authorized window; technical gates still apply\n\n'
             'Full 42.5K cannot be unlocked by these commands.',thread);return
    if cmd=='/nexa_pause':
        set_mode('PAUSED',arg or 'Founder Telegram pause',actor)
        audit('COMMAND_OK',command=cmd,user_id=uid,mode='PAUSED')
        send('NexaBurst · PAUSED\nNo new provider submit will start. Current in-flight job may finish; V2 and Vault may drain existing work.',thread);return
    if cmd=='/nexa_stop':
        set_mode('STOPPED',arg or 'Founder Telegram emergency stop',actor)
        audit('COMMAND_OK',command=cmd,user_id=uid,mode='STOPPED')
        send('NexaBurst · STOPPED\nNo new provider submit will start. V2 will not take a new item after any active item finishes. Vault remains available for already-completed artifacts.',thread);return
    if cmd=='/nexa_resume':
        set_mode('RUNNING',arg or 'Founder Telegram resume',actor)
        audit('COMMAND_OK',command=cmd,user_id=uid,mode='RUNNING')
        st=control_status(); gate=st.get('phase1_pause')
        send('NexaBurst · RESUME AUTHORIZED\nCurrent authorized window may run when health/auth/Unlimited/disk gates pass.'
             + (f'\nTechnical gate still present: {gate}' if gate else '')
             + '\nFull 42.5K remains LOCKED.',thread);return

def main():
    register_commands()
    off=offset_get()
    while True:
        try:
            d=api('getUpdates',{'offset':str(off),'timeout':'50','allowed_updates':json.dumps(['message'])},60)
            if not d.get('ok'):time.sleep(5);continue
            for u in d.get('result') or []:
                off=max(off,int(u.get('update_id',0))+1); offset_set(off)
                try:handle(u.get('message') or {})
                except Exception as e:
                    try:send('NexaBurst control error: '+str(e)[:300],DEFAULT_THREAD)
                    except Exception:pass
        except Exception:
            time.sleep(5)
if __name__=='__main__':main()
