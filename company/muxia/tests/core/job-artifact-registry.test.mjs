import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { JobRegistry } from '../../dist/core/job-registry.js';

const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

function fixture(t, jobId = 'job-001') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'muxia-job-registry-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const paths = resolveMuxiaPaths({ root });
  const artifactTarget = path.join(paths.artifacts, jobId);
  const job = {
    jobId,
    providerId: 'chatgpt',
    requiredCapability: 'image.generate',
    profileSelector: 'chatgpt-a',
    artifactTarget,
    timeoutMs: 420000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: '2026-08-27T04:00:00Z',
  };
  return { root, paths, artifactTarget, job };
}

function moveToVerifying(registry, jobId) {
  registry.transition(jobId, 'ASSIGNED');
  registry.transition(jobId, 'RUNNING');
  return registry.transition(jobId, 'VERIFYING');
}

test('MX-023: job lifecycle persists across registry restart and succeeds only with durable matching artifact receipt', (t) => {
  const { paths, artifactTarget, job } = fixture(t);
  const a = new JobRegistry(paths);
  a.create(job);
  moveToVerifying(a, job.jobId);

  const artifact = path.join(artifactTarget, 'output.png');
  fs.writeFileSync(artifact, PNG_1X1);
  const receipt = a.registerArtifact(job.jobId, 'chatgpt-a', 'chatgpt-operator-v1', artifact, '2026-08-27T04:01:00Z');
  assert.equal(receipt.status, 'VERIFIED');
  assert.equal(receipt.bytes, PNG_1X1.length);
  assert.equal(receipt.mimeType, 'image/png');

  const b = new JobRegistry(paths);
  assert.equal(b.get(job.jobId).status, 'VERIFYING');
  assert.deepEqual(b.verifyArtifact(job.jobId), {
    artifactExists: true,
    receiptExists: true,
    hashMatches: true,
    bytesMatch: true,
    mimeMatches: true,
  });
  assert.equal(b.transition(job.jobId, 'SUCCEEDED').status, 'SUCCEEDED');

  const c = new JobRegistry(paths);
  assert.equal(c.get(job.jobId).status, 'SUCCEEDED');
});

test('MX-023: SUCCEEDED is rejected when no artifact receipt exists', (t) => {
  const { paths, job } = fixture(t, 'job-no-receipt');
  const registry = new JobRegistry(paths);
  registry.create(job);
  moveToVerifying(registry, job.jobId);
  assert.throws(() => registry.transition(job.jobId, 'SUCCEEDED'), /ARTIFACT_RECEIPT_NOT_FOUND/);
  assert.equal(registry.get(job.jobId).status, 'VERIFYING');
});

test('MX-023: corrupted artifact after receipt creation blocks success after restart', (t) => {
  const { paths, artifactTarget, job } = fixture(t, 'job-corrupt');
  const a = new JobRegistry(paths);
  a.create(job);
  moveToVerifying(a, job.jobId);
  const artifact = path.join(artifactTarget, 'output.png');
  fs.writeFileSync(artifact, PNG_1X1);
  a.registerArtifact(job.jobId, 'chatgpt-a', 'chatgpt-operator-v1', artifact);

  fs.appendFileSync(artifact, Buffer.from('corruption'));
  const b = new JobRegistry(paths);
  assert.throws(() => b.transition(job.jobId, 'SUCCEEDED'), /ARTIFACT_HASH_MISMATCH/);
  assert.equal(b.get(job.jobId).status, 'VERIFYING');
});

test('MX-023: artifact outside job target or MUXIA artifact root is rejected', (t) => {
  const { paths, job } = fixture(t, 'job-boundary');
  const registry = new JobRegistry(paths);
  registry.create(job);
  moveToVerifying(registry, job.jobId);

  const outside = path.join(paths.root, 'outside.png');
  fs.writeFileSync(outside, PNG_1X1);
  assert.throws(() => registry.registerArtifact(job.jobId, 'chatgpt-a', 'v1', outside), /ARTIFACT_OUTSIDE_MUXIA_ROOT|ARTIFACT_OUTSIDE_JOB_TARGET/);
});

test('MX-023: failed job requeue increments attempt and remains restart-safe', (t) => {
  const { paths, job } = fixture(t, 'job-retry');
  const a = new JobRegistry(paths);
  a.create(job);
  a.transition(job.jobId, 'ASSIGNED');
  a.transition(job.jobId, 'RUNNING');
  a.transition(job.jobId, 'FAILED');
  const retried = a.transition(job.jobId, 'QUEUED');
  assert.equal(retried.attempt, 1);

  const b = new JobRegistry(paths);
  assert.equal(b.get(job.jobId).attempt, 1);
  assert.equal(b.get(job.jobId).status, 'QUEUED');
});

test('MX-042: artifact profile lineage mismatch is rejected before success', (t) => {
  const { paths, artifactTarget, job } = fixture(t, 'job-profile-lineage');
  const registry = new JobRegistry(paths);
  registry.create(job);
  moveToVerifying(registry, job.jobId);
  const artifact = path.join(artifactTarget, 'output.png');
  fs.writeFileSync(artifact, PNG_1X1);
  registry.registerArtifact(job.jobId, 'chatgpt-b', 'chatgpt-operator-v1', artifact);
  assert.throws(() => registry.transition(job.jobId, 'SUCCEEDED'), /ARTIFACT_PROFILE_MISMATCH/);
  assert.equal(registry.get(job.jobId).status, 'VERIFYING');
});
