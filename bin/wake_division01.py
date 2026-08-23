#!/usr/bin/env python3
"""Division-01 wake: send briefing to pinned ChatGPT conversation.

Transport = outbound VPS -> chatgpt.com via in-page fetch inside a headed
Brave instance (Profile "plus") driven over CDP :9333. A real browser context
passes Cloudflare; raw HTTPS does not (Cf-Mitigated: challenge).

Auth chain (web backend):
  1. GET /api/auth/session -> accessToken (NextAuth web JWT)
  2. POST /backend-api/sentinel/chat-requirements -> requirements token +
     proof-of-work challenge (seed/difficulty, sha3-512)
  3. Python solves PoW (hashlib native), proof injected as
     openai-sentinel-proof-token header
  4. POST /backend-api/conversation (SSE stream parsed in-page)

Usage:
  python wake_division01.py "briefing text"           # pinned conversation
  python wake_division01.py --new "briefing text"     # new conversation + pin
  python wake_division01.py --list                    # list recent conversations
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from websocket import create_connection

DEBUG_PORT = 9333  # default: Division-01 Brave instance
CODE_HOME = Path.home() / ".codex-DIVISION-01"
WAKE_JSON = CODE_HOME / "wake.json"
CHATGPT_URL = "https://chatgpt.com/"
MAX_ITERATION = 500000


def cdp(ws, id_, method, params=None, session=None, timeout=900):
    m = {"id": id_, "method": method, "params": params or {}}
    if session:
        m["sessionId"] = session
    ws.send(json.dumps(m))
    old = ws.gettimeout()
    ws.settimeout(timeout)
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == id_:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error']}")
                return msg
    finally:
        ws.settimeout(old)


def connect():
    ver = json.loads(urllib.request.urlopen(
        f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=10).read())
    return create_connection(ver["webSocketDebuggerUrl"], timeout=60,
                             suppress_origin=True)


def get_chatgpt_session(ws):
    tabs = json.loads(urllib.request.urlopen(
        f"http://127.0.0.1:{DEBUG_PORT}/json/list", timeout=10).read())
    tab = next((p for p in tabs
                if p.get("type") == "page" and "chatgpt.com" in (p.get("url") or "")),
               None)
    if tab is None:
        r = cdp(ws, 1, "Target.createTarget", {"url": CHATGPT_URL})
        tid = r["result"]["targetId"]
        time.sleep(8)
    else:
        tid = tab["id"]
    sid = cdp(ws, 2, "Target.attachToTarget",
              {"targetId": tid, "flatten": True})["result"]["sessionId"]
    for _ in range(30):
        r = cdp(ws, 3, "Runtime.evaluate",
                {"expression": "location.origin", "returnByValue": True},
                session=sid)
        if r["result"]["result"].get("value") == "https://chatgpt.com":
            return sid
        time.sleep(2)
    raise RuntimeError("chatgpt.com tab never reached https origin")


def inpage_fetch(ws, sid, expr_id, js_body: str, timeout=900):
    expr = "(async () => {\n" + js_body + "\nreturn __ret;\n})()"
    r = cdp(ws, expr_id, "Runtime.evaluate",
            {"expression": expr, "awaitPromise": True, "returnByValue": True},
            session=sid, timeout=timeout)
    val = r["result"]["result"].get("value")
    if val is None and r["result"].get("exceptionDetails"):
        desc = r["result"]["exceptionDetails"].get("exception", {}).get("description")
        raise RuntimeError(f"in-page error: {desc}")
    if val is None:
        raise RuntimeError("in-page returned null")
    status, _, payload = str(val).partition("|")
    if status != "200":
        raise RuntimeError(f"E_WAKE_{status}: {payload[:400]}")
    return payload


# ---------- step 1: gather session + sentinel challenge (in-page) ----------
JS_PREPARE = """
const sess = await (await fetch('/api/auth/session', {credentials: 'include'})).json();
if (!sess.accessToken) {
  __ret = '401|no web session accessToken - login chatgpt.com di Brave profil plus';
} else {
  const didPair = document.cookie.split('; ').find(c => c.startsWith('oai-did='));
  const didVal = didPair ? didPair.split('=')[1] : crypto.randomUUID();
  const rr = await fetch('/backend-api/sentinel/chat-requirements', {
    method: 'POST', credentials: 'include',
    headers: {'Authorization': 'Bearer ' + sess.accessToken,
              'Content-Type': 'application/json',
              'oai-device-id': didVal, 'oai-language': 'en-US'},
    body: '{}'
  });
  const req = await rr.json();
  __ret = '200|' + JSON.stringify({
    accessToken: sess.accessToken,
    deviceId: didVal,
    reqToken: req.token,
    persona: req.persona,
    pow: req.proofofwork || {},
    turnstile: req.turnstile || {},
    ua: navigator.userAgent,
    screen: [screen.width, screen.height],
    depth: screen.colorDepth,
    avail: [screen.availWidth, screen.availHeight],
    cores: navigator.hardwareConcurrency,
    lang: navigator.language,
    langs: navigator.languages.join(','),
    tzOffset: new Date().getTimezoneOffset(),
  });
}
"""


# ---------- step 2: PoW solver (python, sha3-512) ----------
def solve_pow(seed: str, difficulty: str, env: dict) -> str:
    t0 = time.perf_counter() * 1000
    now = time.localtime()
    parse_time = time.strftime("%a %b %d %Y %H:%M:%S", now) + \
        f" GMT{-(-env['tzOffset']//60):+03d}00 ({time.tzname[0]})"
    config = [
        env["screen"][0] + env["screen"][1],
        parse_time,
        4294705152,
        0,
        env["ua"],
        "",
        "",
        env["lang"],
        env["langs"],
        0,
        "webdriver-false",
        "__NEXT_DATA__",
        "chrome",
        t0,
        str(uuid.uuid4()),
        "",
        env["cores"] or 8,
        time.time() * 1000 - t0,
    ]
    enc = json.dumps
    p1 = (enc(config[:3], separators=(",", ":"), ensure_ascii=False)[:-1] + ",").encode()
    p2 = ("," + enc(config[4:9], separators=(",", ":"), ensure_ascii=False)[1:-1] + ",").encode()
    p3 = (","+enc(config[10:], separators=(",", ":"), ensure_ascii=False)[1:]).encode()
    seed_b = seed.encode()
    target = bytes.fromhex(difficulty)
    dlen = len(target)
    for i in range(MAX_ITERATION):
        blob = p1 + str(i).encode() + p2 + str(i >> 1).encode() + p3
        b64 = base64.b64encode(blob)
        h = hashlib.sha3_512(seed_b + b64).digest()
        if h[:dlen] <= target:
            print(f"[wake] pow solved in {i+1} iterations", file=sys.stderr)
            return base64.b64encode(blob).decode()
    raise RuntimeError("pow not solved within iteration limit")


# ---------- step 3: conversation POST with proof (in-page) ----------
JS_WAKE_TMPL = """
const sessInfo = __PREP_JSON__;
const body = {
  action: 'next',
  messages: [{id: crypto.randomUUID(), author: {role: 'user'},
              content: {content_type: 'text', parts: [__BRIEFING_JSON__]},
              metadata: {}}],
  parent_message_id: crypto.randomUUID(),
  model: 'auto',
  timezone_offset_min: -420,
  conversation_mode: {kind: 'primary_assistant'},
  system_hints: [],
};
__CONV_LINE__
const headers = {
  'Authorization': 'Bearer ' + sessInfo.accessToken,
  'Content-Type': 'application/json',
  'Accept': 'text/event-stream',
  'oai-device-id': sessInfo.deviceId,
  'oai-language': 'en-US',
};
if (sessInfo.reqToken) headers['openai-sentinel-chat-requirements-token'] = sessInfo.reqToken;
if (__PROOF__) headers['openai-sentinel-proof-token'] = __PROOF__;
const r = await fetch('/backend-api/conversation', {
  method: 'POST', headers, credentials: 'include',
  body: JSON.stringify(body),
});
if (!r.ok) {
  const t = await r.text();
  __ret = r.status + '|' + t.slice(0, 400);
} else {
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = '', lastParts = null, convId = null;
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buf += dec.decode(value, {stream: true});
    let idx;
    while ((idx = buf.indexOf('\\n')) >= 0) {
      const line = buf.slice(0, idx).trim(); buf = buf.slice(idx + 1);
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6);
      if (payload === '[DONE]') continue;
      try {
        const ev = JSON.parse(payload);
        if (ev.conversation_id) convId = ev.conversation_id;
        if (ev.message && ev.message.author && ev.message.author.role === 'assistant') {
          lastParts = ev.message.content && ev.message.content.parts;
        }
      } catch (e) {}
    }
  }
  __ret = '200|' + JSON.stringify({conversation_id: convId,
    reply: lastParts ? lastParts[lastParts.length - 1] : null});
}
"""


def build_wake_js(prep: dict, briefing: str, conv_id: str | None, proof: str | None) -> str:
    conv_line = f"body.conversation_id = {json.dumps(conv_id)};" if conv_id else ""
    js = (JS_WAKE_TMPL
          .replace("__PREP_JSON__", json.dumps(
              {"accessToken": prep["accessToken"], "deviceId": prep["deviceId"],
               "reqToken": prep["reqToken"]}))
          .replace("__BRIEFING_JSON__", json.dumps(briefing))
          .replace("__CONV_LINE__", conv_line))
    if proof:
        js = js.replace("__PROOF__", json.dumps(proof))
    else:
        js = js.replace("if (__PROOF__) headers['openai-sentinel-proof-token'] = __PROOF__;", "")
    return js


def save_conv_id(cid: str):
    cfg = json.loads(WAKE_JSON.read_text()) if WAKE_JSON.exists() else {}
    cfg["conversation_id"] = cid
    WAKE_JSON.parent.mkdir(parents=True, exist_ok=True)
    WAKE_JSON.write_text(json.dumps(cfg, indent=2), encoding="utf8")
    print(f"[wake] pinned conversation_id={cid}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefing", nargs="*")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--port", type=int, default=None, help="CDP port (default 9333 Division, 9110 BrowserOS neo)")
    ap.add_argument("--home", default=None, help="wake.json home dir")
    args = ap.parse_args()

    global DEBUG_PORT, CODE_HOME, WAKE_JSON
    if args.port:
        DEBUG_PORT = args.port
    if args.home:
        CODE_HOME = Path(args.home)
        WAKE_JSON = CODE_HOME / "wake.json"
    ws = connect()
    sid = get_chatgpt_session(ws)

    if args.list:
        print(inpage_fetch(ws, sid, 10, JS_LIST)[:3000])
        return

    text = " ".join(args.briefing).strip()
    if not text:
        sys.exit('usage: wake_division01.py [--new|--list] "briefing"')

    prep = json.loads(inpage_fetch(ws, sid, 20, JS_PREPARE))
    print(f"[wake] persona={prep.get('persona')} pow_required={prep.get('pow', {}).get('required')}",
          file=sys.stderr)

    proof = None
    if prep.get("pow", {}).get("required"):
        proof = "gAAAAAB" + solve_pow(prep["pow"]["seed"], prep["pow"]["difficulty"], prep)

    cfg = json.loads(WAKE_JSON.read_text()) if WAKE_JSON.exists() else {}
    pinned = None if args.new else cfg.get("conversation_id")
    payload = json.loads(inpage_fetch(
        ws, sid, 21, build_wake_js(prep, text, pinned, proof)))
    cid = payload.get("conversation_id")
    if cid and not pinned:
        save_conv_id(cid)
    print(f"[wake] conversation_id={cid}", file=sys.stderr)
    print(payload.get("reply"))


JS_LIST = """
const sess = await (await fetch('/api/auth/session', {credentials: 'include'})).json();
if (!sess.accessToken) {
  __ret = '401|no web session accessToken';
} else {
  const r = await fetch('/backend-api/conversations?limit=10',
    {headers: {'Authorization': 'Bearer ' + sess.accessToken}, credentials: 'include'});
  const t = await r.text();
  __ret = r.status + '|' + t;
}
"""

if __name__ == "__main__":
    main()
