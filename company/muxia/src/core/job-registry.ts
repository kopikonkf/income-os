import fs from 'node:fs';
import path from 'node:path';
import type { JobRecord, JobState } from './domain.js';
import { transitionJob } from './domain.js';
import type { MuxiaPaths } from './paths.js';
import { assertSafeId, isPathInside } from './paths.js';
import { ArtifactRegistry } from './artifact-registry.js';
import { ensureMuxiaLayout, listJsonFiles, readJsonFile, writeJsonAtomic } from './storage.js';

const JOB_FIELDS = new Set([
  'jobId', 'providerId', 'requiredCapability', 'profileSelector', 'artifactTarget',
  'timeoutMs', 'status', 'attempt', 'createdAt',
]);

function assertExactFields(record: Record<string, unknown>): void {
  for (const key of Object.keys(record)) {
    if (!JOB_FIELDS.has(key)) throw new Error(`UNKNOWN_JOB_FIELD:${key}`);
  }
}

function assertJobShape(job: JobRecord, paths: MuxiaPaths): void {
  assertExactFields(job as unknown as Record<string, unknown>);
  assertSafeId(job.jobId, 'job');
  assertSafeId(job.providerId, 'provider');
  if (!job.requiredCapability.trim()) throw new Error('REQUIRED_CAPABILITY_MISSING');
  if (job.profileSelector !== null) assertSafeId(job.profileSelector, 'profile');
  if (!isPathInside(paths.artifacts, job.artifactTarget)) throw new Error('JOB_ARTIFACT_TARGET_OUTSIDE_ROOT');
  if (!Number.isInteger(job.timeoutMs) || job.timeoutMs <= 0) throw new Error('INVALID_JOB_TIMEOUT');
  if (!Number.isInteger(job.attempt) || job.attempt < 0) throw new Error('INVALID_JOB_ATTEMPT');
  if (!job.createdAt.trim()) throw new Error('JOB_CREATED_AT_MISSING');
}

export class JobRegistry {
  private readonly artifactRegistry: ArtifactRegistry;

  constructor(private readonly paths: MuxiaPaths) {
    ensureMuxiaLayout(paths);
    this.artifactRegistry = new ArtifactRegistry(paths);
  }

  private jobFile(jobId: string): string {
    assertSafeId(jobId, 'job');
    return path.join(this.paths.jobs, `${jobId}.json`);
  }

  create(job: JobRecord): JobRecord {
    assertJobShape(job, this.paths);
    if (job.status !== 'QUEUED') throw new Error('JOB_MUST_START_QUEUED');
    const file = this.jobFile(job.jobId);
    if (fs.existsSync(file)) throw new Error('JOB_ALREADY_EXISTS');
    fs.mkdirSync(job.artifactTarget, { recursive: true });
    writeJsonAtomic(file, job);
    return this.get(job.jobId);
  }

  get(jobId: string): JobRecord {
    const file = this.jobFile(jobId);
    if (!fs.existsSync(file)) throw new Error('JOB_NOT_FOUND');
    const job = readJsonFile<JobRecord>(file);
    assertJobShape(job, this.paths);
    return job;
  }

  list(): JobRecord[] {
    return listJsonFiles(this.paths.jobs).map((file) => {
      const job = readJsonFile<JobRecord>(file);
      assertJobShape(job, this.paths);
      return job;
    });
  }

  transition(jobId: string, next: JobState): JobRecord {
    const current = this.get(jobId);
    if (next === 'SUCCEEDED' && current.status !== 'VERIFYING') {
      transitionJob(current, next);
    }
    const evidence = next === 'SUCCEEDED' ? this.artifactRegistry.verifyForJob(current) : undefined;
    let updated = transitionJob(current, next, evidence);
    if (next === 'QUEUED' && current.status !== 'QUEUED') {
      updated = { ...updated, attempt: current.attempt + 1 };
    }
    writeJsonAtomic(this.jobFile(jobId), updated);
    return this.get(jobId);
  }

  registerArtifact(
    jobId: string,
    profileId: string,
    adapterVersion: string,
    artifactPath: string,
    createdAt?: string,
  ) {
    const job = this.get(jobId);
    return this.artifactRegistry.registerForJob(job, profileId, adapterVersion, artifactPath, createdAt);
  }

  verifyArtifact(jobId: string) {
    return this.artifactRegistry.verifyForJob(this.get(jobId));
  }
}
