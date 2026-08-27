import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { ProfileRegistry } from '../dist/core/profile-registry.js';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const registry = new ProfileRegistry(paths);
const aRoot = path.join(paths.profiles, 'chatgpt-a');
const aBrowser = path.join(aRoot, 'edge-auth');
const bRoot = path.join(paths.profiles, 'chatgpt-b');
const bBrowser = path.join(bRoot, 'edge-auth');
const aSessionPath = path.join(paths.state, 'mx034-restart-session.json');
const receiptPath = path.join(paths.state, 'mx040-two-profile-isolation.json');

function ensureProfile(profileId, profilePath) {
  try { return registry.get(profileId); }
  catch {
    fs.mkdirSync(profilePath, { recursive: true });
    return registry.create({
      profileId,
      providerId: 'chatgpt',
      profilePath,
      state: 'READY',
      leaseOwner: null,
      browserPid: null,
      lastHealthAt: null,
      lastSuccessAt: null,
      failureCount: 0,
    });
  }
}

function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function waitForPortFile(file, child) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`PROFILE_B_EDGE_EXITED:${child.exitCode}`);
    try {
      const lines = fs.readFileSync(file, 'utf8').trim().split(/\r?\n/);
      const port = Number(lines[0]);
      if (Number.isInteger(port) && port > 0) return port;
    } catch (error) {
      if (!['ENOENT', 'EBUSY', 'EACCES'].includes(error?.code)) throw error;
    }
    await wait(100);
  }
  throw new Error('PROFILE_B_DEVTOOLS_PORT_TIMEOUT');
}

