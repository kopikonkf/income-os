import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { ProfileRegistry } from '../../dist/core/profile-registry.js';
import { JobRegistry } from '../../dist/core/job-registry.js';
import { markProfileRunning } from '../../dist/core/domain.js';
import { recoverCrashedAssignment } from '../../dist/core/crash-recovery.js';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-mx041-'));
  const paths = resolveMuxiaPaths({ root });
  const profiles = new ProfileRegistry(paths);
  const jobs = new JobRegistry(paths);
  const profilePath = path.join(paths.profiles, 'chatgpt-b');
  fs.mkdirSync(profilePath, { recursive: true });
  profiles.create({
    profileId: 'chatgpt-b',
    providerId: 'chatgpt',
    profilePath,
    state: 'READY',
    leaseOwner: null,
    browserPid: null,
    lastHealthAt: null,
    lastSuccessAt: null,
    failureCount: 0,
  });
  jobs.create({
    jobId: 'mx041-job',
    providerId: 'chatgpt',
    requiredCapability: 'synthetic.crash-proof',
    profileSelector: 'chatgpt-b',
    artifactTarget: path.join(paths.artifacts, 'mx041-job'),
    timeoutMs: 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: new Date().toISOString(),
  });
  jobs.transition('mx041-job', 'ASSIGNED');
  jobs.transition('mx041-job', 'RUNNING');
  profiles.acquireLease('chatgpt-b', 'worker-b');
  profiles.update(markProfileRunning(profiles.get('chatgpt-b'), 'worker-b', 424242));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return { paths, profiles, jobs };
}

test('MX-041: crashed RUNNING assignment becomes FAILED and lease recovers to READY', (t) => {
  const { profiles, jobs } = fixture(t);
  const result = recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId: 'chatgpt-b',
    jobId: 'mx041-job',
    expectedOwner: 'worker-b',
    isProcessAlive: () => false,
  });
  assert.equal(result.action, 'RECOVERED_READY');
  assert.equal(jobs.get('mx041-job').status, 'FAILED');
  const profile = profiles.get('chatgpt-b');
  assert.equal(profile.state, 'READY');
  assert.equal(profile.leaseOwner, null);
  assert.equal(profile.browserPid, null);
});

test('MX-041: live process is never recovered prematurely', (t) => {
  const { profiles, jobs } = fixture(t);
  const result = recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId: 'chatgpt-b',
    jobId: 'mx041-job',
    expectedOwner: 'worker-b',
    isProcessAlive: () => true,
  });
  assert.equal(result.action, 'NOOP_PROCESS_ALIVE');
  assert.equal(jobs.get('mx041-job').status, 'RUNNING');
  assert.equal(profiles.get('chatgpt-b').state, 'RUNNING');
});

test('MX-041: ambiguous owner fails closed to quarantine-required with no mutation', (t) => {
  const { profiles, jobs } = fixture(t);
  const result = recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId: 'chatgpt-b',
    jobId: 'mx041-job',
    expectedOwner: 'wrong-owner',
    isProcessAlive: () => false,
  });
  assert.equal(result.action, 'QUARANTINE_REQUIRED');
  assert.equal(result.reason, 'LEASE_OWNER_AMBIGUOUS');
  assert.equal(jobs.get('mx041-job').status, 'RUNNING');
  assert.equal(profiles.get('chatgpt-b').state, 'RUNNING');
});

test('MX-041: recovered interrupted job cannot be marked SUCCEEDED', (t) => {
  const { profiles, jobs } = fixture(t);
  recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId: 'chatgpt-b',
    jobId: 'mx041-job',
    expectedOwner: 'worker-b',
    isProcessAlive: () => false,
  });
  assert.throws(
    () => jobs.transition('mx041-job', 'SUCCEEDED'),
    /(ARTIFACT_RECEIPT_NOT_FOUND|INVALID_JOB_TRANSITION)/,
  );
  assert.equal(jobs.get('mx041-job').status, 'FAILED');
});
