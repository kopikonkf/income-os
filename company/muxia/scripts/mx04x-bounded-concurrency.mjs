import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn, spawnSync } from 'node:child_process';
import { chromium } from 'playwright';
import { resolveMuxiaPaths } from '../dist/core/paths.js';
import { ProfileRegistry } from '../dist/core/profile-registry.js';
import { JobRegistry } from '../dist/core/job-registry.js';
import { markProfileRunning } from '../dist/core/domain.js';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const root = process.env.MUXIA_ROOT ?? 'C:\\DIE\\workspaces\\MUXIA-B04\\muxia-root';
const taskId = process.env.MUXIA_TASK_ID ?? 'MX-042';
const count = Number(process.env.MUXIA_CONCURRENCY ?? '2');
if (!['MX-042', 'MX-043'].includes(taskId)) throw new Error(`INVALID_TASK_ID:${taskId}`);
if (![2, 4].includes(count)) throw new Error(`INVALID_CONCURRENCY:${count}`);
if ((taskId === 'MX-042' && count !== 2) || (taskId === 'MX-043' && count !== 4)) throw new Error('TASK_CONCURRENCY_MISMATCH');

const paths = resolveMuxiaPaths({ root });
const profiles = new ProfileRegistry(paths);
const jobs = new JobRegistry(paths);
const profileIds = ['chatgpt-b', 'chatgpt-c', 'chatgpt-d', 'chatgpt-e'].slice(0, count);
const png1x1 = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64');
const runtime = new Map();
const ownerByProfile = new Map();
const jobByProfile = new Map();
let server;

function ensureProfile(profileId) {
  const profilePath = path.join(paths.profiles, profileId);
  try {
    const existing = profiles.get(profileId);
    if (existing.state !== 'READY' || existing.leaseOwner !== null) throw new Error(`PROFILE_NOT_READY:${profileId}:${existing.state}`);
    return existing;
  } catch (error) {
    if (!(error instanceof Error) || error.message !== 'PROFILE_NOT_FOUND') throw error;
    fs.mkdirSync(path.join(profilePath, 'edge-auth'), { recursive: true });
    return profiles.create({
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
  }
}

function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function waitForPortFile(file, child) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`EDGE_EXITED_EARLY:${child.pid}:${child.exitCode}`);
    try {
      const lines = fs.readFileSync(file, 'utf8').trim().split(/\r?\n/);
      const port = Number(lines[0]);
      if (Number.isInteger(port) && port > 0) return port;
    } catch (error) {
      if (!['ENOENT', 'EBUSY', 'EACCES'].includes(error?.code)) throw error;
    }
    await wait(100);
  }
  throw new Error(`DEVTOOLS_PORT_TIMEOUT:${child.pid}`);
}

function killTree(pid) {
  spawnSync('taskkill.exe', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
}

function resourceMetrics(profilePath) {
  const escaped = profilePath.replaceAll("'", "''");
  const ps = `$p=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'msedge.exe' -and $_.CommandLine -like '*${escaped}*'}; $o=[ordered]@{process_count=@($p).Count;working_set_bytes=([int64](($p | Measure-Object -Property WorkingSetSize -Sum).Sum));cpu_time_100ns=([int64](($p | ForEach-Object {[int64]$_.KernelModeTime+[int64]$_.UserModeTime} | Measure-Object -Sum).Sum))}; $o | ConvertTo-Json -Compress`;
  const out = spawnSync('powershell.exe', ['-NoProfile', '-Command', ps], { encoding: 'utf8', windowsHide: true, timeout: 10000 });
  if (out.status !== 0) throw new Error(`RESOURCE_SAMPLE_FAILED:${out.stderr}`);
  return JSON.parse(out.stdout.trim());
}

function hostMetrics() {
  const ps = `$o=Get-CimInstance Win32_OperatingSystem; [ordered]@{total_visible_memory_kb=[int64]$o.TotalVisibleMemorySize;free_physical_memory_kb=[int64]$o.FreePhysicalMemory} | ConvertTo-Json -Compress`;
  const out = spawnSync('powershell.exe', ['-NoProfile', '-Command', ps], { encoding: 'utf8', windowsHide: true, timeout: 10000 });
  if (out.status !== 0) throw new Error(`HOST_SAMPLE_FAILED:${out.stderr}`);
  return JSON.parse(out.stdout.trim());
}

async function launchLane(profileId) {
  const profile = profiles.get(profileId);
  const browserRoot = path.join(profile.profilePath, 'edge-auth');
  fs.mkdirSync(browserRoot, { recursive: true });
  const devtoolsFile = path.join(browserRoot, 'DevToolsActivePort');
  fs.rmSync(devtoolsFile, { force: true });
  const child = spawn(EDGE, [
    `--user-data-dir=${browserRoot}`,
    '--remote-debugging-address=127.0.0.1',
    '--remote-debugging-port=0',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank',
  ], { stdio: 'ignore', windowsHide: false });
  const port = await waitForPortFile(devtoolsFile, child);
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 5000 });
  runtime.set(profileId, { child, port, browser, browserRoot });
  return runtime.get(profileId);
}

