#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) args.set(process.argv[i], process.argv[i + 1]);
const requestPath = args.get('--request');
const muxiaRoot = args.get('--muxia-root');
const receiptOut = args.get('--receipt-out');
if (!requestPath || !muxiaRoot || !receiptOut) {
  console.error('usage: synthetic_muxia_proof.mjs --request <json> --muxia-root <dir> --receipt-out <json>');
  process.exit(2);
}

const dieHome = process.env.DIE_HOME || path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const distRoot = path.join(dieHome, 'company', 'muxia', 'dist', 'core');
const { resolveMuxiaPaths } = await import(pathToFileURL(path.join(distRoot, 'paths.js')).href);
const { JobRegistry } = await import(pathToFileURL(path.join(distRoot, 'job-registry.js')).href);

const request = JSON.parse(fs.readFileSync(requestPath, 'utf8'));
if (request.schema !== 'die.muxia-job-request.v1') throw new Error('REQUEST_SCHEMA_INVALID');
const exact = ['schema', 'source_task_id', 'jobId', 'providerId', 'requiredCapability', 'profileSelector', 'timeoutMs'];
if (Object.keys(request).sort().join('|') !== exact.sort().join('|')) throw new Error('REQUEST_FIELDS_INVALID');

const paths = resolveMuxiaPaths({ root: path.resolve(muxiaRoot) });
const registry = new JobRegistry(paths);
const artifactTarget = path.join(paths.artifacts, request.jobId);
const job = {
  jobId: request.jobId,
  providerId: request.providerId,
  requiredCapability: request.requiredCapability,
  profileSelector: request.profileSelector,
  artifactTarget,
  timeoutMs: request.timeoutMs,
  status: 'QUEUED',
  attempt: 0,
  createdAt: new Date().toISOString(),
};
registry.create(job);
registry.transition(job.jobId, 'ASSIGNED');
registry.transition(job.jobId, 'RUNNING');
registry.transition(job.jobId, 'VERIFYING');

// Fixed 1x1 PNG fixture. This is synthetic registry proof, not provider output.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64');
fs.mkdirSync(artifactTarget, { recursive: true });
const artifactPath = path.join(artifactTarget, 'synthetic-fixture.png');
fs.writeFileSync(artifactPath, png);
const artifactReceipt = registry.registerArtifact(job.jobId, 'synthetic-profile', 'die202-synthetic-v1', artifactPath);
const finalJob = registry.transition(job.jobId, 'SUCCEEDED');
const evidence = registry.verifyArtifact(job.jobId);

const receipt = {
  schema: 'die.worker-muxia-boundary-proof.v1',
  source_task_id: request.source_task_id,
  muxia_job_id: job.jobId,
  final_status: finalJob.status,
  artifact_receipt: artifactReceipt,
  completion_evidence: evidence,
  synthetic_fixture: true,
  provider_call_performed: false,
  consumer_chatgpt_used: false,
};
fs.writeFileSync(receiptOut, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
console.log(JSON.stringify({ status: 'PASS', muxia_job_id: job.jobId, final_status: finalJob.status, sha256: artifactReceipt.sha256 }));
