#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,datetime
from pathlib import Path

def run(args):return subprocess.run(args,text=True,capture_output=True,check=False,timeout=10)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--external-port',type=int,default=25013);ap.add_argument('--external-probe',choices=['PROVEN','UNKNOWN'],default='UNKNOWN');a=ap.parse_args()
 ssh=run(['sudo','sshd','-T']);eff={}
 for line in ssh.stdout.splitlines():
  if ' ' in line:
   k,v=line.split(' ',1)
   if k in {'port','permitrootlogin','passwordauthentication','kbdinteractiveauthentication','pubkeyauthentication','authenticationmethods','allowusers','maxauthtries','maxstartups','logingracetime','clientaliveinterval','clientalivecountmax'}:eff[k]=v
 ss=run(['ss','-ltn']).stdout
 loopback_ports={int(m.group(1)) for m in re.finditer(r'127\.0\.0\.1:(\d+)',ss)}
 sensitive={39121,39122,39221,39222}
 cf=Path('/etc/die/staging/cloudflare/linux-mcp.yml');routes=[]
 try:
  if cf.is_file():
   for line in cf.read_text().splitlines():
    s=line.strip()
    if s.startswith('hostname:') or s.startswith('- hostname:') or s.startswith('service:'):routes.append(s)
 except PermissionError:
  routes=['UNKNOWN_PERMISSION_DENIED_USE_PRIVILEGED_SANITIZED_AUDIT']
 exposed=sorted(p for p in sensitive if p not in loopback_ports)
 out={'schema':'die.factory-asset.fa310-management-ingress-audit.v1','observed_at':now(),'guest_sshd':eff,'external_nat':{'public_port':a.external_port,'guest_port':int(eff.get('port','0') or 0),'external_probe':a.external_probe,'nat_distinguished':a.external_port!=int(eff.get('port','0') or 0)},'loopback_sensitive_ports':sorted(sensitive & loopback_ports),'sensitive_ports_not_proven_loopback':exposed,'cloudflare_linux_mcp_routes':routes,'cloudflare_exposes_browser_or_broker_port':any(str(p) in ' '.join(routes) for p in sensitive),'hardening_pass':eff.get('permitrootlogin')=='no' and eff.get('passwordauthentication')=='no' and eff.get('kbdinteractiveauthentication')=='no' and eff.get('pubkeyauthentication')=='yes' and int(eff.get('maxauthtries','99'))<=3 and int(eff.get('logingracetime','999'))<=30 and a.external_probe=='PROVEN' and not exposed and not any(str(p) in ' '.join(routes) for p in sensitive),'credential_values_read':False,'private_key_values_read':False}
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
