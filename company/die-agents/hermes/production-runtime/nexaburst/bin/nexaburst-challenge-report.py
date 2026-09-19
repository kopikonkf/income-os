#!/opt/die/factory-asset/venv/bin/python
from __future__ import annotations
import glob, json, os, statistics, urllib.parse, urllib.request, uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ENV=Path('/home/kopiko/.config/die/nexaburst.env')
ROOT=Path('/var/lib/die/h01/nexaburst')
OUT=ROOT/'challenge'/'challenge-30-20260920'
RECEIPTS=ROOT/'receipts'
PRESETS=[
 ('WC','soft-watercolor-clipart','Soft Watercolor Clipart'),
 ('SR','premium-semi-realistic-vector-like','Premium Semi-Realistic Digital'),
 ('CLAY','clean-commercial-soft-clay','Clean Commercial Clay 3D'),
]

def env():
    if ENV.is_file():
        for raw in ENV.read_text().splitlines():
            if raw.strip() and not raw.lstrip().startswith('#') and '=' in raw:
                k,v=raw.split('=',1); os.environ.setdefault(k.strip(),v.strip())

def font(size,bold=False):
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for p in paths:
        try:return ImageFont.truetype(p,size)
        except:pass
    return ImageFont.load_default()

def load_rows():
    rows=[]
    for p in glob.glob(str(RECEIPTS/'NBVC-*.json')):
        try:d=json.load(open(p))
        except:continue
        if d.get('result',{}).get('status')=='DONE': rows.append(d)
    return rows

def sheet(rows,style,label):
    chosen=sorted([r for r in rows if r.get('style')==style],key=lambda r:r['asset_id'])
    if len(chosen)!=10: raise RuntimeError(f'E_CHALLENGE_INCOMPLETE:{style}:{len(chosen)}')
    tile=300; label_h=48; title_h=80; cols=5; rows_n=2
    canvas=Image.new('RGB',(cols*tile, title_h+rows_n*(tile+label_h)),'white')
    draw=ImageDraw.Draw(canvas)
    draw.text((24,18),f'NexaBurst Visual Challenge · {label}',font=font(26,True),fill='black')
    draw.text((24,50),'Same 10 subjects · deterministic typed prompts · provider originals',font=font(14),fill='black')
    for i,r in enumerate(chosen):
        src=Path(r['result']['source_path'])
        im=Image.open(src).convert('RGB')
        fit=ImageOps.contain(im,(tile-24,tile-24))
        x=(i%cols)*tile+(tile-fit.width)//2
        y=title_h+(i//cols)*(tile+label_h)+(tile-fit.height)//2
        canvas.paste(fit,(x,y))
        noun=r.get('noun','')
        txt=f'{i+1:02d}. {noun}'
        tw=draw.textbbox((0,0),txt,font=font(15,True))[2]
        lx=(i%cols)*tile+(tile-tw)//2
        ly=title_h+(i//cols)*(tile+label_h)+tile+10
        draw.text((lx,ly),txt,font=font(15,True),fill='black')
    return canvas

def multipart(url,fields,file_path):
    boundary='----NB'+uuid.uuid4().hex
    parts=[]
    for k,v in fields.items():
        if v is None or str(v)=='':continue
        parts += [f'--{boundary}\r\n'.encode(),f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(),str(v).encode(),b'\r\n']
    p=Path(file_path)
    parts += [f'--{boundary}\r\n'.encode(),f'Content-Disposition: form-data; name="photo"; filename="{p.name}"\r\n'.encode(),
              b'Content-Type: image/jpeg\r\n\r\n',p.read_bytes(),b'\r\n',f'--{boundary}--\r\n'.encode()]
    req=urllib.request.Request(url,data=b''.join(parts),method='POST',headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())

def send_text(token,chat,thread,text):
    data={'chat_id':chat,'message_thread_id':thread,'text':text,'disable_web_page_preview':'true'}
    req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',data=urllib.parse.urlencode(data).encode(),method='POST')
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def main():
    env(); OUT.mkdir(parents=True,exist_ok=True)
    rows=load_rows()
    if len(rows)<30: raise SystemExit(f'E_CHALLENGE_INCOMPLETE:{len(rows)}/30')
    token=os.environ['NEXABURST_TELEGRAM_BOT_TOKEN']; chat=os.environ['NEXABURST_TELEGRAM_CHAT_ID']; thread=os.environ['NEXABURST_TELEGRAM_THREAD_ID']
    stats=[]
    for tag,style,label in PRESETS:
        rr=[r for r in rows if r.get('style')==style]
        t=[r['timing']['elapsed_ms']/1000 for r in rr]
        stats.append((label,len(rr),statistics.median(t),statistics.mean(t),sum(r['result']['bytes'] for r in rr)))
        img=sheet(rows,style,label)
        p=OUT/f'{tag.lower()}-contact-sheet.jpg'; img.save(p,'JPEG',quality=92,optimize=True)
        resp=multipart(f'https://api.telegram.org/bot{token}/sendPhoto',
           {'chat_id':chat,'message_thread_id':thread,'caption':f'NexaBurst · Visual Challenge\nPreset: {label}\n10 subjects · provider originals · no upscale'},
           p)
        if not resp.get('ok'): raise RuntimeError(resp)
    lines=['NexaBurst · 30-Render Challenge Complete','────────────────────────────',
           '30/30 provider originals are ready.','']
    for label,n,med,mean,b in stats:
        lines += [label,f'  Assets : {n}',f'  Median : {med:.2f}s',f'  Mean   : {mean:.2f}s',f'  Raw    : {b/1024:.0f} KiB','']
    lines += ['Next gate: visual Founder QC → choose one champion preset → 100-noun market canary.',
              'Vault remains separate and activates only after V2 reaches WAITING_FOUNDER_QC.']
    resp=send_text(token,chat,thread,'\n'.join(lines))
    manifest={'schema':'die.h01.nexaburst.visual-challenge-report.v1','rows':len(rows),'stats':[{'preset':x[0],'assets':x[1],'median_sec':x[2],'mean_sec':x[3],'raw_bytes':x[4]} for x in stats],
              'contact_sheets':[str(p) for p in sorted(OUT.glob('*-contact-sheet.jpg'))],'telegram_message_id':(resp.get('result') or {}).get('message_id')}
    (OUT/'report.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))
if __name__=='__main__':main()
