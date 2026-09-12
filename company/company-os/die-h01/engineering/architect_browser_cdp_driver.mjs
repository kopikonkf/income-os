#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import readline from 'node:readline';

function arg(name, fallback = '') {
  const i = process.argv.indexOf(name);
  return i >= 0 ? String(process.argv[i + 1] || '') : fallback;
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function running(child) { return child && child.exitCode === null && child.signalCode === null; }
function fail(code, detail = '') {
  process.stdout.write(JSON.stringify({ status: 'ERROR', error: code, detail: String(detail).slice(0, 300) }) + '\n');
  process.exitCode = 2;
}

class Cdp {
  constructor(wsUrl) { this.wsUrl = wsUrl; this.ws = null; this.seq = 0; this.pending = new Map(); }
  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('E_CDP_WS_TIMEOUT')), 15000);
      this.ws.addEventListener('open', () => { clearTimeout(timer); resolve(); });
      this.ws.addEventListener('error', () => { clearTimeout(timer); reject(new Error('E_CDP_WS')); });
    });
    this.ws.addEventListener('message', (event) => {
      let msg; try { msg = JSON.parse(String(event.data)); } catch { return; }
      if (!msg.id || !this.pending.has(msg.id)) return;
      const p = this.pending.get(msg.id); this.pending.delete(msg.id);
      if (msg.error) p.reject(new Error(`E_CDP_RPC:${msg.error.message || 'unknown'}`)); else p.resolve(msg.result || {});
    });
  }
  send(method, params = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return Promise.reject(new Error('E_CDP_NOT_OPEN'));
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`E_CDP_RPC_TIMEOUT:${method}`)); }, 15000);
      this.pending.set(id, { resolve: (v) => { clearTimeout(timer); resolve(v); }, reject: (e) => { clearTimeout(timer); reject(e); } });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { try { this.ws?.close(); } catch {} }
}

async function readBootstrap() {
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line.trim()) continue;
    const obj = JSON.parse(line);
    if (!obj.bootstrap || typeof obj.bootstrap !== 'string') throw new Error('E_BOOTSTRAP_STDIN');
    return obj.bootstrap;
  }
  throw new Error('E_BOOTSTRAP_STDIN_EOF');
}

async function waitPort(profileDir, child) {
  const file = path.join(profileDir, 'DevToolsActivePort');
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (!running(child)) throw new Error(`E_BROWSER_EXITED:${child.exitCode ?? child.signalCode}`);
    if (fs.existsSync(file)) {
      const port = Number.parseInt(fs.readFileSync(file, 'utf8').split(/\r?\n/, 1)[0] || '', 10);
      if (Number.isInteger(port) && port > 0 && port <= 65535) return port;
    }
    await sleep(100);
  }
  throw new Error('E_DEVTOOLS_PORT_TIMEOUT');
}

async function targets(port) {
  const r = await fetch(`http://127.0.0.1:${port}/json/list`, { signal: AbortSignal.timeout(10000) });
  if (!r.ok) throw new Error(`E_CDP_LIST_HTTP_${r.status}`);
  return await r.json();
}

async function selectTarget(port) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    const list = await targets(port);
    const page = list.find(x => x.type === 'page' && String(x.url || '').startsWith('https://chatgpt.com')) || list.find(x => x.type === 'page');
    if (page?.webSocketDebuggerUrl) return page;
    await sleep(250);
  }
  throw new Error('E_CHATGPT_TARGET_TIMEOUT');
}

async function evaluate(cdp, expression, awaitPromise = true) {
  const out = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise, userGesture: true });
  if (out.exceptionDetails) throw new Error('E_RUNTIME_EVALUATE');
  return out.result?.value;
}

async function readiness(cdp) {
  return await evaluate(cdp, `(() => {
    const url=location.href;
    const composer=document.querySelector('#prompt-textarea, textarea, [contenteditable="true"]');
    const login=[...document.querySelectorAll('button,a')].some(e => /^(log in|sign in)$/i.test((e.innerText||e.textContent||'').trim()));
    return {url, ready:!!composer && !login, authRequired:login || /auth|login|signup/i.test(url)};
  })()`);
}

async function waitReady(cdp) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    const r = await readiness(cdp).catch(() => ({ ready:false, authRequired:false, url:'' }));
    if (r.authRequired) throw new Error('E_AUTH_REQUIRED');
    if (r.ready) return r;
    await sleep(500);
  }
  throw new Error('E_COMPOSER_NOT_READY');
}

async function observeProgress(cdp, expectedMarker) {
  const marker = JSON.stringify(expectedMarker || '');
  return await evaluate(cdp, `(() => {
    const expected=${marker};
    const assistants=[...document.querySelectorAll('[data-message-author-role=\"assistant\"], [role=\"article\"]')];
    const last=assistants.length ? String(assistants[assistants.length-1].innerText || assistants[assistants.length-1].textContent || '') : '';
    const markerCandidates=[...new Set((last.match(/MC005_ARCHITECT_RESULT_[A-Za-z0-9_-]+/g)||[]))].slice(-4);
    const buttons=[...document.querySelectorAll('button')];
    const stopVisible=buttons.some(b => /stop( generating| response)?/i.test(String(b.getAttribute('aria-label')||b.innerText||b.textContent||'')) && !b.disabled);
    const composer=document.querySelector('#prompt-textarea, textarea, [contenteditable=\"true\"]');
    const login=[...document.querySelectorAll('button,a')].some(e => /^(log in|sign in)$/i.test((e.innerText||e.textContent||'').trim()));
    return {
      assistant_nodes:assistants.length, assistant_chars:last.length, stop_visible:stopVisible,
      marker_found:!!expected && last.includes(expected), marker_candidates:markerCandidates,
      composer_ready:!!composer && !login, auth_required:login || /auth|login|signup/i.test(location.href),
      url_origin:location.origin
    };
  })()`);
}

