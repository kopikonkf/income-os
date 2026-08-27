import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { resolveMuxiaPaths } from '../../dist/core/paths.js';
import { ProfileRegistry } from '../../dist/core/profile-registry.js';
import { JobRegistry } from '../../dist/core/job-registry.js';
import { markProfileRunning } from '../../dist/core/domain.js';
import { PlaywrightChromiumDriver } from '../../dist/browser/playwright-driver.js';

if (process.platform !== 'linux') throw new Error('MX052_REQUIRES_LINUX');
if (typeof process.getuid === 'function' && process.getuid() === 0) {
  throw new Error('MX052_MUST_NOT_RUN_AS_ROOT');
}

const root = process.env.MUXIA_ROOT ?? '/var/lib/muxia';
const executablePath = process.env.MUXIA_CHROME
  ?? '/opt/muxia/playwright-browsers/chromium-1234/chrome-linux64/chrome';
const paths = resolveMuxiaPaths({ root });
const profiles = new ProfileRegistry(paths);
const jobs = new JobRegistry(paths);
const profileIds = ['chatgpt-linux-b', 'chatgpt-linux-c', 'chatgpt-linux-d', 'chatgpt-linux-e'];
const runToken = String(Math.floor(Date.now() / 1000));
const drivers = new Map();
const handles = new Map();
const owners = new Map();
const jobIds = new Map();
let server;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function laneShort(profileId) {
  return profileId.at(-1);
}

