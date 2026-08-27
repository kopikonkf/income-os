import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repo = path.resolve(import.meta.dirname, '..', '..');
const bootstrap = path.join(repo, 'scripts', 'linux', 'mx050-bootstrap.sh');
const provision = path.join(repo, 'scripts', 'linux', 'mx050-host-provision.sh');
const apparmor = path.join(repo, 'config', 'linux', 'apparmor.d', 'muxia-playwright-chrome');
const smoke = path.join(repo, 'scripts', 'linux', 'mx050-runtime-smoke.mjs');
const pkg = JSON.parse(fs.readFileSync(path.join(repo, 'package.json'), 'utf8'));

test('MX-050: Linux bootstrap is reproducible, Node 24, root-owned Chromium, and Electron-free', () => {
  const shell = fs.readFileSync(bootstrap, 'utf8');
  const host = fs.readFileSync(provision, 'utf8');
  const profile = fs.readFileSync(apparmor, 'utf8');
  assert.match(shell, /uname -s/);
  assert.match(shell, /NODE_24_LTS_REQUIRED/);
  assert.match(shell, /npm ci/);
  assert.match(shell, /mx050-host-provision\.sh/);
  assert.match(shell, /PLAYWRIGHT_BROWSERS_PATH/);
  assert.match(shell, /npm run build/);
  assert.match(shell, /mx050-runtime-smoke\.mjs/);
  assert.match(host, /playwright install --with-deps chromium/);
  assert.match(host, /chown -R root:root \/opt\/muxia/);
  assert.match(profile, /\/opt\/muxia\/playwright-browsers\/chromium-1234\/chrome-linux64\/chrome/);
  assert.match(profile, /userns,/);
  assert.doesNotMatch(`${shell}\n${host}\n${profile}`, /--no-sandbox/);
  assert.doesNotMatch(shell, /electron/i);
  assert.equal(pkg.engines?.node, '>=24 <25');
  assert.equal(pkg.devDependencies?.typescript, '5.9.3');
  assert.equal(pkg.dependencies?.electron, undefined);
  assert.equal(pkg.devDependencies?.electron, undefined);
});

test('MX-050: runtime smoke refuses to claim Linux when executed on a non-Linux host', () => {
  if (process.platform === 'linux') return;
  const out = spawnSync(process.execPath, [smoke], { encoding: 'utf8' });
  assert.notEqual(out.status, 0);
  assert.match(`${out.stdout}\n${out.stderr}`, /MX050_REQUIRES_LINUX/);
});

test('MX-050 GUI: XFCE+xrdp is tunnel-only and does not alter operator credentials', () => {
  const gui = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx050-gui-provision.sh'), 'utf8');
  const xsession = fs.readFileSync(path.join(repo, 'config', 'linux', 'xrdp', 'xsession'), 'utf8');
  assert.match(gui, /xfce4/);
  assert.match(gui, /xrdp/);
  assert.match(gui, /port=tcp:\/\/\.:3389/);
  assert.match(gui, /127\.0\.0\.1:3389/);
  assert.match(gui, /XRDP_PUBLIC_BIND_REJECTED/);
  assert.doesNotMatch(gui, /ubuntu-desktop/);
  assert.doesNotMatch(gui, /(^|\\n)\\s*(chpasswd|passwd)(\\s|$)/);
  assert.match(xsession, /exec startxfce4/);
});

test('MX-051 operator bootstrap is manual, profile-dedicated, and automation-free during authentication', () => {
  const open = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx051-operator-open.sh'), 'utf8');
  const prepare = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx051-operator-prepare.sh'), 'utf8');
  const desktop = fs.readFileSync(path.join(repo, 'config', 'linux', 'xrdp', 'MUXIA-ChatGPT-Login.desktop'), 'utf8');
  assert.match(open, /chatgpt-linux-a/);
  assert.match(open, /https:\/\/chatgpt\.com\/auth\/login/);
  assert.match(open, /remote_debugging_enabled/);
  assert.match(open, /playwright_attached/);
  assert.doesNotMatch(open, /--remote-debugging|connectOverCDP|--no-sandbox/);
  assert.match(prepare, /0700/);
  const credentialMutations = prepare.split(/\r?\n/).filter((line) => /^\s*(chpasswd|passwd)\b/.test(line) && !/^\s*passwd -S\b/.test(line));
  assert.deepEqual(credentialMutations, []);
  assert.match(desktop, /mx051-operator-open\.sh/);
});


test('MX-051 post-login proof is sanitized, restart-persistent, and fail-closed', () => {
  const proof = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx051-sanitized-restart-proof.mjs'), 'utf8');
  assert.match(proof, /PlaywrightChromiumDriver/);
  assert.match(proof, /detectChatGptPageState/);
  assert.match(proof, /state !== 'READY'/);
  assert.match(proof, /first\.browser_pid === second\.browser_pid/);
  assert.match(proof, /debugHost === '127\.0\.0\.1'/);
  assert.match(proof, /credential_values_read: false/);
  assert.match(proof, /cookies_or_tokens_read: false/);
  assert.match(proof, /prompt_submitted: false/);
  assert.match(proof, /output_extracted: false/);
  assert.match(proof, /bypass_attempted: false/);
  assert.doesNotMatch(proof, /context\.cookies|storageState|document\.cookie|localStorage/);
  assert.doesNotMatch(proof, /--no-sandbox/);
});


test('MX-051 canaries remain operator-controlled and download to the operator home', () => {
  const canary = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx051-operator-canary-open.sh'), 'utf8');
  const prepare = fs.readFileSync(path.join(repo, 'scripts', 'linux', 'mx051-operator-canary-prepare.sh'), 'utf8');
  const desktop = fs.readFileSync(path.join(repo, 'config', 'linux', 'xrdp', 'MUXIA-MX051-Canaries.desktop'), 'utf8');
  assert.match(canary, /interaction_mode.*OPERATOR_CONTROLLED_NORMAL_CHROMIUM/);
  assert.match(canary, /prompt_submitted_by_automation.*false/);
  assert.match(canary, /output_extracted_by_automation.*false/);
  assert.match(canary, /credential_values_read_by_muxia.*false/);
  assert.match(canary, /MUXIA_LINUX_TEXT_OK_1/);
  assert.match(canary, /\$HOME\/Downloads/);
  assert.doesNotMatch(canary, /--remote-debugging|connectOverCDP|--no-sandbox/);
  assert.match(prepare, /MUXIA-MX051-Canaries\.desktop/);
  assert.match(desktop, /mx051-operator-canary-open\.sh/);
});