function closeProcessTree(pid) {
  return new Promise((resolve) => {
    const killer = spawn('taskkill.exe', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
    killer.on('exit', () => resolve());
    killer.on('error', () => resolve());
  });
}

ensureProfile('chatgpt-a', aRoot);
const bExistedBefore = fs.existsSync(bRoot);
ensureProfile('chatgpt-b', bRoot);
if (!fs.existsSync(aBrowser)) throw new Error('PROFILE_A_BROWSER_ROOT_MISSING');
fs.mkdirSync(bBrowser, { recursive: true });

const ownerA = 'mx040-owner-a';
const ownerB = 'mx040-owner-b';
let leaseA = false;
let leaseB = false;
let duplicateLeaseRejectedA = false;
let duplicateLeaseRejectedB = false;
let crossOwnerReleaseRejected = false;
let browserA;
let browserB;
let childB;
let server;

try {
  registry.acquireLease('chatgpt-a', ownerA);
  leaseA = true;
  registry.acquireLease('chatgpt-b', ownerB);
  leaseB = true;
  try { registry.acquireLease('chatgpt-a', 'mx040-intruder-a'); } catch (e) { duplicateLeaseRejectedA = String(e.message).includes('DUPLICATE_PROFILE_LEASE'); }
  try { registry.acquireLease('chatgpt-b', 'mx040-intruder-b'); } catch (e) { duplicateLeaseRejectedB = String(e.message).includes('DUPLICATE_PROFILE_LEASE'); }
  try { registry.releaseLease('chatgpt-a', ownerB); } catch (e) { crossOwnerReleaseRejected = String(e.message).includes('LEASE_OWNER_MISMATCH'); }

  const aSession = JSON.parse(fs.readFileSync(aSessionPath, 'utf8').replace(/^\uFEFF/, ''));
  const aDebug = `http://${aSession.debug_host}:${aSession.debug_port}`;
  browserA = await chromium.connectOverCDP(aDebug, { timeout: 5000 });

  const bDevToolsFile = path.join(bBrowser, 'DevToolsActivePort');
  fs.rmSync(bDevToolsFile, { force: true });
  childB = spawn(EDGE, [
    `--user-data-dir=${bBrowser}`,
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=0',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { detached: false, windowsHide: false, stdio: 'ignore' });
  const bPort = await waitForPortFile(bDevToolsFile, childB);
  browserB = await chromium.connectOverCDP(`http://127.0.0.1:${bPort}`, { timeout: 5000 });

  server = http.createServer((req, res) => {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
    res.end('<!doctype html><html><body>MUXIA MX-040 synthetic isolation origin</body></html>');
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const address = server.address();
  const origin = `http://127.0.0.1:${address.port}/`;

  const contextA = browserA.contexts()[0];
  const contextB = browserB.contexts()[0];
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  await pageA.goto(origin, { waitUntil: 'domcontentloaded', timeout: 5000 });
  await pageA.evaluate(() => {
    localStorage.setItem('muxia_mx040_marker', 'A');
    document.cookie = 'muxia_mx040_cookie=A; SameSite=Lax';
  });
  const aBefore = await pageA.evaluate(() => ({ local: localStorage.getItem('muxia_mx040_marker'), cookie: document.cookie }));

  await pageB.goto(origin, { waitUntil: 'domcontentloaded', timeout: 5000 });
  const bBefore = await pageB.evaluate(() => ({ local: localStorage.getItem('muxia_mx040_marker'), cookie: document.cookie }));
  await pageB.evaluate(() => {
    localStorage.setItem('muxia_mx040_marker', 'B');
    document.cookie = 'muxia_mx040_cookie=B; SameSite=Lax';
  });
  const bAfter = await pageB.evaluate(() => ({ local: localStorage.getItem('muxia_mx040_marker'), cookie: document.cookie }));
  const aAfter = await pageA.evaluate(() => ({ local: localStorage.getItem('muxia_mx040_marker'), cookie: document.cookie }));

  await pageA.close();
  await pageB.close();

  const artifactA = path.join(paths.artifacts, 'mx040-profile-a');
  const artifactB = path.join(paths.artifacts, 'mx040-profile-b');
  fs.mkdirSync(artifactA, { recursive: true });
  fs.mkdirSync(artifactB, { recursive: true });
  fs.writeFileSync(path.join(artifactA, 'a.marker'), 'A\n', 'utf8');
  fs.writeFileSync(path.join(artifactB, 'b.marker'), 'B\n', 'utf8');
  const artifactNamesA = fs.readdirSync(artifactA).sort();
  const artifactNamesB = fs.readdirSync(artifactB).sort();

  const result = {
    schema: 'die.muxia.mx040.two-profile-isolation.v1',
    task_id: 'MX-040',
    status: 'PASS',
    root,
    profiles: {
      a: { profile_id: 'chatgpt-a', profile_root: aRoot, browser_root: aBrowser, debug_port: aSession.debug_port },
      b: { profile_id: 'chatgpt-b', profile_root: bRoot, browser_root: bBrowser, debug_port: bPort, existed_before_prepare: bExistedBefore },
      distinct_paths: path.resolve(aRoot).toLowerCase() !== path.resolve(bRoot).toLowerCase(),
      legacy_copy_used_for_b: false,
    },
    ownership: {
      owner_a: ownerA,
      owner_b: ownerB,
      duplicate_lease_rejected_a: duplicateLeaseRejectedA,
      duplicate_lease_rejected_b: duplicateLeaseRejectedB,
      cross_owner_release_rejected: crossOwnerReleaseRejected,
    },
    synthetic_storage: {
      origin,
      credential_values_touched: false,
      provider_cookies_read: false,
      marker_cookie_only: 'muxia_mx040_cookie',
      marker_local_storage_only: 'muxia_mx040_marker',
      a_before: aBefore,
      b_before_setting_b: bBefore,
      b_after: bAfter,
      a_after_b_write: aAfter,
      b_did_not_inherit_a: bBefore.local === null && !bBefore.cookie.includes('muxia_mx040_cookie=A'),
      a_remained_a_after_b_write: aAfter.local === 'A' && aAfter.cookie.includes('muxia_mx040_cookie=A'),
      b_remained_b: bAfter.local === 'B' && bAfter.cookie.includes('muxia_mx040_cookie=B'),
    },
    artifact_namespaces: {
      a_dir: artifactA,
      b_dir: artifactB,
      a_files: artifactNamesA,
      b_files: artifactNamesB,
      no_cross_contamination: artifactNamesA.length === 1 && artifactNamesA[0] === 'a.marker' && artifactNamesB.length === 1 && artifactNamesB[0] === 'b.marker',
    },
    acceptance: {
      distinct_ownership: duplicateLeaseRejectedA && duplicateLeaseRejectedB && crossOwnerReleaseRejected,
      no_session_storage_contamination: bBefore.local === null && !bBefore.cookie.includes('muxia_mx040_cookie=A') && aAfter.local === 'A' && bAfter.local === 'B',
      no_artifact_contamination: artifactNamesA.length === 1 && artifactNamesB.length === 1 && artifactNamesA[0] === 'a.marker' && artifactNamesB[0] === 'b.marker',
    },
    verdict: 'PASS',
    observed_at: new Date().toISOString(),
  };
  if (!Object.values(result.acceptance).every(Boolean)) throw new Error(`MX040_ACCEPTANCE_FAILED:${JSON.stringify(result.acceptance)}`);
  fs.writeFileSync(receiptPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(result, null, 2));
} finally {
  if (server) await new Promise((resolve) => server.close(resolve));
  // Do not close browserA: it is the operator's authenticated profile process.
  if (childB && childB.exitCode === null) await closeProcessTree(childB.pid);
  if (leaseB) { try { registry.releaseLease('chatgpt-b', ownerB); } catch {} }
  if (leaseA) { try { registry.releaseLease('chatgpt-a', ownerA); } catch {} }
}

process.exit(0);