async function cleanup() {
  for (const [profileId, rt] of runtime.entries()) {
    try { if (rt.child.exitCode === null) killTree(rt.child.pid); } catch {}
    await wait(250);
    const owner = ownerByProfile.get(profileId);
    if (owner) {
      try {
        const current = profiles.get(profileId);
        if (current.leaseOwner === owner) profiles.releaseLease(profileId, owner);
      } catch {}
    }
    const jobId = jobByProfile.get(profileId);
    if (jobId) {
      try {
        const current = jobs.get(jobId);
        if (current.status === 'RUNNING' || current.status === 'VERIFYING') jobs.transition(jobId, 'FAILED');
      } catch {}
    }
  }
}

try {
  for (const profileId of profileIds) ensureProfile(profileId);

  const duplicateLeaseRejected = {};
  for (const profileId of profileIds) {
    const owner = `${taskId.toLowerCase()}-${profileId}`;
    ownerByProfile.set(profileId, owner);
    profiles.acquireLease(profileId, owner);
    try { profiles.acquireLease(profileId, `${owner}-duplicate`); duplicateLeaseRejected[profileId] = false; }
    catch (error) { duplicateLeaseRejected[profileId] = error instanceof Error && error.message === 'DUPLICATE_PROFILE_LEASE'; }
  }

  await Promise.all(profileIds.map((id) => launchLane(id)));

  for (const profileId of profileIds) {
    const owner = ownerByProfile.get(profileId);
    const rt = runtime.get(profileId);
    profiles.update(markProfileRunning(profiles.get(profileId), owner, rt.child.pid));
    const jobId = `${taskId.toLowerCase()}-${profileId}`;
    jobByProfile.set(profileId, jobId);
    if (jobs.list().some((j) => j.jobId === jobId)) throw new Error(`JOB_ALREADY_EXISTS_FROM_PRIOR_RUN:${jobId}`);
    jobs.create({
      jobId,
      providerId: 'chatgpt',
      requiredCapability: 'synthetic.bounded-concurrency',
      profileSelector: profileId,
      artifactTarget: path.join(paths.artifacts, jobId),
      timeoutMs: 120000,
      status: 'QUEUED',
      attempt: 0,
      createdAt: new Date().toISOString(),
    });
    jobs.transition(jobId, 'ASSIGNED');
    jobs.transition(jobId, 'RUNNING');
  }

  server = http.createServer((req, res) => {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
    res.end('<!doctype html><html><body>MUXIA bounded concurrency synthetic origin</body></html>');
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const origin = `http://127.0.0.1:${server.address().port}/`;

  const pages = new Map();
  const before = {};
  for (const profileId of profileIds) {
    const context = runtime.get(profileId).browser.contexts()[0];
    const page = await context.newPage();
    pages.set(profileId, page);
    await page.goto(origin, { waitUntil: 'domcontentloaded', timeout: 5000 });
    before[profileId] = await page.evaluate(() => ({ local: localStorage.getItem('muxia_bounded_lane'), cookie: document.cookie }));
  }

  const startWall = Date.now();
  const workloadPromises = profileIds.map(async (profileId) => {
    const page = pages.get(profileId);
    const started = Date.now();
    const result = await page.evaluate(async (id) => {
      localStorage.setItem('muxia_bounded_lane', id);
      document.cookie = `muxia_bounded_lane=${id}; SameSite=Lax`;
      await new Promise((resolve) => setTimeout(resolve, 1800));
      return { local: localStorage.getItem('muxia_bounded_lane'), cookie: document.cookie };
    }, profileId);
    return { profileId, started, ended: Date.now(), result };
  });

  await wait(600);
  const host = hostMetrics();
  const resources = {};
  for (const profileId of profileIds) resources[profileId] = resourceMetrics(profiles.get(profileId).profilePath);

  const workloads = await Promise.all(workloadPromises);
  const endWall = Date.now();
  const overlapStart = Math.max(...workloads.map((w) => w.started));
  const overlapEnd = Math.min(...workloads.map((w) => w.ended));
  const overlapMs = Math.max(0, overlapEnd - overlapStart);

  const after = {};
  for (const profileId of profileIds) after[profileId] = await pages.get(profileId).evaluate(() => ({ local: localStorage.getItem('muxia_bounded_lane'), cookie: document.cookie }));

  const laneReceipts = {};
  for (const profileId of profileIds) {
    const jobId = jobByProfile.get(profileId);
    const job = jobs.get(jobId);
    const artifactPath = path.join(job.artifactTarget, `${profileId}.png`);
    const logDir = path.join(paths.logs, taskId.toLowerCase(), profileId);
    fs.mkdirSync(logDir, { recursive: true });
    fs.writeFileSync(path.join(logDir, 'lane.log'), `task=${taskId}\nprofile=${profileId}\njob=${jobId}\n`, 'utf8');
    fs.writeFileSync(artifactPath, png1x1);
    jobs.transition(jobId, 'VERIFYING');
    const receipt = jobs.registerArtifact(jobId, profileId, 'muxia-synthetic-bounded-v1', artifactPath);
    jobs.transition(jobId, 'SUCCEEDED');
    laneReceipts[profileId] = {
      job_id: jobId,
      job_profile_selector: jobs.get(jobId).profileSelector,
      job_status: jobs.get(jobId).status,
      receipt_profile_id: receipt.profileId,
      artifact_path: receipt.artifactPath,
      sha256: receipt.sha256,
      bytes: receipt.bytes,
      mime_type: receipt.mimeType,
      log_dir: logDir,
      lineage_match: jobs.get(jobId).profileSelector === receipt.profileId,
    };
  }

  const noStorageContamination = profileIds.every((id) => before[id].local === null && after[id].local === id && after[id].cookie.includes(`muxia_bounded_lane=${id}`));
  const noArtifactOrLogContamination = profileIds.every((id) => {
    const lane = laneReceipts[id];
    return lane.artifact_path.includes(lane.job_id) && lane.log_dir.includes(id) && lane.lineage_match;
  });
  const lineageCorrect = profileIds.every((id) => laneReceipts[id].lineage_match && laneReceipts[id].job_status === 'SUCCEEDED');
  const leasesCorrect = profileIds.every((id) => duplicateLeaseRejected[id] === true);
  const resourceProcessesPresent = profileIds.every((id) => resources[id].process_count > 0 && resources[id].working_set_bytes > 0);

  const result = {
    schema: 'die.muxia.bounded-concurrency.v1',
    task_id: taskId,
    status: 'PASS',
    concurrency: count,
    participants: profileIds,
    control_profile_a_excluded_from_synthetic_load: true,
    synthetic_origin: origin,
    timing: {
      wall_start_ms: startWall,
      wall_end_ms: endWall,
      wall_duration_ms: endWall - startWall,
      overlap_ms: overlapMs,
      all_lanes_overlapped: overlapMs > 0,
      workloads,
    },
    ownership: { duplicate_lease_rejected: duplicateLeaseRejected },
    storage: { before, after, no_contamination: noStorageContamination },
    lineage: { lanes: laneReceipts, correct: lineageCorrect },
    resources: {
      host,
      lanes: resources,
      aggregate_working_set_bytes: Object.values(resources).reduce((sum, r) => sum + r.working_set_bytes, 0),
      aggregate_process_count: Object.values(resources).reduce((sum, r) => sum + r.process_count, 0),
    },
    isolation: { no_artifact_or_log_contamination: noArtifactOrLogContamination },
    acceptance: {
      correct_lineage: lineageCorrect,
      no_duplicate_lease: leasesCorrect,
      all_lanes_overlapped: overlapMs > 0,
      no_storage_contamination: noStorageContamination,
      no_artifact_or_log_contamination: noArtifactOrLogContamination,
      resource_metrics_captured: resourceProcessesPresent,
    },
    credential_values_read: false,
    provider_prompt_submitted: false,
    provider_output_extracted: false,
    observed_at: new Date().toISOString(),
  };
  if (!Object.values(result.acceptance).every(Boolean)) throw new Error(`BOUNDED_CONCURRENCY_ACCEPTANCE_FAILED:${JSON.stringify(result.acceptance)}`);
  const stateReceipt = path.join(paths.state, `${taskId.toLowerCase()}-bounded-concurrency.json`);
  fs.writeFileSync(stateReceipt, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(result, null, 2));
} finally {
  if (server) await new Promise((resolve) => server.close(resolve));
  await cleanup();
}
