import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import type { MuxiaPaths } from './paths.js';
import { ProfileRegistry } from './profile-registry.js';
import { JobRegistry } from './job-registry.js';
import { markProfileRunning } from './domain.js';
import { recoverCrashedAssignment } from './crash-recovery.js';

export const MX062_MIN_DURATION_MS = 24 * 60 * 60 * 1000;
export const MX062_SAMPLE_INTERVAL_MS = 60 * 1000;
export const MX062_MIN_COVERAGE = 0.95;

export interface SoakFailureCounters {
  profileCorruption: number;
  credentialLeakage: number;
  duplicateOwnership: number;
  recoveryMismatch: number;
  artifactMismatch: number;
  clockRollback: number;
  chainTamper: number;
}

export interface SoakSample {
  sequence: number;
  observedAt: string;
  elapsedMs: number;
  checks: SoakFailureCounters;
  rssBytes: number;
  previousHash: string | null;
  sampleHash: string;
}

export interface SoakReceipt {
  schema: 'muxia.mx062.soak.receipt.v1';
  status: 'PASS' | 'FAIL';
  startedAt: string;
  endedAt: string;
  elapsedMs: number;
  minimumElapsedMs: number;
  sampleIntervalMs: number;
  samples: number;
  expectedSamples: number;
  coverage: number;
  minimumCoverage: number;
  failures: SoakFailureCounters;
  peakRssBytes: number;
  finalSampleHash: string;
  authorityBoundary: {
    providerInvoked: false;
    credentialsRead: false;
    productionProfileRead: false;
    submissionAuthorized: false;
  };
}

