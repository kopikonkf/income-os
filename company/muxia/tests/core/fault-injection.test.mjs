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
import { FAULT_KINDS, classifyInjectedFault } from '../../dist/core/fault-policy.js';

function fixture(t, suffix) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `muxia-mx061-${suffix}-`));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const paths = resolveMuxiaPaths({ root });
  const profiles = new ProfileRegistry(paths);
  const jobs = new JobRegistry(paths);
  const profileId = `profile-${suffix}`;
  const jobId = `job-${suffix}`;
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
  jobs.create({
    jobId,
    providerId: 'chatgpt',
    requiredCapability: 'synthetic.fault-injection',
    profileSelector: profileId,
    artifactTarget: path.join(paths.artifacts, jobId),
    timeoutMs: 1_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: '2026-08-30T00:00:00Z',
  });
  return { paths, profiles, jobs, profileId, jobId };
}

function start(fx, owner = 'worker-a') {
  fx.jobs.transition(fx.jobId, 'ASSIGNED');
  fx.jobs.transition(fx.jobId, 'RUNNING');
  fx.profiles.acquireLease(fx.profileId, owner);
  fx.profiles.update(markProfileRunning(fx.profiles.get(fx.profileId), owner, 424242));
}

test('MX-061: all required faults have immutable fail-closed dispositions', () => {
  assert.deepEqual([...FAULT_KINDS], ['TIMEOUT', 'BROWSER_CRASH', 'LEASE_CONTENTION', 'DISK_ARTIFACT_FAILURE', 'AUTH_REQUIRED']);
  for (const fault of FAULT_KINDS) {
    const first = classifyInjectedFault(fault);
    const second = classifyInjectedFault(fault);
    assert.deepEqual(first, second);
    assert.equal(first.successAllowed, false);
    assert.ok(first.recovery.length > 0);
    assert.ok(first.escalation.length > 0);
  }
});

test('MX-061: timeout becomes TIMED_OUT, releases ownership, and cannot succeed', (t) => {
  const fx = fixture(t, 'timeout');
  start(fx);
  fx.jobs.transition(fx.jobId, 'TIMED_OUT');
  fx.profiles.releaseLease(fx.profileId, 'worker-a');
  assert.equal(fx.jobs.get(fx.jobId).status, classifyInjectedFault('TIMEOUT').jobState);
  assert.equal(fx.profiles.get(fx.profileId).state, 'READY');
  assert.throws(() => fx.jobs.transition(fx.jobId, 'SUCCEEDED'), /INVALID_JOB_TRANSITION/);
});

test('MX-061: dead browser deterministically fails job and recovers lease', (t) => {
  const fx = fixture(t, 'crash');
  start(fx);
  const result = recoverCrashedAssignment({
    profileRegistry: fx.profiles,
    jobRegistry: fx.jobs,
    profileId: fx.profileId,
    jobId: fx.jobId,
    expectedOwner: 'worker-a',
    isProcessAlive: () => false,
  });
  assert.equal(result.action, 'RECOVERED_READY');
  assert.equal(fx.jobs.get(fx.jobId).status, classifyInjectedFault('BROWSER_CRASH').jobState);
  assert.equal(fx.profiles.get(fx.profileId).state, 'READY');
});

test('MX-061: lease contention preserves the original owner and blocks contender', (t) => {
  const fx = fixture(t, 'contention');
  fx.jobs.transition(fx.jobId, 'ASSIGNED');
  fx.profiles.acquireLease(fx.profileId, 'worker-a');
  assert.throws(() => fx.profiles.acquireLease(fx.profileId, 'worker-b'), /DUPLICATE_PROFILE_LEASE/);
  fx.jobs.transition(fx.jobId, 'BLOCKED');
  assert.equal(fx.jobs.get(fx.jobId).status, classifyInjectedFault('LEASE_CONTENTION').jobState);
  assert.equal(fx.profiles.get(fx.profileId).leaseOwner, 'worker-a');
});

test('MX-061: invalid artifact fails verification and creates no false success', (t) => {
  const fx = fixture(t, 'disk');
  fx.jobs.transition(fx.jobId, 'ASSIGNED');
  fx.jobs.transition(fx.jobId, 'RUNNING');
  fx.jobs.transition(fx.jobId, 'VERIFYING');
  const invalidArtifact = path.join(fx.paths.artifacts, fx.jobId, 'invalid.png');
  fs.writeFileSync(invalidArtifact, 'not-a-raster-container');
  assert.throws(() => fx.jobs.registerArtifact(fx.jobId, fx.profileId, 'v1', invalidArtifact), /UNSUPPORTED_RASTER_CONTAINER/);
  assert.throws(() => fx.jobs.transition(fx.jobId, 'SUCCEEDED'), /ARTIFACT_RECEIPT_NOT_FOUND/);
  fx.jobs.transition(fx.jobId, 'FAILED');
  assert.equal(fx.jobs.get(fx.jobId).status, classifyInjectedFault('DISK_ARTIFACT_FAILURE').jobState);
});

test('MX-061: auth-required waits for operator, clears process and lease, and cannot succeed', (t) => {
  const fx = fixture(t, 'auth');
  start(fx);
  fx.jobs.transition(fx.jobId, 'WAITING_OPERATOR');
  const profile = fx.profiles.requireAuthentication(fx.profileId, 'worker-a', '2026-08-30T01:00:00Z');
  assert.equal(fx.jobs.get(fx.jobId).status, classifyInjectedFault('AUTH_REQUIRED').jobState);
  assert.equal(profile.state, 'AUTH_REQUIRED');
  assert.equal(profile.leaseOwner, null);
  assert.equal(profile.browserPid, null);
  assert.equal(profile.failureCount, 1);
  assert.throws(() => fx.profiles.acquireLease(fx.profileId, 'worker-b'), /PROFILE_NOT_READY/);
  assert.throws(() => fx.jobs.transition(fx.jobId, 'SUCCEEDED'), /INVALID_JOB_TRANSITION/);
});

test('MX-061: wrong auth owner fails closed without mutation', (t) => {
  const fx = fixture(t, 'auth-owner');
  start(fx);
  assert.throws(() => fx.profiles.requireAuthentication(fx.profileId, 'worker-b'), /LEASE_OWNER_MISMATCH/);
  assert.equal(fx.profiles.get(fx.profileId).state, 'RUNNING');
  assert.equal(fx.profiles.get(fx.profileId).leaseOwner, 'worker-a');
});
