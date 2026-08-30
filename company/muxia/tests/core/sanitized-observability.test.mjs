import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { ProfileRegistry } from '../../dist/core/profile-registry.js';
import { JobRegistry } from '../../dist/core/job-registry.js';
import { markProfileRunning } from '../../dist/core/domain.js';
import { buildSanitizedHealthSnapshot } from '../../dist/observability/health.js';
import { REDACTED, safeDiagnosticCode, sanitizeLogEvent } from '../../dist/observability/sanitized-logging.js';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-mx060-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const paths = resolveMuxiaPaths({ root });
  const profiles = new ProfileRegistry(paths);
  const jobs = new JobRegistry(paths);
  for (const profileId of ['chatgpt-a', 'chatgpt-b']) {
    const profilePath = path.join(paths.profiles, profileId);
    fs.mkdirSync(profilePath, { recursive: true });
    profiles.create({
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
  profiles.acquireLease('chatgpt-b', 'sensitive-owner-name');
  profiles.update(markProfileRunning(profiles.get('chatgpt-b'), 'sensitive-owner-name', 424242));
  jobs.create({
    jobId: 'mx060-job',
    providerId: 'chatgpt',
    requiredCapability: 'image.generate',
    profileSelector: 'chatgpt-b',
    artifactTarget: path.join(paths.artifacts, 'mx060-job'),
    timeoutMs: 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: '2026-08-30T00:00:00Z',
  });
  jobs.transition('mx060-job', 'ASSIGNED');
  jobs.transition('mx060-job', 'RUNNING');
  jobs.transition('mx060-job', 'VERIFYING');
  return { root, paths, profiles, jobs };
}

test('MX-060: health diagnoses dead process and missing artifact without runtime-private fields', (t) => {
  const { root, profiles, jobs } = fixture(t);
  const snapshot = buildSanitizedHealthSnapshot({
    providers: [{
      providerId: 'chatgpt',
      adapterVersion: 'chatgpt-operator-v1',
      capabilities: ['image.generate'],
      health: 'DEGRADED',
    }],
    profileRegistry: profiles,
    jobRegistry: jobs,
    isProcessAlive: () => false,
    observedAt: '2026-08-30T01:00:00Z',
  });

  assert.equal(snapshot.grade, 'DEGRADED');
  assert.deepEqual(snapshot.profiles.find((row) => row.profileId === 'chatgpt-b')?.issueCodes, ['RUNNING_PROCESS_DEAD']);
  assert.deepEqual(snapshot.jobs[0].issueCodes, ['ARTIFACT_RECEIPT_NOT_FOUND']);
  assert.equal(snapshot.jobs[0].artifact, 'INVALID');

  const serialized = JSON.stringify(snapshot);
  for (const forbidden of [root, 'sensitive-owner-name', '424242', 'profilePath', 'leaseOwner', 'browserPid', 'artifactTarget', 'artifactPath']) {
    assert.equal(serialized.includes(forbidden), false, `health leaked ${forbidden}`);
  }
});

test('MX-060: log sanitizer redacts credential-equivalent keys and values recursively', () => {
  const jwt = 'eyJ0123456789.abcdefghijklmno.qrstuvwxyz01234';
  const event = sanitizeLogEvent({
    event: 'provider.failure',
    authorization: 'Bearer highly-sensitive-value',
    nested: {
      cookieJar: 'sid=highly-sensitive-cookie',
      harmless: 'diagnostic-code',
      providerDetail: `request failed ${jwt}`,
    },
    list: ['safe', 'access_token=highly-sensitive-token'],
    error: new Error('ARTIFACT_MISSING:/private/runtime/path'),
  });
  const serialized = JSON.stringify(event);
  for (const secret of ['highly-sensitive-value', 'highly-sensitive-cookie', 'highly-sensitive-token', jwt, '/private/runtime/path']) {
    assert.equal(serialized.includes(secret), false, `log leaked ${secret}`);
  }
  assert.equal(event.authorization, REDACTED);
  assert.equal(event.nested.cookieJar, REDACTED);
  assert.equal(event.nested.harmless, 'diagnostic-code');
  assert.deepEqual(event.error, { name: 'Error', code: 'ARTIFACT_MISSING' });
});

test('MX-060: diagnostic codes reject free-form/raw error text', () => {
  assert.equal(safeDiagnosticCode('LEASE_OWNER_MISMATCH:worker-a'), 'LEASE_OWNER_MISMATCH');
  assert.equal(safeDiagnosticCode('network failed for user@example.test'), 'INTERNAL_ERROR');
});
