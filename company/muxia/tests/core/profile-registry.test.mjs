import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { ProfileRegistry } from '../../dist/core/profile-registry.js';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-profile-registry-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const paths = resolveMuxiaPaths({ root });
  const profile = {
    profileId: 'chatgpt-a',
    providerId: 'chatgpt',
    profilePath: path.join(paths.profiles, 'chatgpt-a'),
    state: 'READY',
    leaseOwner: null,
    browserPid: null,
    lastHealthAt: null,
    lastSuccessAt: null,
    failureCount: 0,
  };
  return { root, paths, profile };
}

test('MX-022: persistent profile CRUD survives registry re-instantiation', (t) => {
  const { paths, profile } = fixture(t);
  const a = new ProfileRegistry(paths);
  a.create(profile);
  assert.equal(a.get('chatgpt-a').providerId, 'chatgpt');

  a.update({ ...a.get('chatgpt-a'), failureCount: 2, lastHealthAt: '2026-08-27T03:00:00Z' });
  const b = new ProfileRegistry(paths);
  assert.equal(b.get('chatgpt-a').failureCount, 2);
  assert.equal(b.list().length, 1);

  b.remove('chatgpt-a');
  assert.throws(() => a.get('chatgpt-a'), /PROFILE_NOT_FOUND/);
});

test('MX-022: filesystem lease rejects a second registry owner', (t) => {
  const { paths, profile } = fixture(t);
  const a = new ProfileRegistry(paths);
  const b = new ProfileRegistry(paths);
  a.create(profile);

  const leased = a.acquireLease('chatgpt-a', 'worker-a');
  assert.equal(leased.state, 'LEASED');
  assert.equal(leased.leaseOwner, 'worker-a');
  assert.throws(() => b.acquireLease('chatgpt-a', 'worker-b'), /DUPLICATE_PROFILE_LEASE/);

  const released = a.releaseLease('chatgpt-a', 'worker-a');
  assert.equal(released.state, 'READY');
  assert.equal(released.leaseOwner, null);
});

test('MX-022: wrong owner cannot release persistent lease', (t) => {
  const { paths, profile } = fixture(t);
  const registry = new ProfileRegistry(paths);
  registry.create(profile);
  registry.acquireLease('chatgpt-a', 'worker-a');
  assert.throws(() => registry.releaseLease('chatgpt-a', 'worker-b'), /LEASE_OWNER_MISMATCH/);
  assert.equal(registry.get('chatgpt-a').leaseOwner, 'worker-a');
});

test('MX-022: secret-like fields and profile paths outside configured root are rejected', (t) => {
  const { paths, profile } = fixture(t);
  const registry = new ProfileRegistry(paths);
  assert.throws(() => registry.create({ ...profile, cookieToken: 'forbidden' }), /SECRET_LIKE_FIELD_REJECTED|UNKNOWN_PROFILE_FIELD/);
  assert.throws(() => registry.create({ ...profile, profilePath: path.resolve(paths.root, '..', 'escape') }), /PROFILE_PATH_OUTSIDE_ROOT/);
});