const ZERO_COUNTERS: SoakFailureCounters = {
  profileCorruption: 0,
  credentialLeakage: 0,
  duplicateOwnership: 0,
  recoveryMismatch: 0,
  artifactMismatch: 0,
  clockRollback: 0,
  chainTamper: 0,
};

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, child]) => `${JSON.stringify(key)}:${canonical(child)}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function hashPayload(value: unknown): string {
  return crypto.createHash('sha256').update(canonical(value)).digest('hex');
}

function samplePayload(sample: Omit<SoakSample, 'sampleHash'>): Omit<SoakSample, 'sampleHash'> {
  return sample;
}

export function appendSoakSample(
  samples: readonly SoakSample[],
  input: {
    observedAt: string;
    elapsedMs: number;
    checks?: Partial<SoakFailureCounters>;
    rssBytes?: number;
  },
): SoakSample {
  const observedMs = Date.parse(input.observedAt);
  if (!Number.isFinite(observedMs)) throw new Error('MX062_INVALID_SAMPLE_TIME');
  if (!Number.isInteger(input.elapsedMs) || input.elapsedMs < 0) throw new Error('MX062_INVALID_ELAPSED_MS');
  const previous = samples.at(-1);
  if (previous) {
    if (observedMs < Date.parse(previous.observedAt) || input.elapsedMs < previous.elapsedMs) {
      throw new Error('MX062_CLOCK_ROLLBACK');
    }
    if (!verifySoakChain(samples)) throw new Error('MX062_CHAIN_TAMPER');
  }
  const checks: SoakFailureCounters = { ...ZERO_COUNTERS, ...(input.checks ?? {}) };
  for (const [name, value] of Object.entries(checks)) {
    if (!Number.isInteger(value) || value < 0) throw new Error(`MX062_INVALID_COUNTER:${name}`);
  }
  const base: Omit<SoakSample, 'sampleHash'> = {
    sequence: samples.length,
    observedAt: input.observedAt,
    elapsedMs: input.elapsedMs,
    checks,
    rssBytes: Math.max(0, Math.trunc(input.rssBytes ?? 0)),
    previousHash: previous?.sampleHash ?? null,
  };
  return { ...base, sampleHash: hashPayload(samplePayload(base)) };
}

export function verifySoakChain(samples: readonly SoakSample[]): boolean {
  let previousHash: string | null = null;
  let previousObserved = -Infinity;
  let previousElapsed = -1;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = samples[index]!;
    if (sample.sequence !== index) return false;
    if (sample.previousHash !== previousHash) return false;
    const observed = Date.parse(sample.observedAt);
    if (!Number.isFinite(observed) || observed < previousObserved || sample.elapsedMs < previousElapsed) return false;
    const { sampleHash, ...base } = sample;
    if (hashPayload(samplePayload(base)) !== sampleHash) return false;
    previousHash = sampleHash;
    previousObserved = observed;
    previousElapsed = sample.elapsedMs;
  }
  return true;
}

export function finalizeSoak(samples: readonly SoakSample[]): SoakReceipt {
  if (samples.length < 2) throw new Error('MX062_INSUFFICIENT_SAMPLES');
  if (!verifySoakChain(samples)) throw new Error('MX062_CHAIN_TAMPER');
  const first = samples[0]!;
  const last = samples.at(-1)!;
  const elapsedMs = last.elapsedMs - first.elapsedMs;
  if (elapsedMs < MX062_MIN_DURATION_MS) throw new Error('MX062_MINIMUM_24H_NOT_MET');
  const expectedSamples = Math.floor(elapsedMs / MX062_SAMPLE_INTERVAL_MS) + 1;
  const coverage = Math.min(1, samples.length / expectedSamples);
  const failures = { ...ZERO_COUNTERS };
  let peakRssBytes = 0;
  for (const sample of samples) {
    peakRssBytes = Math.max(peakRssBytes, sample.rssBytes);
    for (const key of Object.keys(failures) as Array<keyof SoakFailureCounters>) {
      failures[key] += sample.checks[key];
    }
  }
  const failureTotal = Object.values(failures).reduce((sum, value) => sum + value, 0);
  const status = coverage >= MX062_MIN_COVERAGE && failureTotal === 0 ? 'PASS' : 'FAIL';
  return {
    schema: 'muxia.mx062.soak.receipt.v1',
    status,
    startedAt: first.observedAt,
    endedAt: last.observedAt,
    elapsedMs,
    minimumElapsedMs: MX062_MIN_DURATION_MS,
    sampleIntervalMs: MX062_SAMPLE_INTERVAL_MS,
    samples: samples.length,
    expectedSamples,
    coverage: Number(coverage.toFixed(6)),
    minimumCoverage: MX062_MIN_COVERAGE,
    failures,
    peakRssBytes,
    finalSampleHash: last.sampleHash,
    authorityBoundary: {
      providerInvoked: false,
      credentialsRead: false,
      productionProfileRead: false,
      submissionAuthorized: false,
    },
  };
}

function tinyPng(): Buffer {
  return Buffer.from('89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082', 'hex');
}

function countCredentialLikeKeys(root: string): number {
  const forbidden = /(^|_)(token|cookie|password|authorization|session|secret|credential)(_|$)/i;
  let hits = 0;
  const visit = (candidate: string): void => {
    if (!fs.existsSync(candidate)) return;
    const stat = fs.statSync(candidate);
    if (stat.isDirectory()) {
      for (const entry of fs.readdirSync(candidate)) visit(path.join(candidate, entry));
      return;
    }
    if (!candidate.endsWith('.json')) return;
    try {
      const value = JSON.parse(fs.readFileSync(candidate, 'utf8')) as unknown;
      const walk = (node: unknown): void => {
        if (Array.isArray(node)) {
          node.forEach(walk);
        } else if (node && typeof node === 'object') {
          for (const [key, child] of Object.entries(node as Record<string, unknown>)) {
            if (forbidden.test(key)) hits += 1;
            walk(child);
          }
        }
      };
      walk(value);
    } catch {
      hits += 1;
    }
  };
  visit(root);
  return hits;
}

export function runSyntheticSoakProbe(paths: MuxiaPaths, cycleId: string, now = new Date().toISOString()): SoakFailureCounters {
  const counters = { ...ZERO_COUNTERS };
  const profiles = new ProfileRegistry(paths);
  const jobs = new JobRegistry(paths);
  const profileId = `mx062p-${cycleId}`;
  const owner = `mx062o-${cycleId}`;
  const crashJobId = `mx062c-${cycleId}`;
  const artifactJobId = `mx062a-${cycleId}`;
  const profilePath = path.join(paths.profiles, profileId);
  fs.mkdirSync(profilePath, { recursive: true });

  profiles.create({
    profileId,
    providerId: 'synthetic',
    profilePath,
    state: 'READY',
    leaseOwner: null,
    browserPid: null,
    lastHealthAt: now,
    lastSuccessAt: null,
    failureCount: 0,
  });
  profiles.acquireLease(profileId, owner, now);
  try {
    profiles.acquireLease(profileId, `other-${cycleId}`, now);
    counters.duplicateOwnership += 1;
  } catch (error) {
    if (!(error instanceof Error) || error.message !== 'DUPLICATE_PROFILE_LEASE') counters.duplicateOwnership += 1;
  }

  const running = markProfileRunning(profiles.get(profileId), owner, 999999);
  profiles.update(running);
  jobs.create({
    jobId: crashJobId,
    providerId: 'synthetic',
    requiredCapability: 'synthetic.recovery',
    profileSelector: profileId,
    artifactTarget: path.join(paths.artifacts, crashJobId),
    timeoutMs: 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: now,
  });
  jobs.transition(crashJobId, 'ASSIGNED');
  jobs.transition(crashJobId, 'RUNNING');
  const recovered = recoverCrashedAssignment({
    profileRegistry: profiles,
    jobRegistry: jobs,
    profileId,
    jobId: crashJobId,
    expectedOwner: owner,
    isProcessAlive: () => false,
  });
  if (recovered.action !== 'RECOVERED_READY' || recovered.jobStatus !== 'FAILED' || recovered.profileState !== 'READY') {
    counters.recoveryMismatch += 1;
  }

  jobs.create({
    jobId: artifactJobId,
    providerId: 'synthetic',
    requiredCapability: 'synthetic.artifact',
    profileSelector: profileId,
    artifactTarget: path.join(paths.artifacts, artifactJobId),
    timeoutMs: 60_000,
    status: 'QUEUED',
    attempt: 0,
    createdAt: now,
  });
  jobs.transition(artifactJobId, 'ASSIGNED');
  jobs.transition(artifactJobId, 'RUNNING');
  jobs.transition(artifactJobId, 'VERIFYING');
  const artifactPath = path.join(paths.artifacts, artifactJobId, 'probe.png');
  fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
  fs.writeFileSync(artifactPath, tinyPng());
  jobs.registerArtifact(artifactJobId, profileId, 'mx062-synthetic-v1', artifactPath, now);
  try {
    jobs.transition(artifactJobId, 'SUCCEEDED');
    const evidence = jobs.verifyArtifact(artifactJobId);
    if (!Object.values(evidence).every(Boolean)) counters.artifactMismatch += 1;
  } catch {
    counters.artifactMismatch += 1;
  }

  const reloadedProfiles = new ProfileRegistry(paths);
  const reloadedJobs = new JobRegistry(paths);
  const persisted = reloadedProfiles.get(profileId);
  if (persisted.state !== 'READY' || persisted.leaseOwner !== null || persisted.browserPid !== null) counters.profileCorruption += 1;
  if (reloadedJobs.get(crashJobId).status !== 'FAILED' || reloadedJobs.get(artifactJobId).status !== 'SUCCEEDED') counters.profileCorruption += 1;
  counters.credentialLeakage += countCredentialLikeKeys(paths.state);
  return counters;
}
