import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repo = path.resolve(import.meta.dirname, '..', '..');
const bootstrap = path.join(repo, 'scripts', 'linux', 'mx050-bootstrap.sh');
const smoke = path.join(repo, 'scripts', 'linux', 'mx050-runtime-smoke.mjs');
const pkg = JSON.parse(fs.readFileSync(path.join(repo, 'package.json'), 'utf8'));

test('MX-050: Linux bootstrap contract is explicit, reproducible, Node 24, and Chromium-only', () => {
  const shell = fs.readFileSync(bootstrap, 'utf8');
  assert.match(shell, /uname -s/);
  assert.match(shell, /NODE_24_LTS_REQUIRED/);
  assert.match(shell, /npm ci/);
  assert.match(shell, /playwright install --with-deps chromium/);
  assert.match(shell, /npm run build/);
  assert.match(shell, /mx050-runtime-smoke\.mjs/);
  assert.doesNotMatch(shell, /electron/i);
  assert.equal(pkg.engines?.node, '>=24 <25');
  assert.equal(pkg.dependencies?.electron, undefined);
  assert.equal(pkg.devDependencies?.electron, undefined);
});

test('MX-050: runtime smoke refuses to claim Linux when executed on a non-Linux host', () => {
  if (process.platform === 'linux') return;
  const out = spawnSync(process.execPath, [smoke], { encoding: 'utf8' });
  assert.notEqual(out.status, 0);
  assert.match(`${out.stdout}\n${out.stderr}`, /MX050_REQUIRES_LINUX/);
});
