import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { JobRegistry } from '../../dist/core/job-registry.js';

if (process.platform !== 'linux') throw new Error('MX051_FINALIZE_REQUIRES_LINUX');
if (typeof process.getuid === 'function' && process.getuid() === 0) {
  throw new Error('MX051_FINALIZE_MUST_NOT_RUN_AS_ROOT');
}
if (process.env.MUXIA_TEXT_CANARY_ATTESTED !== 'true') {
  throw new Error('MX051_OPERATOR_TEXT_ATTESTATION_REQUIRED');
}

const root = process.env.MUXIA_ROOT ?? '/var/lib/muxia';
const operatorHome = process.env.HOME ?? '/home/kopiko';
const paths = resolveMuxiaPaths({ root });
const jobs = new JobRegistry(paths);
const profileId = 'chatgpt-linux-a';
const profileDir = path.join(paths.profiles, profileId, 'browser');
const sessionPath = path.join(paths.state, 'mx051-operator-canary-session.json');
const restartPath = path.join(paths.state, 'mx051-sanitized-state-restart.json');
const finalPath = path.join(paths.state, 'mx051-single-profile-parity.json');
const downloadDir = path.join(operatorHome, 'Downloads');
const supportedExtensions = new Set(['.png', '.jpg', '.jpeg', '.webp']);

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function profileProcessCount() {
  let count = 0;
  for (const entry of fs.readdirSync('/proc')) {
    if (!/^\d+$/.test(entry)) continue;
    try {
      const cmdline = fs.readFileSync(path.join('/proc', entry, 'cmdline'), 'utf8').replaceAll('\0', ' ');
      if (cmdline.includes(`--user-data-dir=${profileDir}`)) count += 1;
    } catch {
      // Process may exit between enumeration and read.
    }
  }
  return count;
}

if (!fs.existsSync(sessionPath)) throw new Error('MX051_CANARY_SESSION_RECEIPT_MISSING');
if (!fs.existsSync(restartPath)) throw new Error('MX051_RESTART_RECEIPT_MISSING');
if (profileProcessCount() !== 0) throw new Error('MX051_OPERATOR_BROWSER_STILL_RUNNING');

const session = readJson(sessionPath);
const restart = readJson(restartPath);
if (session.status !== 'WAITING_OPERATOR_CANARIES') throw new Error('MX051_CANARY_SESSION_STATE_INVALID');
if (session.profile_id !== profileId) throw new Error('MX051_CANARY_PROFILE_MISMATCH');
if (restart.status !== 'PASS') throw new Error('MX051_RESTART_PROOF_NOT_PASS');
if (restart.first_observation?.state !== 'READY' || restart.post_restart_observation?.state !== 'READY') {
  throw new Error('MX051_RESTART_READY_EVIDENCE_MISSING');
}

const openedAtMs = Date.parse(session.opened_at);
if (!Number.isFinite(openedAtMs)) throw new Error('MX051_CANARY_OPENED_AT_INVALID');
const candidates = fs.readdirSync(downloadDir, { withFileTypes: true })
  .filter((entry) => entry.isFile() && supportedExtensions.has(path.extname(entry.name).toLowerCase()))
  .map((entry) => {
    const file = path.join(downloadDir, entry.name);
    const stat = fs.statSync(file);
    return { file, name: entry.name, mtimeMs: stat.mtimeMs, bytes: stat.size };
  })
  .filter((item) => item.mtimeMs >= openedAtMs - 2_000 && item.bytes > 0)
  .sort((left, right) => right.mtimeMs - left.mtimeMs);
if (candidates.length === 0) throw new Error('MX051_DOWNLOADED_IMAGE_NOT_FOUND');
const source = candidates[0];

const runToken = String(Math.floor(openedAtMs / 1000));
const jobId = `mx051-image-${runToken}`;
const artifactTarget = path.join(paths.artifacts, jobId);
const extension = path.extname(source.name).toLowerCase() === '.jpeg'
  ? '.jpg'
  : path.extname(source.name).toLowerCase();
const artifactPath = path.join(artifactTarget, `mx051-operator-image${extension}`);

jobs.create({
  jobId,
  providerId: 'chatgpt',
  requiredCapability: 'operator.image-canary',
  profileSelector: profileId,
  artifactTarget,
  timeoutMs: 120_000,
  status: 'QUEUED',
  attempt: 0,
  createdAt: new Date().toISOString(),
});
jobs.transition(jobId, 'ASSIGNED');
jobs.transition(jobId, 'RUNNING');
fs.copyFileSync(source.file, artifactPath);
jobs.transition(jobId, 'VERIFYING');
const artifactReceipt = jobs.registerArtifact(
  jobId,
  profileId,
  'muxia-linux-operator-image-v1',
  artifactPath,
);
jobs.transition(jobId, 'SUCCEEDED');

const textPrompt = 'Reply with exactly this text and nothing else: MUXIA_LINUX_TEXT_OK_1';
const imagePrompt = 'Create one square image: a single solid blue circle centered on a plain white background, with no text.';
const receipt = {
  schema: 'die.muxia.mx051.single-profile-parity.v1',
  task_id: 'MX-051',
  status: 'PASS',
  profile_id: profileId,
  interaction_mode: 'OPERATOR_CONTROLLED',
  sanitized_state_and_restart: {
    detector_version: restart.detector_version,
    rendering_mode: restart.rendering_mode,
    first_state: restart.first_observation.state,
    post_restart_state: restart.post_restart_observation.state,
    same_profile_reused: restart.acceptance.same_profile_reused,
    process_identity_changed: restart.acceptance.browser_process_identity_changed,
    debug_loopback_only: restart.acceptance.debug_loopback_only,
  },
  text_canary: {
    prompt_sha256: sha256(textPrompt),
    expected_response: 'MUXIA_LINUX_TEXT_OK_1',
    operator_attested_exact_response: true,
    prompt_submitted_by_automation: false,
    output_extracted_by_automation: false,
  },
  image_canary: {
    prompt_sha256: sha256(imagePrompt),
    operator_downloaded_artifact: true,
    source_download_basename: source.name,
    job_id: jobId,
    job_status: jobs.get(jobId).status,
    artifact_path: artifactReceipt.artifactPath,
    sha256: artifactReceipt.sha256,
    bytes: artifactReceipt.bytes,
    mime_type: artifactReceipt.mimeType,
    receipt_path: path.join(paths.receipts, `${jobId}.json`),
    prompt_submitted_by_automation: false,
    output_extracted_by_automation: false,
  },
  acceptance: {
    sanitized_state_ready: restart.first_observation.state === 'READY',
    restart_persistence_ready: restart.post_restart_observation.state === 'READY',
    operator_text_canary_attested: true,
    operator_image_artifact_registered: jobs.get(jobId).status === 'SUCCEEDED',
    artifact_lineage_matches_profile: artifactReceipt.profileId === profileId,
    browser_closed_before_finalize: profileProcessCount() === 0,
  },
  credential_values_read: false,
  cookies_or_tokens_read: false,
  bypass_attempted: false,
  completed_at: new Date().toISOString(),
};
if (!Object.values(receipt.acceptance).every(Boolean)) {
  throw new Error(`MX051_FINAL_ACCEPTANCE_FAILED:${JSON.stringify(receipt.acceptance)}`);
}
fs.writeFileSync(finalPath, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
console.log(JSON.stringify(receipt, null, 2));
