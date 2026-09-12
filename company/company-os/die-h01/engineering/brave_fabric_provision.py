#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
ROOT=Path('/var/lib/die/h01/browser')
TEMPLATE=Path('/etc/die/h01/brave/profile-preferences-template.json')
MANIFEST=ROOT/'fabric-manifest-v1.json'

def loadj(p):
    with p.open() as f: return json.load(f)

def merge(dst,src):
    for k,v in src.items():
        if isinstance(v,dict) and isinstance(dst.get(k),dict): merge(dst[k],v)
        else: dst[k]=v

def ensure():
    t=loadj(TEMPLATE); rows=[]
    for n in range(1,101):
        shard=(n-1)//5+1; slot=(n-1)%5+1
        sid=f'h01-web-s{shard:02d}'; pid=f'h01-web-p{n:03d}'
        udd=ROOT/sid; prof=udd/pid; pref=prof/'Preferences'
        udd.mkdir(parents=True,exist_ok=True); prof.mkdir(parents=True,exist_ok=True); (udd/'First Run').touch(exist_ok=True)
        try: cur=loadj(pref) if pref.exists() else {}
        except Exception: cur={}
        merge(cur,t)
        with pref.open('w') as f: json.dump(cur,f,separators=(',',':'),sort_keys=True)
        os.chmod(udd,0o700); os.chmod(prof,0o700); os.chmod(pref,0o600)
        rows.append({'udd_id':sid,'udd_index':shard,'slot':slot,'profile_id':pid,'profile_number':n,'user_data_dir':str(udd),'profile_directory':pid,'cdp_host':'127.0.0.1','cdp_port':9200+n,'state':'PROVISIONED_NOT_AUTHENTICATED'})
    manifest={'schema':'die.h01.brave-fabric.host-local.v1','browser':'brave-stable','browser_binary':'/usr/bin/brave-browser','topology':{'udd_count':20,'profiles_per_udd':5,'profile_count':100,'max_active_per_udd':1},'profile_template':str(TEMPLATE),'managed_policy':'/etc/brave/policies/managed/die-h01-runtime.json','profiles':rows}
    with MANIFEST.open('w') as f: json.dump(manifest,f,indent=2)
    os.chmod(MANIFEST,0o640)

def validate():
    errors=[]
    checks=[(('brave','brave_search','show-ntp-search'),False),(('brave','new_tab_page','show_background_image'),False),(('brave','new_tab_page','show_stats'),False),(('ntp','shortcust_visible'),False),(('translate','enabled'),False)]
    def get(d,path):
        for k in path: d=d[k]
        return d
    seen=set()
    for n in range(1,101):
        shard=(n-1)//5+1; sid=f'h01-web-s{shard:02d}'; pid=f'h01-web-p{n:03d}'; pref=ROOT/sid/pid/'Preferences'; port=9200+n
        if not pref.exists(): errors.append(f'{pid}:missing Preferences'); continue
        try: d=loadj(pref)
        except Exception as e: errors.append(f'{pid}:bad json:{e}'); continue
        for path,expected in checks:
            try: actual=get(d,path)
            except Exception: errors.append(f'{pid}:missing {".".join(path)}'); continue
            if actual!=expected: errors.append(f'{pid}:{".".join(path)}={actual!r}')
        if port in seen: errors.append(f'{pid}:duplicate port {port}')
        seen.add(port)
    udd_count=len(list(ROOT.glob('h01-web-s??'))); profile_count=sum(1 for _ in ROOT.glob('h01-web-s??/h01-web-p???'))
    if udd_count!=20: errors.append(f'udd_count={udd_count}')
    if profile_count!=100: errors.append(f'profile_count={profile_count}')
    print(json.dumps({'status':'PASS' if not errors else 'FAIL','udd_count':udd_count,'profile_count':profile_count,'cdp_range':'9201-9300','errors':errors[:100]},indent=2))
    return 0 if not errors else 1

cmd=sys.argv[1] if len(sys.argv)>1 else 'validate'
if cmd=='ensure': ensure(); sys.exit(validate())
if cmd=='validate': sys.exit(validate())
print('usage: h01-brave-provision [ensure|validate]',file=sys.stderr); sys.exit(64)
