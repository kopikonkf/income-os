import fs from 'node:fs';
import path from 'node:path';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { JobRegistry } from '../dist/core/job-registry.js';

const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const registry = new JobRegistry(paths);
const jobId = 'mx033-image-canary-001';
const artifactTarget = path.join(paths.artifacts, jobId);
const expectedFile = path.join(artifactTarget, 'mx033-canary.png');

let job;
try {
  job = registry.get(jobId);
} catch {
  job = registry.create({
    jobId,
    providerId: 'chatgpt',
    requiredCapability: 'image.generate',
    profileSelector: 'chatgpt-a',
    artifactTarget,
    timeoutMs: 900000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: new Date().toISOString(),
  });
}

if (job.status === 'QUEUED') job = registry.transition(jobId, 'ASSIGNED');
if (job.status === 'ASSIGNED') job = registry.transition(jobId, 'RUNNING');
if (!['RUNNING', 'VERIFYING', 'SUCCEEDED'].includes(job.status)) {
  throw new Error(`MX033_UNEXPECTED_JOB_STATE:${job.status}`);
}

fs.mkdirSync(artifactTarget, { recursive: true });
const prompt = 'Create a simple square image: one cobalt-blue circle perfectly centered on a plain white background, flat vector style, no text, no logo, no watermark.';
const prep = {
  schema: 'die.muxia.mx033.prepare.v1',
  task_id: 'MX-033',
  job_id: jobId,
  job_status: job.status,
  profile_id: 'chatgpt-a',
  interaction_mode: 'OPERATOR_CONTROLLED',
  prompt,
  artifact_target: artifactTarget,
  expected_file: expectedFile,
  operator_steps: [
    'In the already-authenticated Edge ChatGPT session, manually request image generation using the pinned prompt.',
    'When the image is ready, manually download/save it as the exact expected_file path.',
    'Do not alter or convert the file after download.',
    'Report to Architect once the file exists.'
  ],
  prompt_submitted_by_automation: false,
  output_extracted_by_automation: false,
  created_at: new Date().toISOString(),
};
fs.writeFileSync(path.join(paths.state, 'mx033-image-canary-prep.json'), `${JSON.stringify(prep, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(prep, null, 2));
