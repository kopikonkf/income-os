import fs from 'node:fs';
import path from 'node:path';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { JobRegistry } from '../dist/core/job-registry.js';

const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const registry = new JobRegistry(paths);
const jobId = 'mx033-image-canary-001';
const expectedFile = path.join(paths.artifacts, jobId, 'mx033-canary.png');

if (!fs.existsSync(expectedFile)) {
  throw new Error(`MX033_ARTIFACT_MISSING:${expectedFile}`);
}

let job = registry.get(jobId);
if (job.status === 'RUNNING') job = registry.transition(jobId, 'VERIFYING');
if (job.status !== 'VERIFYING' && job.status !== 'SUCCEEDED') {
  throw new Error(`MX033_UNEXPECTED_JOB_STATE:${job.status}`);
}

let receipt;
try {
  receipt = registry.registerArtifact(jobId, 'chatgpt-a', 'chatgpt-operator-image-v1', expectedFile, new Date().toISOString());
} catch (error) {
  if (String(error?.message ?? error).includes('ARTIFACT_RECEIPT_ALREADY_EXISTS')) {
    receipt = registry.verifyArtifact(jobId);
  } else {
    throw error;
  }
}

if (job.status !== 'SUCCEEDED') {
  job = registry.transition(jobId, 'SUCCEEDED');
}

const artifactReceipt = JSON.parse(fs.readFileSync(path.join(paths.receipts, `${jobId}.json`), 'utf8'));
const result = {
  schema: 'die.muxia.mx033.finalize.v1',
  task_id: 'MX-033',
  job_id: jobId,
  job_status: job.status,
  profile_id: 'chatgpt-a',
  interaction_mode: 'OPERATOR_CONTROLLED',
  prompt_submitted_by_automation: false,
  output_extracted_by_automation: false,
  artifact: {
    path: artifactReceipt.artifactPath,
    sha256: artifactReceipt.sha256,
    bytes: artifactReceipt.bytes,
    mime_type: artifactReceipt.mimeType,
    adapter_version: artifactReceipt.adapterVersion,
    receipt_path: path.join(paths.receipts, `${jobId}.json`),
  },
  verdict: 'PASS',
  finalized_at: new Date().toISOString(),
};
fs.writeFileSync(path.join(paths.state, 'mx033-image-canary-final.json'), `${JSON.stringify(result, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(result, null, 2));