function expectedMarkerFromBootstrap(bootstrap) {
  const found=String(bootstrap||'').match(/MC005_ARCHITECT_RESULT_[A-Za-z0-9_-]+/g) || [];
  return found.length ? found[found.length-1] : '';
}

async function injectAndSubmit(cdp, bootstrap) {
  const payload = JSON.stringify(bootstrap);
  const result = await evaluate(cdp, `(() => {
    const text=${payload};
    const el=document.querySelector('#prompt-textarea, textarea, [contenteditable="true"]');
    if(!el) return {ok:false,reason:'NO_COMPOSER'};
    el.focus();
    if(el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement){
      const proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
      const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
      if(setter) setter.call(el,text); else el.value=text;
      el.dispatchEvent(new Event('input',{bubbles:true}));
      el.dispatchEvent(new Event('change',{bubbles:true}));
    } else {
      el.textContent='';
      document.execCommand('insertText',false,text);
      if(!(el.innerText||'').includes(text.slice(0,32))) el.textContent=text;
      el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:text}));
    }
    const send=document.querySelector('[data-testid="send-button"], button[aria-label*="Send" i]');
    if(send && !send.disabled){ send.click(); return {ok:true,method:'button'}; }
    return {ok:true,method:'keyboard'};
  })()`);
  if (!result?.ok) throw new Error(`E_BOOTSTRAP_INJECT:${result?.reason || 'unknown'}`);
  if (result.method === 'keyboard') {
    await cdp.send('Input.dispatchKeyEvent', { type:'keyDown', key:'Enter', code:'Enter', windowsVirtualKeyCode:13, nativeVirtualKeyCode:13 });
    await cdp.send('Input.dispatchKeyEvent', { type:'keyUp', key:'Enter', code:'Enter', windowsVirtualKeyCode:13, nativeVirtualKeyCode:13 });
  }
  await sleep(1000);
  return result.method;
}

const browserExecutable = arg('--browser-executable');
const userDataDir = arg('--user-data-dir');
const profileDirectory = arg('--profile-directory', 'Default');
const fixtureUrl = arg('--fixture-url', '');
const startUrl = fixtureUrl || 'https://chatgpt.com/';
if (!browserExecutable || !userDataDir || !profileDirectory) {
  fail('E_CONFIG');
} else if (fixtureUrl && process.env.DIE_H01_CDP_FIXTURE !== '1') {
  fail('E_FIXTURE_MODE_FORBIDDEN');
} else if (!path.isAbsolute(browserExecutable) || !path.isAbsolute(userDataDir)) {
  fail('E_ABSOLUTE_PATH_REQUIRED');
} else if (!fs.existsSync(browserExecutable)) {
  fail('E_BROWSER_EXECUTABLE_MISSING');
} else {
  let child = null; let cdp = null; let closing = false;
  async function closeAll() {
    if (closing) return; closing = true;
    try { await cdp?.send('Browser.close', {}); } catch {}
    cdp?.close();
    const deadline=Date.now()+7000;
    while (running(child) && Date.now()<deadline) await sleep(100);
    if (running(child)) { try { child.kill('SIGTERM'); } catch {} }
    await sleep(200);
    if (running(child)) { try { child.kill('SIGKILL'); } catch {} }
  }
  process.on('SIGTERM', async () => { await closeAll(); process.exit(0); });
  process.on('SIGINT', async () => { await closeAll(); process.exit(0); });
  try {
    const bootstrap = await readBootstrap();
    fs.mkdirSync(userDataDir, { recursive:true, mode:0o700 });
    fs.rmSync(path.join(userDataDir,'DevToolsActivePort'), { force:true });
    const browserArgs = [
      `--user-data-dir=${userDataDir}`, `--profile-directory=${profileDirectory}`,
      '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
      '--no-first-run', '--no-default-browser-check'
    ];
    if (fixtureUrl) browserArgs.push('--headless=new');
    browserArgs.push(startUrl);
    child = spawn(browserExecutable, browserArgs, { stdio:'ignore', windowsHide:true });
    if (!child.pid) throw new Error('E_BROWSER_PID');
    const port = await waitPort(userDataDir, child);
    const target = await selectTarget(port);
    cdp = new Cdp(target.webSocketDebuggerUrl); await cdp.connect();
    await cdp.send('Runtime.enable'); await cdp.send('Page.enable');
    const ready = await waitReady(cdp);
    const method = await injectAndSubmit(cdp, bootstrap);
    const expectedMarker = expectedMarkerFromBootstrap(bootstrap);
    process.stdout.write(JSON.stringify({ status:'SUBMITTED', browser_pid:child.pid, debug_host:'127.0.0.1', debug_port:port, url:new URL(ready.url).origin, submit_method:method })+'\n');
    child.once('exit', () => process.exit(0));
    const emitObservation = async () => {
      if (closing || !running(child)) return;
      try {
        const obs = await observeProgress(cdp, expectedMarker);
        process.stdout.write(JSON.stringify({ status:'OBSERVATION', observed_at:new Date().toISOString(), ...obs })+'\n');
      } catch {
        process.stdout.write(JSON.stringify({ status:'OBSERVATION', observed_at:new Date().toISOString(), observation_error:true })+'\n');
      }
    };
    await emitObservation();
    const timer=setInterval(() => { void emitObservation(); }, fixtureUrl ? 250 : 2000);
    timer.unref?.();
    setInterval(() => {}, 1000);
  } catch (e) {
    await closeAll();
    fail(String(e?.message || e));
  }
}
