import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  acquireProfileLease,
  releaseProfileLease,
  markProfileRunning,
  transitionJob,
  assertJobTransition,
  assertProfileTransition,
  PROFILE_STATES,
  JOB_STATES,
} from '../../dist/core/domain.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCHEMA_PATH = path.resolve(HERE, '..', '..', 'contracts', 'muxia.core-domain.v1.schema.json');

function baseProfile() {
  return {
    profileId: 'chatgpt-a',
    providerId: 'chatgpt',
    profilePath: '/data/muxia/profiles/chatgpt-a',
    state: 'READY',
    leaseOwner: null,
    browserPid: null,
    lastHealthAt: null,
    lastSuccessAt: null,
    failureCount: 0,
  };
}

function baseJob(status = 'QUEUED') {
  return {
    jobId: 'job-001',
    providerId: 'chatgpt',
    requiredCapability: 'image.generate',
    profileSelector: null,
    artifactTarget: '/data/muxia/artifacts/job-001',
    timeoutMs: 420000,
    status,
    attempt: 0,
    createdAt: '2026-08-27T00:00:00Z',
  };
}

const completeEvidence = {
  artifactExists: true,
  receiptExists: true,
  hashMatches: true,
  bytesMatch: true,
  mimeMatches: true,
};

test('MX-020: profile lifecycle allows READY -> LEASED -> RUNNING -> READY with same owner', () => {
  const leased = acquireProfileLease(baseProfile(), 'worker-a');
  assert.equal(leased.state, 'LEASED');
  assert.equal(leased.leaseOwner, 'worker-a');

  const running = markProfileRunning(leased, 'worker-a', 4242);
  assert.equal(running.state, 'RUNNING');
  assert.equal(running.browserPid, 4242);

  const released = releaseProfileLease(running, 'worker-a');
  assert.equal(released.state, 'READY');
  assert.equal(released.leaseOwner, null);
  assert.equal(released.browserPid, null);
});

test('MX-020: duplicate profile lease fails closed', () => {
  const leased = acquireProfileLease(baseProfile(), 'worker-a');
  assert.throws(() => acquireProfileLease(leased, 'worker-b'), /DUPLICATE_PROFILE_LEASE/);
});

test('MX-020: wrong owner cannot run or release a leased profile', () => {
  const leased = acquireProfileLease(baseProfile(), 'worker-a');
  assert.throws(() => markProfileRunning(leased, 'worker-b', 1234), /LEASE_OWNER_MISMATCH/);
  assert.throws(() => releaseProfileLease(leased, 'worker-b'), /LEASE_OWNER_MISMATCH/);
});

test('MX-020: invalid profile transitions are rejected', () => {
  assert.throws(() => assertProfileTransition('READY', 'RUNNING'), /INVALID_PROFILE_TRANSITION/);
  assert.throws(() => assertProfileTransition('DISABLED', 'READY'), /INVALID_PROFILE_TRANSITION/);
});

test('MX-020: normal job lifecycle reaches VERIFYING before SUCCEEDED', () => {
  let job = baseJob();
  job = transitionJob(job, 'ASSIGNED');
  job = transitionJob(job, 'RUNNING');
  job = transitionJob(job, 'VERIFYING');
  job = transitionJob(job, 'SUCCEEDED', completeEvidence);
  assert.equal(job.status, 'SUCCEEDED');
});

test('MX-020: false-success transition without durable evidence is rejected', () => {
  const verifying = baseJob('VERIFYING');
  assert.throws(() => transitionJob(verifying, 'SUCCEEDED'), /FALSE_SUCCESS:MISSING_COMPLETION_EVIDENCE/);
  assert.throws(() => transitionJob(verifying, 'SUCCEEDED', { ...completeEvidence, hashMatches: false }), /FALSE_SUCCESS:HASH_MISMATCH/);
});

test('MX-020: invalid job lifecycle shortcuts are rejected', () => {
  assert.throws(() => assertJobTransition('QUEUED', 'SUCCEEDED', completeEvidence), /INVALID_JOB_TRANSITION/);
  assert.throws(() => assertJobTransition('SUCCEEDED', 'RUNNING'), /INVALID_JOB_TRANSITION/);
});

test('MX-020: core schema is valid JSON and state enums match TypeScript domain constants', () => {
  const schema = JSON.parse(fs.readFileSync(SCHEMA_PATH, 'utf8'));
  assert.equal(schema.$id, 'die.muxia.core-domain.v1');
  assert.deepEqual(schema.$defs.profile.properties.state.enum, [...PROFILE_STATES]);
  assert.deepEqual(schema.$defs.job.properties.status.enum, [...JOB_STATES]);
});
