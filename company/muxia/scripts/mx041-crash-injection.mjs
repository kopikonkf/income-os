import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { ProfileRegistry } from '../dist/core/profile-registry.js';
import { JobRegistry } from '../dist/core/job-registry.js';
import { markProfileRunning } from '../dist/core/domain.js';
import { recoverCrashedAssignment } from '../dist/core/crash-recovery.js';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const paths = resolveMuxiaPaths({ root });
const profiles = new ProfileRegistry(paths);
const jobs = new JobRegistry(paths);
const profileId = 'chatgpt-b';
const owner = 'mx041-worker-b';
const jobId = 'mx041-crash-job-001';
const profile = profiles.get(profileId);
const browserRoot = path.join(profile.profilePath, 'edge-auth');
const artifactTarget = path.join(paths.artifacts, jobId);
const receiptPath = path.join(paths.state, 'mx041-crash-recovery.json');

function isAlive(pid) {
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

if (profile.state !== 'READY' || profile.leaseOwner !== null) {
  throw new Error(`PROFILE_B_NOT_READY:${profile.state}:${profile.leaseOwner}`);
}
if (jobs.list().some((j) => j.jobId === jobId)) {
  throw new Error('MX041_JOB_ALREADY_EXISTS');
}
fs.mkdirSync(browserRoot, { recursive: true });

let child;
let crashPid;
let falseSuccessRejected = false;
let falseSuccessError = null;
try {
  profiles.acquireLease(profileId, owner);

  child = spawn(EDGE, [
    `--user-data-dir=${browserRoot}`,
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=0',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: 'ignore', windowsHide: false });
  crashPid = child.pid;
  await wait(1000);
  if (!isAlive(crashPid)) throw new Error('PROFILE_B_EDGE_DID_NOT_STAY_ALIVE');

  profiles.update(markProfileRunning(profiles.get(profileId), owner, crashPid));

  jobs.create({
    jobId,
    providerId: 'chatgpt',
    requiredCapability: 'synthetic.crash-proof',
    profileSelector: profileId,
    artifactTarget,
    timeoutMs: 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: new Date().toISOString(),
  });
  jobs.transition(jobId, 'ASSIGNED');
  jobs.transition(jobId, 'RUNNING');

  const preCrash = {
    profile: profiles.get(profileId),
    job: jobs.get(jobId),
    pid_alive: isAlive(crashPid),
  };

  spawnSync('taskkill.exe', ['/PID', String(crashPid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
  await wait(750);
  const aliveAfterKill = isAlive(crashPid);
  if (aliveAfterKill) throw new Error('CRASH_INJECTION_FAILED_PROCESS_STILL_ALIVE');

  const recovery = recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId,
    jobId,
    expectedOwner: owner,
    isProcessAlive: isAlive,
  });

  try {
    jobs.transition(jobId, 'SUCCEEDED');
  } catch (error) {
    falseSuccessRejected = true;
    falseSuccessError = error instanceof Error ? error.message : String(error);
  }

  const postRecovery = {
    profile: profiles.get(profileId),
    job: jobs.get(jobId),
    pid_alive: isAlive(crashPid),
    lease_file_exists: fs.existsSync(path.join(paths.locks, `profile-${profileId}.lease.json`)),
    artifact_receipt_exists: fs.existsSync(path.join(paths.receipts, `${jobId}.json`)),
  };

  const result = {
    schema: 'die.muxia.mx041.crash-recovery.v1',
    task_id: 'MX-041',
    status: 'PASS',
    profile_id: profileId,
    owner,
    job_id: jobId,
    crash_pid: crashPid,
    pre_crash: preCrash,
    crash: {
      injected: true,
      process_alive_after_kill: aliveAfterKill,
    },
    recovery,
    post_recovery: postRecovery,
    false_success: {
      rejected: falseSuccessRejected,
      error: falseSuccessError,
    },
    acceptance: {
      interrupted_job_never_succeeded: postRecovery.job.status === 'FAILED' && falseSuccessRejected,
      crashed_process_dead: postRecovery.pid_alive === false,
      lease_recovered: postRecovery.profile.state === 'READY' && postRecovery.profile.leaseOwner === null && postRecovery.lease_file_exists === false,
      no_artifact_receipt_fabricated: postRecovery.artifact_receipt_exists === false,
    },
    credential_values_read: false,
    provider_output_extracted: false,
    provider_prompt_submitted: false,
    observed_at: new Date().toISOString(),
  };
  if (!Object.values(result.acceptance).every(Boolean)) {
    throw new Error(`MX041_ACCEPTANCE_FAILED:${JSON.stringify(result.acceptance)}`);
  }
  fs.writeFileSync(receiptPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(result, null, 2));
} finally {
  if (child && child.exitCode === null && isAlive(child.pid)) {
    spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
  }
}
