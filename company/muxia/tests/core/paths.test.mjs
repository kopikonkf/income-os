import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolveMuxiaPaths, isPathInside } from '../../dist/core/paths.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(HERE, '..', '..', 'src');

function collectTsFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return collectTsFiles(full);
    return entry.isFile() && entry.name.endsWith('.ts') ? [full] : [];
  });
}

test('MX-021: Windows fixture resolves configured root without host literals in core', () => {
  const p = resolveMuxiaPaths({
    root: 'D:\\muxia-root',
    pathApi: path.win32,
    env: {},
    homeDir: 'C:\\Users\\fixture',
  });
  assert.equal(p.root, 'D:\\muxia-root');
  assert.equal(p.profiles, 'D:\\muxia-root\\profiles');
  assert.equal(p.receipts, 'D:\\muxia-root\\state\\receipts');
  assert.equal(isPathInside(p.root, 'D:\\muxia-root\\profiles\\chatgpt-a', path.win32), true);
  assert.equal(isPathInside(p.root, 'D:\\other\\profile', path.win32), false);
});

test('MX-021: Linux fixture resolves configured root with identical logical layout', () => {
  const p = resolveMuxiaPaths({
    root: '/data/muxia',
    pathApi: path.posix,
    env: {},
    homeDir: '/home/fixture',
  });
  assert.equal(p.root, '/data/muxia');
  assert.equal(p.profiles, '/data/muxia/profiles');
  assert.equal(p.receipts, '/data/muxia/state/receipts');
  assert.equal(isPathInside(p.root, '/data/muxia/profiles/chatgpt-a', path.posix), true);
  assert.equal(isPathInside(p.root, '/var/tmp/escape', path.posix), false);
});

test('MX-021: MUXIA_ROOT overrides home-based development fallback', () => {
  const p = resolveMuxiaPaths({
    env: { MUXIA_ROOT: '/srv/custom-muxia' },
    homeDir: '/home/fixture',
    pathApi: path.posix,
  });
  assert.equal(p.root, '/srv/custom-muxia');
});

test('MX-021: core source has no hard-coded Windows drive or Linux production root', () => {
  const source = collectTsFiles(SRC_ROOT).map((f) => fs.readFileSync(f, 'utf8')).join('\n');
  assert.doesNotMatch(source, /[A-Za-z]:\\\\/);
  assert.doesNotMatch(source, /\/data\/muxia/);
  assert.doesNotMatch(source, /D:\\muxia/i);
});