function ensureProfile(profileId) {
  const profilePath = path.join(paths.profiles, profileId);
  const browserPath = path.join(profilePath, 'browser');
  try {
    const existing = profiles.get(profileId);
    if (existing.state !== 'READY' || existing.leaseOwner !== null) {
      throw new Error(`MX052_PROFILE_NOT_READY:${profileId}:${existing.state}`);
    }
    fs.mkdirSync(browserPath, { recursive: true, mode: 0o700 });
    fs.chmodSync(profilePath, 0o700);
    fs.chmodSync(browserPath, 0o700);
    return existing;
  } catch (error) {
    if (!(error instanceof Error) || error.message !== 'PROFILE_NOT_FOUND') throw error;
    fs.mkdirSync(browserPath, { recursive: true, mode: 0o700 });
    fs.chmodSync(profilePath, 0o700);
    fs.chmodSync(browserPath, 0o700);
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

function linuxProcessesForProfile(profilePath) {
  let processCount = 0;
  let rssKb = 0;
  for (const entry of fs.readdirSync('/proc')) {
    if (!/^\d+$/.test(entry)) continue;
    const procRoot = path.join('/proc', entry);
    try {
      const cmdline = fs.readFileSync(path.join(procRoot, 'cmdline'), 'utf8').replaceAll('\0', ' ');
      if (!cmdline.includes(profilePath)) continue;
      const status = fs.readFileSync(path.join(procRoot, 'status'), 'utf8');
      const rss = status.match(/^VmRSS:\s+(\d+)\s+kB$/m);
      processCount += 1;
      rssKb += rss ? Number(rss[1]) : 0;
    } catch {
      // Process may exit between /proc enumeration and read.
    }
  }
  return { process_count: processCount, rss_kb: rssKb };
}

function hostMetrics() {
  const meminfo = fs.readFileSync('/proc/meminfo', 'utf8');
  const total = Number(meminfo.match(/^MemTotal:\s+(\d+)\s+kB$/m)?.[1] ?? 0);
  const available = Number(meminfo.match(/^MemAvailable:\s+(\d+)\s+kB$/m)?.[1] ?? 0);
  return {
    mem_total_kb: total,
    mem_available_kb: available,
    load_average: fs.readFileSync('/proc/loadavg', 'utf8').trim().split(/\s+/).slice(0, 3).map(Number),
  };
}

async function closeServer() {
  if (!server) return;
  const active = server;
  server = undefined;
  await new Promise((resolve) => active.close(resolve));
}

async function cleanup(markFailed) {
  await closeServer();
  await Promise.all([...drivers.values()].map((driver) => driver.stop().catch(() => undefined)));
  for (const profileId of profileIds) {
    const owner = owners.get(profileId);
    if (owner) {
      try {
        const current = profiles.get(profileId);
        if (current.leaseOwner === owner) profiles.releaseLease(profileId, owner);
      } catch {
        // Preserve the original proof error; residual lease is detected below.
      }
    }
    if (markFailed) {
      const jobId = jobIds.get(profileId);
      if (!jobId) continue;
      try {
        const job = jobs.get(jobId);
        if (job.status === 'RUNNING' || job.status === 'VERIFYING') jobs.transition(jobId, 'FAILED');
      } catch {
        // Preserve the original proof error.
      }
    }
  }
}

let proof;
try {
  for (const profileId of profileIds) ensureProfile(profileId);

  const duplicateLeaseRejected = {};
  for (const profileId of profileIds) {
    const owner = `mx052-${laneShort(profileId)}-${runToken}`;
    owners.set(profileId, owner);
    profiles.acquireLease(profileId, owner);
    try {
      profiles.acquireLease(profileId, `${owner}-duplicate`);
      duplicateLeaseRejected[profileId] = false;
    } catch (error) {
      duplicateLeaseRejected[profileId] = error instanceof Error
        && error.message === 'DUPLICATE_PROFILE_LEASE';
    }
  }

  await Promise.all(profileIds.map(async (profileId) => {
    const driver = new PlaywrightChromiumDriver({
      executablePath,
      headless: true,
      launchTimeoutMs: 30_000,
      shutdownTimeoutMs: 8_000,
    });
    drivers.set(profileId, driver);
    const browserPath = path.join(profiles.get(profileId).profilePath, 'browser');
    const handle = await driver.launch(browserPath);
    handles.set(profileId, handle);
    profiles.update(markProfileRunning(profiles.get(profileId), owners.get(profileId), handle.pid));
  }));

  for (const profileId of profileIds) {
    const jobId = `mx052-${laneShort(profileId)}-${runToken}`;
    jobIds.set(profileId, jobId);
    jobs.create({
      jobId,
      providerId: 'chatgpt',
      requiredCapability: 'synthetic.four-profile-isolation',
      profileSelector: profileId,
      artifactTarget: path.join(paths.artifacts, jobId),
      timeoutMs: 120_000,
      status: 'QUEUED',
      attempt: 0,
      createdAt: new Date().toISOString(),
    });
    jobs.transition(jobId, 'ASSIGNED');
    jobs.transition(jobId, 'RUNNING');
  }

  server = http.createServer((request, response) => {
    response.writeHead(200, {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store',
    });
    response.end('<!doctype html><html><body><h1>MUXIA MX-052 local isolation fixture</h1></body></html>');
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('MX052_LOCAL_SERVER_ADDRESS_MISSING');
  const origin = `http://127.0.0.1:${address.port}/`;

  const pages = new Map();
  const before = {};
  for (const profileId of profileIds) {
    const context = handles.get(profileId).browser.contexts()[0];
    if (!context) throw new Error(`MX052_CONTEXT_MISSING:${profileId}`);
    const page = context.pages()[0] ?? await context.newPage();
    pages.set(profileId, page);
    await page.goto(origin, { waitUntil: 'domcontentloaded', timeout: 10_000 });
    before[profileId] = await page.evaluate(() => ({
      local: localStorage.getItem('muxia_mx052_lane'),
      cookie: document.cookie,
    }));
  }

  const workloadStartedAt = Date.now();
  const workloads = await Promise.all(profileIds.map(async (profileId) => {
    const page = pages.get(profileId);
    const marker = `${runToken}:${profileId}`;
    const started = Date.now();
    const state = await page.evaluate(async ({ marker }) => {
      localStorage.setItem('muxia_mx052_lane', marker);
      document.cookie = `muxia_mx052_lane=${encodeURIComponent(marker)}; SameSite=Lax`;
      await new Promise((resolve) => setTimeout(resolve, 2_000));
      return {
        local: localStorage.getItem('muxia_mx052_lane'),
        cookie: document.cookie,
      };
    }, { marker });
    return { profile_id: profileId, marker, started_ms: started, ended_ms: Date.now(), state };
  }));

  await sleep(300);
  const resources = {};
  for (const profileId of profileIds) {
    resources[profileId] = linuxProcessesForProfile(profiles.get(profileId).profilePath);
  }

  const after = {};
  const lanes = {};
  for (const profileId of profileIds) {
    const page = pages.get(profileId);
    after[profileId] = await page.evaluate(() => ({
      local: localStorage.getItem('muxia_mx052_lane'),
      cookie: document.cookie,
    }));

    const jobId = jobIds.get(profileId);
    const artifactPath = path.join(paths.artifacts, jobId, `${profileId}.png`);
    const logDir = path.join(paths.logs, 'mx052', runToken, profileId);
    fs.mkdirSync(logDir, { recursive: true });
    fs.writeFileSync(path.join(logDir, 'lane.log'), `profile=${profileId}\njob=${jobId}\nmarker=${runToken}:${profileId}\n`, 'utf8');
    await page.screenshot({ path: artifactPath, type: 'png' });
    jobs.transition(jobId, 'VERIFYING');
    const artifactReceipt = jobs.registerArtifact(
      jobId,
      profileId,
      'muxia-linux-synthetic-isolation-v1',
      artifactPath,
    );
    jobs.transition(jobId, 'SUCCEEDED');
    lanes[profileId] = {
      logical_owner: owners.get(profileId),
      browser_pid: handles.get(profileId).pid,
      debug_host: handles.get(profileId).debugHost,
      debug_port_ephemeral: handles.get(profileId).debugPort > 0,
      job_id: jobId,
      job_status: jobs.get(jobId).status,
      receipt_profile_id: artifactReceipt.profileId,
      artifact_path: artifactReceipt.artifactPath,
      artifact_sha256: artifactReceipt.sha256,
      artifact_bytes: artifactReceipt.bytes,
      artifact_mime_type: artifactReceipt.mimeType,
      log_dir: logDir,
      lineage_match: jobs.get(jobId).profileSelector === artifactReceipt.profileId,
    };
  }

  const overlapStart = Math.max(...workloads.map((item) => item.started_ms));
  const overlapEnd = Math.min(...workloads.map((item) => item.ended_ms));
  const overlapMs = Math.max(0, overlapEnd - overlapStart);
  const storageIsolated = profileIds.every((profileId) => {
    const expected = `${runToken}:${profileId}`;
    const current = after[profileId];
    const others = profileIds.filter((other) => other !== profileId);
    return current.local === expected
      && current.cookie.includes(encodeURIComponent(expected))
      && others.every((other) => !current.local?.includes(other));
  });
  const priorStorageOwnedOrEmpty = profileIds.every((profileId) => {
    const prior = before[profileId].local;
    return prior === null || prior.endsWith(`:${profileId}`);
  });
  const artifactAndLogsIsolated = profileIds.every((profileId) => {
    const lane = lanes[profileId];
    return lane.artifact_path.includes(lane.job_id)
      && lane.log_dir.endsWith(profileId)
      && lane.lineage_match;
  });
  const resourceMetricsCaptured = profileIds.every((profileId) => (
    resources[profileId].process_count > 0 && resources[profileId].rss_kb > 0
  ));

  proof = {
    run_token: runToken,
    local_synthetic_origin: origin,
    participants: profileIds,
    control_profile_a_excluded: !profileIds.includes('chatgpt-linux-a'),
    workload_started_at_ms: workloadStartedAt,
    overlap_ms: overlapMs,
    before,
    after,
    workloads,
    duplicate_lease_rejected: duplicateLeaseRejected,
    lanes,
    resources: {
      host: hostMetrics(),
      per_lane: resources,
      aggregate_rss_kb: Object.values(resources).reduce((sum, item) => sum + item.rss_kb, 0),
      aggregate_process_count: Object.values(resources).reduce((sum, item) => sum + item.process_count, 0),
    },
    preliminary_acceptance: {
      exactly_four_profiles: profileIds.length === 4,
      control_profile_a_excluded: !profileIds.includes('chatgpt-linux-a'),
      unique_logical_owners: new Set([...owners.values()]).size === 4,
      duplicate_lease_rejected: Object.values(duplicateLeaseRejected).every(Boolean),
      all_lanes_overlapped: overlapMs > 0,
      storage_isolated: storageIsolated,
      prior_storage_owned_or_empty: priorStorageOwnedOrEmpty,
      artifact_and_log_lineage_isolated: artifactAndLogsIsolated,
      resource_metrics_captured: resourceMetricsCaptured,
      debug_loopback_only: profileIds.every((id) => lanes[id].debug_host === '127.0.0.1'),
      all_jobs_succeeded: profileIds.every((id) => lanes[id].job_status === 'SUCCEEDED'),
    },
  };
  if (!Object.values(proof.preliminary_acceptance).every(Boolean)) {
    throw new Error(`MX052_PRELIMINARY_ACCEPTANCE_FAILED:${JSON.stringify(proof.preliminary_acceptance)}`);
  }
} catch (error) {
  await cleanup(true);
  throw error;
}

await cleanup(false);
await sleep(500);

const residualProcesses = {};
const finalProfiles = {};
for (const profileId of profileIds) {
  residualProcesses[profileId] = linuxProcessesForProfile(profiles.get(profileId).profilePath);
  const profile = profiles.get(profileId);
  finalProfiles[profileId] = {
    state: profile.state,
    lease_owner: profile.leaseOwner,
    browser_pid: profile.browserPid,
    profile_path: profile.profilePath,
    mode: (fs.statSync(profile.profilePath).mode & 0o777).toString(8).padStart(3, '0'),
  };
}

const acceptance = {
  ...proof.preliminary_acceptance,
  deterministic_teardown: profileIds.every((id) => residualProcesses[id].process_count === 0),
  leases_released: profileIds.every((id) => finalProfiles[id].lease_owner === null),
  profiles_returned_ready: profileIds.every((id) => finalProfiles[id].state === 'READY'),
  browser_pids_cleared: profileIds.every((id) => finalProfiles[id].browser_pid === null),
  profile_directories_private: profileIds.every((id) => finalProfiles[id].mode === '700'),
};
const receipt = {
  schema: 'die.muxia.mx052.four-profile-isolation.v1',
  task_id: 'MX-052',
  status: Object.values(acceptance).every(Boolean) ? 'PASS' : 'FAIL',
  platform: process.platform,
  muxia_root: root,
  ...proof,
  final_profiles: finalProfiles,
  residual_processes: residualProcesses,
  acceptance,
  credential_values_read: false,
  provider_prompt_submitted: false,
  provider_output_extracted: false,
  provider_network_used: false,
  completed_at: new Date().toISOString(),
};
if (receipt.status !== 'PASS') {
  throw new Error(`MX052_ACCEPTANCE_FAILED:${JSON.stringify(acceptance)}`);
}
const receiptPath = path.join(paths.state, 'mx052-four-profile-isolation.json');
fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
console.log(JSON.stringify(receipt, null, 2));
