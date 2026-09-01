import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { JobRegistry } from '../../dist/core/job-registry.js';
import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import {
  LEGACY_PROXIMA_ENDPOINT,
  MX070_COMPATIBILITY_VERSION,
  adaptLegacyProximaJob,
  exportVerifiedArtifactToLegacyWorkspace,
  projectLegacyCompletion,
} from '../../dist/api/compatibility.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..', '..', '..');
const DIE_ACCEPT = path.join(REPO_ROOT, 'bin', 'die_accept.py');

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function legacyJob(workspace) {
  return {
    schema_version: 'die.worker-job.v1',
    task_id: 'M001J2A1',
    stage: 'J2',
    mission_id: 'M-001',
    goal: 'Produce one bounded canary raster without changing commercial semantics.',
    context: {
      run_id: 'M001-U1-MX070',
      expected_output: 'asset.png',
      stage_contract: {
        worker_job_unit: 'one asset',
        proxima_endpoint: LEGACY_PROXIMA_ENDPOINT,
      },
    },
    workspace,
    constraints: {
      time_budget_min: 120,
      allowed_paths: [workspace],
      network: 'proxima_loopback_only',
      forbidden: [
        'credentials', 'market submission', 'publication', 'spawning workers',
        'writes outside workspace', 'canonical state writes', 'strategy changes',
      ],
      read_only_inputs: [],
    },
    acceptance_criteria: [
      { id: 'AC-1', statement: 'Durable raster exists.', verify_with: 'hash artifact' },
      { id: 'AC-2', statement: 'Result maps criteria to evidence.', verify_with: 'die_accept.py' },
      { id: 'AC-3', statement: 'No authority expansion occurred.', verify_with: 'compat receipt' },
    ],
  };
}

function tinyPng() {
  return Buffer.from('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000049454e44ae426082', 'hex');
}

test('MX-070: legacy Proxima job maps deterministically to a bounded MUXIA job without calling :3211', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mx070-route-'));
  const paths = resolveMuxiaPaths({ root: path.join(temp, 'muxia') });
  const workspace = path.join(temp, 'legacy-workspace');
  const input = legacyJob(workspace);
  const route = adaptLegacyProximaJob(input, paths, '2026-09-01T00:00:00Z');

  assert.equal(route.schema, 'die.muxia.legacy-compat-route.v1');
  assert.equal(route.compatibilityVersion, MX070_COMPATIBILITY_VERSION);
  assert.equal(route.legacy.taskId, input.task_id);
  assert.equal(route.legacy.workspace, path.resolve(workspace));
  assert.equal(route.legacy.legacyEndpoint, LEGACY_PROXIMA_ENDPOINT);
  assert.equal(route.legacy.rollbackAvailable, true);
  assert.equal(route.legacy.legacyEndpointCalled, false);
  assert.equal(route.muxiaJob.jobId, input.task_id);
  assert.equal(route.muxiaJob.providerId, 'chatgpt');
  assert.equal(route.muxiaJob.requiredCapability, 'image.generate');
  assert.equal(route.muxiaJob.timeoutMs, 120 * 60_000);
  assert.equal(route.muxiaJob.status, 'QUEUED');
  assert.equal(route.authorityBoundary.maxCostUsd, 0);
  assert.equal(route.authorityBoundary.submissionAuthorized, false);
  assert.equal(route.authorityBoundary.publicationAuthorized, false);
});

test('MX-070: verified MUXIA raster exports idempotently to legacy workspace with identical bytes/hash', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mx070-export-'));
  const paths = resolveMuxiaPaths({ root: path.join(temp, 'muxia') });
  const workspace = path.join(temp, 'legacy-workspace');
  const input = legacyJob(workspace);
  const route = adaptLegacyProximaJob(input, paths, '2026-09-01T00:00:00Z');
  const jobs = new JobRegistry(paths);

  jobs.create(route.muxiaJob);
  jobs.transition(route.muxiaJob.jobId, 'ASSIGNED');
  jobs.transition(route.muxiaJob.jobId, 'RUNNING');
  jobs.transition(route.muxiaJob.jobId, 'VERIFYING');

  const source = path.join(route.muxiaJob.artifactTarget, 'asset.png');
  fs.mkdirSync(path.dirname(source), { recursive: true });
  const bytes = tinyPng();
  fs.writeFileSync(source, bytes);
  const receipt = jobs.registerArtifact(route.muxiaJob.jobId, 'chatgpt-a', 'chatgpt-web-v1', source, '2026-09-01T00:01:00Z');
  jobs.transition(route.muxiaJob.jobId, 'SUCCEEDED');

  const exported = exportVerifiedArtifactToLegacyWorkspace(route, receipt, paths, 'asset.png');
  assert.equal(exported.idempotentReuse, false);
  assert.equal(exported.sha256, sha256(bytes));
  assert.deepEqual(fs.readFileSync(exported.legacyArtifactPath), bytes);

  const second = exportVerifiedArtifactToLegacyWorkspace(route, receipt, paths, 'asset.png');
  assert.equal(second.idempotentReuse, true);
  assert.equal(second.sha256, exported.sha256);
});

