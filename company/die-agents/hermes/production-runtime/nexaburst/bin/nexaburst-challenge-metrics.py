#!/opt/die/factory-asset/venv/bin/python
from __future__ import annotations
import glob,json,math,statistics
from pathlib import Path
from PIL import Image

ROOT=Path('/var/lib/die/h01/nexaburst')
OUT=ROOT/'challenge'/'challenge-30-20260920'
styles={
 'soft-watercolor-clipart':'Soft Watercolor Clipart',
 'premium-semi-realistic-vector-like':'Premium Semi-Realistic Digital',
 'clean-commercial-soft-clay':'Clean Commercial Clay 3D'
}
def measure(r):
    im=Image.open(r['result']['source_path']).convert('RGB')
    w,h=im.size; pix=im.load()
    mask=[]
    border_white=0; border_total=0
    bx=int(w*.06); by=int(h*.06)
    sx=sy=n=0; xs=[];ys=[]
    for y in range(h):
        for x in range(w):
            R,G,B=pix[x,y]
            dist=((255-R)**2+(255-G)**2+(255-B)**2)**0.5
            fg=dist>18
            if fg:
                n+=1;sx+=x;sy+=y;xs.append(x);ys.append(y)
            if x<bx or x>=w-bx or y<by or y>=h-by:
                border_total+=1
                if R>247 and G>247 and B>247:border_white+=1
    if n:
        x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys)
        margins=[x0/w,(w-1-x1)/w,y0/h,(h-1-y1)/h]
        centroid=((sx/n)/w,(sy/n)/h)
        offset=math.hypot(centroid[0]-.5,centroid[1]-.5)
        clipped=min(margins)<.012
        bbox_area=((x1-x0+1)*(y1-y0+1))/(w*h)
    else:
        margins=[1,1,1,1];offset=1;clipped=True;bbox_area=0
    return {
      'asset_id':r['asset_id'],'noun':r['noun'],'style':r['style'],
      'border_white_ratio':border_white/border_total if border_total else 0,
      'foreground_ratio':n/(w*h),'bbox_area_ratio':bbox_area,
      'centroid_offset':offset,'min_margin_ratio':min(margins),'clipped':clipped,
      'bytes':r['result']['bytes'],'elapsed_ms':r['timing']['elapsed_ms']
    }
rows=[]
for p in glob.glob(str(ROOT/'receipts'/'NBVC-*.json')):
    try:r=json.load(open(p))
    except:continue
    rows.append(measure(r))
if len(rows)!=30:raise SystemExit(f'E_INCOMPLETE:{len(rows)}')
summary=[]
for style,label in styles.items():
    rr=[x for x in rows if x['style']==style]
    def avg(k):return statistics.mean(x[k] for x in rr)
    summary.append({
      'preset':label,'assets':len(rr),
      'border_white_pct':round(avg('border_white_ratio')*100,2),
      'foreground_pct':round(avg('foreground_ratio')*100,2),
      'bbox_area_pct':round(avg('bbox_area_ratio')*100,2),
      'centroid_offset_pct':round(avg('centroid_offset')*100,2),
      'min_margin_pct':round(avg('min_margin_ratio')*100,2),
      'clipped_count':sum(x['clipped'] for x in rr),
      'median_elapsed_sec':round(statistics.median(x['elapsed_ms'] for x in rr)/1000,3),
      'median_bytes':int(statistics.median(x['bytes'] for x in rr))
    })
report={'schema':'die.h01.nexaburst.visual-hygiene.v1','rows':rows,'summary':summary}
OUT.mkdir(parents=True,exist_ok=True);(OUT/'visual-hygiene.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(summary,indent=2))
