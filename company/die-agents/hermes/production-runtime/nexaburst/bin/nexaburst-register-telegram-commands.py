#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,urllib.parse,urllib.request
from pathlib import Path
COMMANDS=[
 {"command":"nexa_status","description":"Show NexaBurst lane status"},
 {"command":"nexa_pause","description":"Pause new provider submissions"},
 {"command":"nexa_stop","description":"Stop production admission"},
 {"command":"nexa_resume","description":"Resume within current Founder authorization"},
 {"command":"nexa_help","description":"Show NexaBurst founder controls"}]
def env(path):
 out={}
 for raw in Path(path).read_text(encoding="utf-8").splitlines():
  line=raw.strip()
  if not line or line.startswith("#") or "=" not in line: continue
  k,v=line.split("=",1);out[k.strip()]=v.strip().strip('"').strip("'")
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--env",required=True);a=ap.parse_args()
 e=env(a.env);token=e.get("NEXABURST_TELEGRAM_BOT_TOKEN") or e.get("TELEGRAM_BOT_TOKEN")
 if not token: raise SystemExit("E_TELEGRAM_TOKEN_MISSING")
 data=urllib.parse.urlencode({"commands":json.dumps(COMMANDS,separators=(",",":"))}).encode()
 req=urllib.request.Request(f"https://api.telegram.org/bot{token}/setMyCommands",data=data,method="POST")
 with urllib.request.urlopen(req,timeout=30) as r: payload=json.load(r)
 if not payload.get("ok"): raise SystemExit("E_SET_COMMANDS:"+str(payload))
 print(json.dumps({"status":"COMMANDS_REGISTERED","commands":[x["command"] for x in COMMANDS]}))
if __name__=="__main__":main()