test('MX-070: legacy RESULT projection is accepted by unchanged die_accept.py', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mx070-accept-'));
  const paths = resolveMuxiaPaths({ root: path.join(temp, 'muxia') });
  const workspace = path.join(temp, 'legacy-workspace');
  fs.mkdirSync(workspace, { recursive: true });
  const input = legacyJob(workspace);
  const route = adaptLegacyProximaJob(input, paths, '2026-09-01T00:00:00Z');
  const jobs = new JobRegistry(paths);
  jobs.create(route.muxiaJob);
  jobs.transition(route.muxiaJob.jobId, 'ASSIGNED');
  jobs.transition(route.muxiaJob.jobId, 'RUNNING');
  jobs.transition(route.muxiaJob.jobId, 'VERIFYING');

  const source = path.join(route.muxiaJob.artifactTarget, 'asset.png');
  fs.mkdirSync(path.dirname(source), { recursive: true });
  fs.writeFileSync(source, tinyPng());
  const receipt = jobs.registerArtifact(route.muxiaJob.jobId, 'chatgpt-a', 'chatgpt-web-v1', source, '2026-09-01T00:01:00Z');
  jobs.transition(route.muxiaJob.jobId, 'SUCCEEDED');
  const exported = exportVerifiedArtifactToLegacyWorkspace(route, receipt, paths, 'asset.png');
  const projection = projectLegacyCompletion(route, receipt, exported);

  assert.equal(projection.legacyResult.status, 'done');
  assert.equal(projection.workerResult.status, 'done');
  assert.equal(projection.legacyResult.artifact[0].path, 'asset.png');
  assert.equal(projection.workerResult.artifacts[0].path, 'asset.png');
  assert.deepEqual(projection.legacyResult.evidence.map((row) => row.claim), ['AC-1', 'AC-2', 'AC-3']);

  fs.writeFileSync(path.join(workspace, 'JOB.json'), JSON.stringify(input, null, 2));
  fs.writeFileSync(path.join(workspace, 'RESULT.json'), JSON.stringify(projection.legacyResult, null, 2));
  fs.writeFileSync(path.join(workspace, 'MX070_COMPATIBILITY_RECEIPT.json'), JSON.stringify(projection, null, 2));
  const changed = [exported.legacyArtifactPath, path.join(workspace, 'RESULT.json'), path.join(workspace, 'MX070_COMPATIBILITY_RECEIPT.json')];
  const changedPath = path.join(workspace, 'changed-paths.json');
  fs.writeFileSync(changedPath, JSON.stringify(changed));

  const pythonCommand = process.platform === 'win32' ? 'py' : 'python3';
  const pythonArgs = process.platform === 'win32' ? ['-3', DIE_ACCEPT, workspace, changedPath] : [DIE_ACCEPT, workspace, changedPath];
  const run = spawnSync(pythonCommand, pythonArgs, { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const accepted = JSON.parse(run.stdout);
  assert.equal(accepted.accepted_status, 'done');
  assert.deepEqual(accepted.problems, []);
});

test('MX-070: adapter fails closed on authority/network/endpoint drift and export conflicts', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mx070-fail-'));
  const paths = resolveMuxiaPaths({ root: path.join(temp, 'muxia') });
  const workspace = path.join(temp, 'legacy-workspace');

  const wrongNetwork = legacyJob(workspace);
  wrongNetwork.constraints.network = 'internet';
  assert.throws(() => adaptLegacyProximaJob(wrongNetwork, paths), /LEGACY_JOB_NOT_PROXIMA_ROUTE/);

  const missingBoundary = legacyJob(workspace);
  missingBoundary.constraints.forbidden = missingBoundary.constraints.forbidden.filter((item) => item !== 'market submission');
  assert.throws(() => adaptLegacyProximaJob(missingBoundary, paths), /LEGACY_AUTHORITY_BOUNDARY_MISSING:market submission/);

  const wrongEndpoint = legacyJob(workspace);
  wrongEndpoint.context.stage_contract.proxima_endpoint = 'http://127.0.0.1:9999/v1/chat/completions';
  assert.throws(() => adaptLegacyProximaJob(wrongEndpoint, paths), /UNSUPPORTED_LEGACY_PROXIMA_ENDPOINT/);
});
